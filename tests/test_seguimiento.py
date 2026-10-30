"""Gestor de documentos, pasos 1A, 3 y 5: seguimiento, encargado, notas y etapa de un cartel (docs/GESTOR_DOCUMENTOS.md).

Datos SINTÉTICOS en una base temporal; nunca toca data/.
"""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import historial, panel, seguimiento, usuarios
from app.database import apply_migrations, connect
from app.historial import Quien
from app.importers.carteles import import_carteles
from app.main import app
from app.matching.evaluar import evaluar_base
from app.matching.reglas import cargar_reglas
from tests.test_panel import CARTELES_SINTETICO, CONTRASENA, iniciar_sesion, token_csrf

AHORA = datetime.now(timezone.utc).replace(microsecond=0)
CR = timezone(timedelta(hours=-6))
CIERRE = (AHORA + timedelta(days=5)).astimezone(CR).isoformat(timespec="seconds")
NRO = "00000000001"     # GPS sintético: sale en el panel (Alta)
OTRO = "00000000002"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    t = "2026-10-01T00:00:00+00:00"
    with closing(connect(path)) as conn:
        conn.execute("INSERT INTO institutions (cedula, nombre, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                     ("3000000001", "Municipalidad Sintética A", t, t))
        conn.executemany(
            "INSERT INTO tenders (nro_sicop, descripcion, institution_cedula, fecha_cierre_recepcion, content_hash,"
            " first_seen, last_seen) VALUES (?, ?, '3000000001', ?, 'h', ?, ?)",
            [(NRO, "Servicio de monitoreo GPS de vehículos", CIERRE, t, t),
             (OTRO, "Monitoreo GPS para la flotilla municipal", CIERRE, t, t)])
        evaluar_base(conn, cargar_reglas(), AHORA)
        usuarios.crear_usuario(conn, "oscar@ejemplo.test", "Oscar", CONTRASENA, usuarios.ADMIN)
        usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", CONTRASENA)
        usuarios.crear_usuario(conn, "ana@ejemplo.test", "Ana", CONTRASENA)
    return path


def _id(db, email):
    with closing(connect(db)) as conn:
        return usuarios.buscar_id(conn, email)


def _quien(db, email):
    with closing(connect(db)) as conn:
        u = usuarios.obtener(conn, usuarios.buscar_id(conn, email))
    return Quien(u.id, u.nombre)


@pytest.fixture
def clientes(db, monkeypatch):
    """Un cliente con sesión por persona: Oscar (admin), Ivania y Ana (encargadas)."""
    monkeypatch.setenv("DATABASE_PATH", str(db))
    resultado = {}
    for nombre, email in (("oscar", "oscar@ejemplo.test"), ("ivania", "ivania@ejemplo.test"),
                          ("ana", "ana@ejemplo.test")):
        cliente = TestClient(app)
        assert iniciar_sesion(cliente, email).status_code == 303
        resultado[nombre] = cliente
    return resultado


def _dar_seguimiento(cliente, nro=NRO):
    token = token_csrf(cliente.get(f"/oportunidades/{nro}").text)
    return cliente.post(f"/oportunidades/{nro}/seguimiento", data={"csrf_token": token}, follow_redirects=False)


def _asignar(cliente, encargado_id, nro=NRO):
    token = token_csrf(cliente.get("/oportunidades").text)
    return cliente.post(f"/seguimiento/{nro}/encargado", data={"csrf_token": token, "encargado": str(encargado_id)},
                        follow_redirects=False)


# --- Lógica (sin web) ---------------------------------------------------------------------------------------------

def test_abrir_dos_veces_no_duplica_y_queda_sin_encargado(db):
    quien = _quien(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        assert seguimiento.abrir(conn, NRO, quien, AHORA) is True
        assert seguimiento.abrir(conn, NRO, quien, AHORA) is False
        estado = seguimiento.estado(conn, NRO)
        assert conn.execute("SELECT count(*) FROM seguimientos").fetchone()[0] == 1
        eventos = historial.ultimos(conn, historial.DE_SEGUIMIENTO)

    assert (estado.abierto_por, estado.encargado_id, estado.encargado) == ("Ivania", None, None)
    assert [(e.accion, e.detalle) for e in eventos] == [("abrir_seguimiento", NRO)]


def test_cambiar_de_encargado_guarda_el_historial(db):
    admin = _quien(db, "oscar@ejemplo.test")
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, NRO, admin, AHORA)
        assert seguimiento.asignar(conn, NRO, _id(db, "ivania@ejemplo.test"), admin, AHORA) is True
        assert seguimiento.asignar(conn, NRO, _id(db, "ivania@ejemplo.test"), admin, AHORA) is False  # ya lo era
        assert seguimiento.asignar(conn, NRO, _id(db, "ana@ejemplo.test"), admin, AHORA + timedelta(hours=1)) is True
        estado = seguimiento.estado(conn, NRO)
        asignaciones = seguimiento.historial_de(conn, NRO)
        eventos = [e.detalle for e in historial.ultimos(conn, ("asignar_encargado",))]

    assert estado.encargado == "Ana"
    assert [(a.encargado, a.asignado_por) for a in asignaciones] == [("Ana", "Oscar"), ("Ivania", "Oscar")]
    assert eventos == [f"{NRO}: Ivania → Ana", f"{NRO}: sin encargado → Ivania"]


def test_no_se_asigna_a_un_usuario_desactivado_ni_sin_seguimiento(db):
    admin = _quien(db, "oscar@ejemplo.test")
    with closing(connect(db)) as conn:
        with pytest.raises(seguimiento.SeguimientoInvalido, match="no está en seguimiento"):
            seguimiento.asignar(conn, NRO, _id(db, "ivania@ejemplo.test"), admin, AHORA)
        seguimiento.abrir(conn, NRO, admin, AHORA)
        usuarios.cambiar_estado(conn, _id(db, "ana@ejemplo.test"), False)
        with pytest.raises(seguimiento.SeguimientoInvalido, match="desactivado"):
            seguimiento.asignar(conn, NRO, _id(db, "ana@ejemplo.test"), admin, AHORA)
        assert [u.nombre for u in seguimiento.asignables(conn)] == ["Ivania", "Oscar"]


def test_los_seguimientos_y_las_asignaciones_no_se_borran_ni_se_cambian(db):
    admin = _quien(db, "oscar@ejemplo.test")
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, NRO, admin, AHORA)
        seguimiento.asignar(conn, NRO, _id(db, "ivania@ejemplo.test"), admin, AHORA)
        for sql in ("DELETE FROM seguimientos", "UPDATE seguimientos SET abierto_por_nombre = 'x'",
                    "DELETE FROM seguimiento_asignaciones", "UPDATE seguimiento_asignaciones SET encargado_id = 1"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)
        assert seguimiento.estado(conn, NRO).encargado == "Ivania"


def test_reimportar_y_reevaluar_no_toca_el_seguimiento(tmp_path):
    db = tmp_path / "sicop.db"
    apply_migrations(db)
    raw = tmp_path / "raw"
    with closing(connect(db)) as conn:
        import_carteles(conn, CARTELES_SINTETICO, "sintetico", raw)
        usuarios.crear_usuario(conn, "oscar@ejemplo.test", "Oscar", CONTRASENA, usuarios.ADMIN)
        admin = Quien(usuarios.buscar_id(conn, "oscar@ejemplo.test"), "Oscar")
        seguimiento.abrir(conn, "20269900001", admin, AHORA)
        seguimiento.asignar(conn, "20269900001", admin.user_id, admin, AHORA)

    modificado = tmp_path / "carteles_v2.csv"
    modificado.write_bytes(CARTELES_SINTETICO.read_bytes().replace(
        b"monitoreo GPS de flotilla vehicular;", b"monitoreo GPS de flotilla vehicular (enmienda);"))
    with closing(connect(db)) as conn:
        assert import_carteles(conn, modificado, "sintetico", raw).actualizadas == 1
        evaluar_base(conn, cargar_reglas(), AHORA)
        estado = seguimiento.estado(conn, "20269900001")

    assert (estado.abierto_por, estado.encargado) == ("Oscar", "Oscar")


# --- Rutas web ----------------------------------------------------------------------------------------------------

def test_cualquier_usuario_da_seguimiento_y_aparece_en_la_pagina(clientes):
    ana = clientes["ana"]
    assert 'action="/oportunidades/00000000001/seguimiento"' in ana.get(f"/oportunidades/{NRO}").text

    respuesta = _dar_seguimiento(ana)

    assert respuesta.status_code == 303 and respuesta.headers["location"] == f"/oportunidades/{NRO}"
    detalle = ana.get(f"/oportunidades/{NRO}").text
    assert "En seguimiento · sin encargado" in detalle and "Dar seguimiento</button>" not in detalle
    lista = ana.get("/seguimiento").text
    assert NRO in lista and "Sin encargado" in lista and "Lo abrió Ana" in lista
    assert f'href="/seguimiento/{NRO}"' not in lista  # sin encargado, solo entran los administradores
    assert _dar_seguimiento(ana).status_code == 303  # dos veces: no falla ni duplica


def test_solo_un_administrador_asigna(clientes, db):
    _dar_seguimiento(clientes["ana"])

    assert _asignar(clientes["ana"], _id(db, "ana@ejemplo.test")).status_code == 403
    respuesta = _asignar(clientes["oscar"], _id(db, "ivania@ejemplo.test"))

    assert respuesta.status_code == 303 and respuesta.headers["location"] == f"/seguimiento/{NRO}"
    pagina = clientes["oscar"].get(f"/seguimiento/{NRO}").text
    assert "Encargado asignado." in pagina and "Ivania · asignado por Oscar" in pagina
    assert "Le llegará un correo con el ciclo diario de las 8:00." in pagina   # paso 1B
    assert 'name="encargado"' in pagina  # el administrador ve el formulario


def test_el_expediente_solo_lo_ven_su_encargado_y_los_administradores(clientes, db):
    _dar_seguimiento(clientes["ana"])
    _asignar(clientes["oscar"], _id(db, "ivania@ejemplo.test"))

    ivania = clientes["ivania"].get(f"/seguimiento/{NRO}")
    ana = clientes["ana"].get(f"/seguimiento/{NRO}")

    assert ivania.status_code == 200 and 'name="encargado"' not in ivania.text  # la encargada no reasigna
    assert ana.status_code == 403 and "Este expediente es de Ivania y de los administradores" in ana.text
    assert clientes["oscar"].get(f"/seguimiento/{NRO}").status_code == 200
    # Ana no entra, pero ve quién lo tiene: en el panel, en el cartel y en la página de seguimiento.
    assert "En seguimiento · Ivania" in clientes["ana"].get("/oportunidades").text
    detalle = clientes["ana"].get(f"/oportunidades/{NRO}").text
    assert "En seguimiento · Ivania" in detalle and f'href="/seguimiento/{NRO}"' not in detalle
    assert f'href="/seguimiento/{NRO}"' in clientes["ivania"].get(f"/oportunidades/{NRO}").text


def test_un_cartel_vencido_sale_del_panel_pero_sigue_en_seguimiento(clientes, db):
    _dar_seguimiento(clientes["ana"])
    vencido = (AHORA - timedelta(minutes=1)).astimezone(CR).isoformat(timespec="seconds")
    with closing(connect(db)) as conn:  # el cierre pasó hace un minuto
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = ? WHERE nro_sicop = ?", (vencido, NRO))

    assert f'href="/oportunidades/{NRO}"' not in clientes["ana"].get("/oportunidades").text
    assert f'href="/oportunidades/{NRO}"' in clientes["ana"].get("/oportunidades?plazo=vencido").text
    assert f'href="/oportunidades/{NRO}"' in clientes["ana"].get("/seguimiento").text
    assert clientes["ana"].get(f"/oportunidades/{NRO}").status_code == 200  # nada se borra


def test_sin_token_csrf_no_se_da_seguimiento_ni_se_asigna(clientes, db):
    assert clientes["ana"].post(f"/oportunidades/{NRO}/seguimiento", follow_redirects=False).status_code == 403
    _dar_seguimiento(clientes["ana"])
    sin_token = clientes["oscar"].post(f"/seguimiento/{NRO}/encargado",
                                       data={"encargado": str(_id(db, "ivania@ejemplo.test"))}, follow_redirects=False)

    assert sin_token.status_code == 403
    with closing(connect(db)) as conn:
        assert seguimiento.estado(conn, NRO).encargado is None


def test_errores_claros(clientes):
    token = token_csrf(clientes["ana"].get("/oportunidades").text)
    no_existe = clientes["ana"].post("/oportunidades/99999999999/seguimiento", data={"csrf_token": token},
                                     follow_redirects=False)
    assert no_existe.status_code == 404
    assert clientes["oscar"].get(f"/seguimiento/{OTRO}").status_code == 404  # no está en seguimiento
    _dar_seguimiento(clientes["ana"])
    elegir_nada = _asignar(clientes["oscar"], "")
    assert elegir_nada.status_code == 400 and "Elige un encargado de la lista." in elegir_nada.text


# --- Paso 5: etapas del seguimiento -------------------------------------------------------------------------------

def _etapa(cliente, etapa, nro=NRO):
    token = token_csrf(cliente.get("/oportunidades").text)
    return cliente.post(f"/seguimiento/{nro}/etapa", data={"csrf_token": token, "etapa": etapa},
                        follow_redirects=False)


def _etapa_de(db, nro=NRO):
    with closing(connect(db)) as conn:
        return seguimiento.estado(conn, nro).etapa


def test_empieza_preparando_y_cada_cambio_queda_en_el_historial(db):
    ivania = _quien(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, NRO, ivania, AHORA)
        assert seguimiento.estado(conn, NRO).etapa == "preparando" and seguimiento.etapas_de(conn, NRO) == []
        assert seguimiento.cambiar_etapa(conn, NRO, "preparando", ivania, AHORA) is False  # ya lo estaba
        assert seguimiento.cambiar_etapa(conn, NRO, "enviada", ivania, AHORA) is True
        assert seguimiento.cambiar_etapa(conn, NRO, "ganada", ivania, AHORA + timedelta(days=1)) is True
        assert seguimiento.cambiar_etapa(conn, NRO, "enviada", ivania, AHORA + timedelta(days=2)) is True  # corrige
        estado = seguimiento.estado(conn, NRO)
        cambios = seguimiento.etapas_de(conn, NRO)
        eventos = [e.detalle for e in historial.ultimos(conn, ("cambiar_etapa",))]

    assert (estado.etapa, estado.etapa_texto) == ("enviada", "Enviada")
    assert [(c.etapa, c.puesta_por) for c in cambios] == [("enviada", "Ivania"), ("ganada", "Ivania"),
                                                           ("enviada", "Ivania")]
    assert eventos == [f"{NRO}: Ganada → Enviada", f"{NRO}: Enviada → Ganada", f"{NRO}: Preparando → Enviada"]


def test_etapa_invalida_o_sin_seguimiento_y_no_se_borra_ni_se_cambia(db):
    ivania = _quien(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        with pytest.raises(seguimiento.SeguimientoInvalido, match="no está en seguimiento"):
            seguimiento.cambiar_etapa(conn, NRO, "enviada", ivania, AHORA)
        seguimiento.abrir(conn, NRO, ivania, AHORA)
        with pytest.raises(seguimiento.SeguimientoInvalido, match="Elige una etapa"):
            seguimiento.cambiar_etapa(conn, NRO, "adjudicada", ivania, AHORA)
        with pytest.raises(sqlite3.IntegrityError):  # la base tampoco acepta otra etapa
            conn.execute("INSERT INTO seguimiento_etapas (seguimiento_id, etapa, puesta_por, puesta_por_nombre,"
                         " created_at) VALUES (1, 'adjudicada', 1, 'x', 't')")
        seguimiento.cambiar_etapa(conn, NRO, "perdida", ivania, AHORA)
        for sql in ("DELETE FROM seguimiento_etapas", "UPDATE seguimiento_etapas SET etapa = 'ganada'"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)
        assert seguimiento.estado(conn, NRO).etapa == "perdida"


def test_la_etapa_no_cambia_la_decision_y_reevaluar_no_la_toca(db):
    ivania = _quien(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        panel.guardar_revision(conn, NRO, "interesa", "", "", ivania.user_id, AHORA)
        seguimiento.abrir(conn, NRO, ivania, AHORA)
        seguimiento.cambiar_etapa(conn, NRO, "ganada", ivania, AHORA)
        evaluar_base(conn, cargar_reglas(), AHORA + timedelta(hours=1))
        decisiones = [d for (d,) in conn.execute("SELECT decision FROM reviews WHERE nro_sicop = ?", (NRO,))]
        assert seguimiento.estado(conn, NRO).etapa == "ganada"
    assert decisiones == ["interesa"]


def test_la_etapa_la_cambian_el_encargado_y_los_administradores(clientes, db):
    _dar_seguimiento(clientes["ana"])
    _asignar(clientes["oscar"], _id(db, "ivania@ejemplo.test"))

    assert _etapa(clientes["ana"], "perdida").status_code == 403  # dio seguimiento, pero no es la encargada
    assert _etapa_de(db) == "preparando"
    respuesta = _etapa(clientes["ivania"], "enviada")
    assert respuesta.status_code == 303 and respuesta.headers["location"] == f"/seguimiento/{NRO}#etapa"
    expediente = clientes["ivania"].get(f"/seguimiento/{NRO}").text
    assert "Etapa: Enviada." in expediente and "¿Marcar también el cartel como «Ofertada»?" in expediente
    assert _etapa(clientes["oscar"], "ganada").status_code == 303
    assert _etapa_de(db) == "ganada"
    # Todos ven la etapa, aunque no entren al expediente.
    assert "En seguimiento · Ivania · ganada" in clientes["ana"].get(f"/oportunidades/{NRO}").text
    assert "En seguimiento · Ivania · ganada" in clientes["ana"].get("/oportunidades").text
    assert "etapa-ganada" in clientes["ana"].get("/seguimiento").text


def test_ya_ofertada_no_sugiere_y_errores_de_etapa(clientes, db):
    _dar_seguimiento(clientes["ana"])
    with closing(connect(db)) as conn:
        panel.guardar_revision(conn, NRO, "ofertada", "", "", _id(db, "oscar@ejemplo.test"), AHORA)
    _etapa(clientes["oscar"], "enviada")
    assert "¿Marcar también" not in clientes["oscar"].get(f"/seguimiento/{NRO}").text

    invalida = _etapa(clientes["oscar"], "adjudicada")
    assert invalida.status_code == 400 and "Elige una etapa" in invalida.text
    assert _etapa(clientes["oscar"], "ganada", nro=OTRO).status_code == 404  # no está en seguimiento
    sin_token = clientes["oscar"].post(f"/seguimiento/{NRO}/etapa", data={"etapa": "ganada"}, follow_redirects=False)
    assert sin_token.status_code == 403 and _etapa_de(db) == "enviada"


# --- Paso 3: notas del expediente ---------------------------------------------------------------------------------

def _nota(cliente, texto, nro=NRO):
    token = token_csrf(cliente.get("/oportunidades").text)
    return cliente.post(f"/seguimiento/{nro}/notas", data={"csrf_token": token, "texto": texto},
                        follow_redirects=False)


def _notas_de(db, nro=NRO):
    with closing(connect(db)) as conn:
        return seguimiento.notas_de(conn, nro)


def test_notas_con_autor_y_fecha_de_la_mas_reciente_a_la_mas_vieja(db):
    ivania, oscar = _quien(db, "ivania@ejemplo.test"), _quien(db, "oscar@ejemplo.test")
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, NRO, ivania, AHORA)
        seguimiento.escribir_nota(conn, NRO, "  Pedir el pliego a la proveeduría.\r\nLlamar el lunes.  ", ivania, AHORA)
        seguimiento.escribir_nota(conn, NRO, "Revisé la garantía: 5 %.", oscar, AHORA + timedelta(hours=1))
        notas = seguimiento.notas_de(conn, NRO)
        eventos = [e.detalle for e in historial.ultimos(conn, ("escribir_nota",))]

    assert [(n.texto, n.escrita_por) for n in notas] == [
        ("Revisé la garantía: 5 %.", "Oscar"),
        ("Pedir el pliego a la proveeduría.\nLlamar el lunes.", "Ivania")]  # sin espacios sobrantes ni CRLF
    assert notas[1].fecha.endswith("-06:00")  # hora de Costa Rica
    assert eventos == [f"{NRO}: nota #2", f"{NRO}: nota #1"]  # el historial no copia el texto


def test_nota_vacia_larga_o_sin_seguimiento_y_no_se_borra_ni_se_cambia(db):
    ivania = _quien(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        with pytest.raises(seguimiento.SeguimientoInvalido, match="no está en seguimiento"):
            seguimiento.escribir_nota(conn, NRO, "Hola", ivania, AHORA)
        seguimiento.abrir(conn, NRO, ivania, AHORA)
        with pytest.raises(seguimiento.SeguimientoInvalido, match="Escribe la nota"):
            seguimiento.escribir_nota(conn, NRO, " \r\n ", ivania, AHORA)
        with pytest.raises(seguimiento.SeguimientoInvalido, match="2001 caracteres; el máximo es 2000"):
            seguimiento.escribir_nota(conn, NRO, "x" * 2001, ivania, AHORA)
        seguimiento.escribir_nota(conn, NRO, "x" * 2000, ivania, AHORA)  # justo en el tope
        with pytest.raises(sqlite3.IntegrityError):  # la base tampoco acepta una más larga
            conn.execute("INSERT INTO seguimiento_notas (seguimiento_id, texto, escrita_por, escrita_por_nombre,"
                         " created_at) VALUES (1, ?, 1, 'x', 't')", ("x" * 2001,))
        for sql in ("DELETE FROM seguimiento_notas", "UPDATE seguimiento_notas SET texto = 'otra cosa'"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)
        evaluar_base(conn, cargar_reglas(), AHORA + timedelta(hours=1))  # reevaluar no las toca
        assert [len(n.texto) for n in seguimiento.notas_de(conn, NRO)] == [2000]


def test_las_notas_las_escriben_y_las_leen_el_encargado_y_los_administradores(clientes, db):
    _dar_seguimiento(clientes["ana"])
    _asignar(clientes["oscar"], _id(db, "ivania@ejemplo.test"))

    assert _nota(clientes["ana"], "Yo también quiero").status_code == 403  # dio seguimiento, pero no es la encargada
    respuesta = _nota(clientes["ivania"], "Pedir aclaración <b>sobre</b> el plazo.\nAntes del viernes.")
    assert respuesta.status_code == 303 and respuesta.headers["location"] == f"/seguimiento/{NRO}#notas"
    assert _nota(clientes["oscar"], "Visto.").status_code == 303
    expediente = clientes["ivania"].get(f"/seguimiento/{NRO}").text
    assert "Nota guardada." in expediente and "Visto." in expediente
    assert "Pedir aclaración &lt;b&gt;sobre&lt;/b&gt; el plazo.\nAntes del viernes." in expediente  # texto, no HTML
    assert "Pedir aclaración" not in clientes["ana"].get(f"/seguimiento/{NRO}").text  # 403: no la lee
    # Al cambiar de encargado, la nueva lee todo lo anterior y la anterior ya no entra.
    _asignar(clientes["oscar"], _id(db, "ana@ejemplo.test"))
    assert "Pedir aclaración" in clientes["ana"].get(f"/seguimiento/{NRO}").text
    assert _nota(clientes["ivania"], "Una más").status_code == 403
    assert [n.escrita_por for n in _notas_de(db)] == ["Oscar", "Ivania"]


def test_errores_de_nota_conservan_el_texto(clientes, db):
    _dar_seguimiento(clientes["ana"])
    vacia = _nota(clientes["oscar"], "   ")
    assert vacia.status_code == 400 and "Escribe la nota." in vacia.text
    larga = _nota(clientes["oscar"], "Borrador largo " + "y" * 2000)
    assert larga.status_code == 400 and "el máximo es 2000" in larga.text and "Borrador largo yyy" in larga.text
    assert _nota(clientes["oscar"], "Hola", nro=OTRO).status_code == 404  # no está en seguimiento
    sin_token = clientes["oscar"].post(f"/seguimiento/{NRO}/notas", data={"texto": "Hola"}, follow_redirects=False)
    assert sin_token.status_code == 403 and _notas_de(db) == []
