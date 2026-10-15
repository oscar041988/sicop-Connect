"""Panel web (lección 5): lista con filtros, detalle con evidencia y revisión humana.

Datos SINTÉTICOS en una base temporal; nunca toca data/.
"""

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import panel, usuarios
from app.database import apply_migrations, connect
from app.importers.carteles import import_carteles
from app.main import app
from app.matching.evaluar import evaluar_base, plazo_estado
from app.matching.reglas import cargar_reglas

AHORA = datetime.now(timezone.utc).replace(microsecond=0)
CR = timezone(timedelta(hours=-6))
CARTELES_SINTETICO = Path(__file__).parent / "fixtures" / "carteles_sintetico.csv"


def _cierre(dias):
    return (AHORA + timedelta(days=dias)).astimezone(CR).isoformat(timespec="seconds")


CARTELES = [
    # nro, título, cédula, tipo, cierre → resultado esperado con las reglas reales
    ("00000000001", "Servicio de monitoreo GPS de vehículos", "3000000001", "Licitación Reducida", _cierre(3)),     # Alta, cierra en 7 días
    ("00000000002", "Alquiler de GPS para la flotilla", "3000000002", "Licitación Menor", _cierre(30)),            # Media, abierto
    ("00000000003", "Compra de GPS", "3000000001", "Licitación Reducida", _cierre(-10)),                           # Baja, vencido
    ("00000000004", "Cámaras corporales para policía <script>alert(1)</script>", "3000000002",
     "Procedimiento por Excepción", None),                                                                          # Alta, por verificar
    ("00000000005", "Compra de sillas", "3000000001", "Licitación Menor", _cierre(5)),                            # sin coincidencia
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    t = "2026-10-01T00:00:00+00:00"
    with closing(connect(path)) as conn:
        conn.executemany("INSERT INTO institutions (cedula, nombre, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                         [("3000000001", "Municipalidad Sintética A", t, t), ("3000000002", "Ministerio Sintético B", t, t)])
        conn.executemany(
            "INSERT INTO tenders (nro_sicop, descripcion, institution_cedula, tipo_procedimiento, fecha_cierre_recepcion,"
            " content_hash, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, 'h', ?, ?)",
            [(*c, t, t) for c in CARTELES])
        evaluar_base(conn, cargar_reglas(), AHORA)
    return path


CONTRASENA = "una contraseña sintética larga"


def token_csrf(html):
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def iniciar_sesion(cliente, email="ivania@ejemplo.test", contrasena=CONTRASENA):
    token = token_csrf(cliente.get("/login").text)
    return cliente.post("/login", data={"csrf_token": token, "email": email, "contrasena": contrasena},
                        follow_redirects=False)


@pytest.fixture
def cliente(db, monkeypatch):
    """Cliente con la sesión iniciada (usuario sintético en la base temporal)."""
    monkeypatch.setenv("DATABASE_PATH", str(db))
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", CONTRASENA)
    cliente = TestClient(app)
    assert iniciar_sesion(cliente).status_code == 303
    return cliente


def _listar(db, **filtros):
    with closing(connect(db)) as conn:
        version = panel.version_vigente(conn)
        return panel.listar(conn, version, panel.Filtros(**filtros), AHORA)


def _nros(pagina):
    return [f.nro_sicop for f in pagina.filas]


def _usuario(conn, nombre="Ivania"):
    """id del usuario sintético con ese nombre (lo crea la primera vez)."""
    email = f"{nombre.lower()}@ejemplo.test"
    fila = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    return fila[0] if fila else usuarios.crear_usuario(conn, email, nombre, CONTRASENA)


def _revisar(db, nro, decision="interesa", motivo="", comentario="", responsable="Ivania"):
    with closing(connect(db)) as conn:
        panel.guardar_revision(conn, nro, decision, motivo, comentario, _usuario(conn, responsable), AHORA)


# --- Lista: filtros, orden y páginas --------------------------------------------------------

def test_por_defecto_solo_candidatos_ordenados_por_cierre(db):
    p = _listar(db)

    assert _nros(p) == ["00000000001", "00000000002", "00000000004"]  # cierra pronto → abierto → por verificar
    assert [f.plazo for f in p.filas] == ["cierra_7_dias", "abierto", "por_verificar"]
    assert p.total == 3


@pytest.mark.parametrize("filtros, esperado", [
    ({"familia": "camaras_corporales"}, ["00000000004"]),
    ({"institucion": "3000000002"}, ["00000000002", "00000000004"]),
    ({"plazo": "abierto"}, ["00000000002"]),
    ({"tipo": "Licitación Reducida"}, ["00000000001"]),
    ({"prioridad": "baja"}, ["00000000004", "00000000003"]),  # el 4 también es Baja en videotelematica
    ({"prioridad": "todas", "familia": "gps_flotas"}, ["00000000001", "00000000002", "00000000003"]),
    ({"prioridad": "inventada", "plazo": "inventado"}, ["00000000001", "00000000002", "00000000004"]),  # se ignoran
])
def test_filtros(db, filtros, esperado):
    assert _nros(_listar(db, **filtros)) == esperado


def test_filtro_revisado(db):
    _revisar(db, "00000000001")

    assert _nros(_listar(db, revisado="si")) == ["00000000001"]
    assert _nros(_listar(db, revisado="no")) == ["00000000002", "00000000004"]
    assert _listar(db).filas[0].decision == "interesa"


def test_paginas(db, monkeypatch):
    monkeypatch.setattr(panel, "POR_PAGINA", 2)

    assert (_listar(db).paginas, _nros(_listar(db, pagina=2))) == (2, ["00000000004"])
    assert _listar(db, pagina=99).pagina == 2  # una página que no existe muestra la última


def test_plazo_en_sql_es_igual_al_de_python(db):
    cierres = [None, "2026-11-30", _cierre(-1), _cierre(0.5), _cierre(7.5), _cierre(40)]
    with closing(connect(db)) as conn:
        for n, cierre in enumerate(cierres):
            conn.execute("UPDATE tenders SET fecha_cierre_recepcion = ? WHERE nro_sicop = '00000000005'", (cierre,))
            sql = conn.execute(f"SELECT {panel._PLAZO_SQL} FROM tenders t WHERE nro_sicop = :nro",
                               {"ahora": AHORA.isoformat(timespec="seconds"), "nro": "00000000005"}).fetchone()[0]
            assert sql == plazo_estado(cierre, AHORA), cierre


# --- Evidencia resaltada y HTML escapado -------------------------------------------------------

def test_frases_de_evidencia():
    assert panel.frases_de_evidencia("«MONITOREO GPS» (título) · «GPS» (línea 1) · «GPS» (línea 2)") == {
        "título": ["MONITOREO GPS"], "línea 1": ["GPS"], "línea 2": ["GPS"]}


def test_resaltar_escapa_y_marca():
    resultado = panel.resaltar("<b>GPS</b> y monitoreo GPS", ["GPS", "monitoreo GPS"])

    assert str(resultado) == "&lt;b&gt;<mark>GPS</mark>&lt;/b&gt; y <mark>monitoreo GPS</mark>"


# --- Revisión humana ------------------------------------------------------------------------------

@pytest.mark.parametrize("cambios, mensaje", [
    ({"decision": "no_interesa"}, "motivo"),
    ({"decision": "quizas"}, "decisión"),
    ({"comentario": "x" * 2001}, "comentario"),
])
def test_revision_invalida_no_se_guarda(db, cambios, mensaje):
    with pytest.raises(panel.RevisionInvalida, match=mensaje):
        _revisar(db, "00000000001", **cambios)
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_revision_guarda_historial_y_motivo_solo_con_no_interesa(db):
    _revisar(db, "00000000001", "interesa", motivo="plazo", comentario="  Llamar al comprador  ")
    _revisar(db, "00000000001", "no_interesa", motivo="requisitos", responsable="Oscar")
    with closing(connect(db)) as conn:
        d = panel.detalle(conn, "00000000001", panel.version_vigente(conn), AHORA)

    assert [(r.decision, r.motivo, r.comentario, r.responsable) for r in d.revisiones] == [
        ("no_interesa", "requisitos", None, "Oscar"),           # la vigente primero
        ("interesa", None, "Llamar al comprador", "Ivania"),     # el motivo se ignora si no es «no interesa»
    ]


def test_revision_queda_ligada_al_usuario(db):
    _revisar(db, "00000000001", responsable="Oscar")

    with closing(connect(db)) as conn:
        assert conn.execute("SELECT u.email, r.responsable FROM reviews r JOIN users u ON u.id = r.user_id"
                            ).fetchall() == [("oscar@ejemplo.test", "Oscar")]


def test_usuario_desactivado_o_inexistente_no_puede_revisar(db):
    with closing(connect(db)) as conn:
        oscar = _usuario(conn, "Oscar")
        conn.execute("UPDATE users SET active = 0 WHERE id = ?", (oscar,))
        for user_id in (oscar, 999):
            with pytest.raises(panel.RevisionInvalida, match="desactivado"):
                panel.guardar_revision(conn, "00000000001", "interesa", "", "", user_id, AHORA)
        assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_revisiones_viejas_sin_usuario_se_muestran_como_escritas_a_mano(db):
    with closing(connect(db)) as conn:  # así quedaron las revisiones de antes del login
        conn.execute("INSERT INTO reviews (nro_sicop, responsable, decision, created_at)"
                     " VALUES ('00000000001', 'Ivania', 'interesa', '2026-10-09T10:00:00-06:00')")
    _revisar(db, "00000000001", "revisar_requisitos")
    with closing(connect(db)) as conn:
        d = panel.detalle(conn, "00000000001", panel.version_vigente(conn), AHORA)

    assert [(r.responsable, r.escrito_a_mano) for r in d.revisiones] == [("Ivania", False), ("Ivania", True)]


def test_reimportar_el_cartel_modificado_no_borra_la_revision(tmp_path):
    db = tmp_path / "sicop.db"
    apply_migrations(db)
    raw = tmp_path / "raw"
    with closing(connect(db)) as conn:
        import_carteles(conn, CARTELES_SINTETICO, "sintetico", raw)
        assert conn.execute("SELECT tipo_procedimiento FROM tenders WHERE nro_sicop = '20269900001'").fetchone() == (
            "Licitación Reducida",)  # el importador guarda el tipo
        panel.guardar_revision(conn, "20269900001", "revisar_requisitos", "", "Pedir el pliego", _usuario(conn), AHORA)

    modificado = tmp_path / "carteles_v2.csv"
    modificado.write_bytes(CARTELES_SINTETICO.read_bytes().replace(
        b"monitoreo GPS de flotilla vehicular;", b"monitoreo GPS de flotilla vehicular (enmienda);"))
    with closing(connect(db)) as conn:
        r = import_carteles(conn, modificado, "sintetico", raw)
        assert r.actualizadas == 1
        assert conn.execute("SELECT descripcion FROM tenders WHERE nro_sicop = '20269900001'").fetchone()[0].endswith(
            "(enmienda)")
        assert conn.execute("SELECT decision, comment FROM reviews WHERE nro_sicop = '20269900001'").fetchall() == [
            ("revisar_requisitos", "Pedir el pliego")]


# --- Rutas web ---------------------------------------------------------------------------------------------------

def test_inicio_redirige_a_la_lista(cliente):
    respuesta = cliente.get("/", follow_redirects=False)

    assert respuesta.status_code == 307 and respuesta.headers["location"] == "/oportunidades"


def test_lista_web_filtra_y_escapa_html(cliente):
    respuesta = cliente.get("/oportunidades")

    assert respuesta.status_code == 200
    assert "00000000001" in respuesta.text and "00000000003" not in respuesta.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in respuesta.text
    assert "<script>alert(1)" not in respuesta.text
    assert "Las reglas cambiaron" not in respuesta.text

    filtrada = cliente.get("/oportunidades", params={"familia": "camaras_corporales"})
    assert "00000000004" in filtrada.text and "00000000001" not in filtrada.text


def test_detalle_web_resalta_la_evidencia(cliente):
    respuesta = cliente.get("/oportunidades/00000000001")

    assert respuesta.status_code == 200
    assert "<mark>monitoreo GPS</mark>" in respuesta.text
    assert "senales_alta: monitoreo gps" in respuesta.text
    assert "Municipalidad Sintética A" in respuesta.text and "Licitación Reducida" in respuesta.text


def test_detalle_de_un_cartel_que_no_existe(cliente):
    assert cliente.get("/oportunidades/99999999999").status_code == 404


def test_revision_web_valida_y_persiste(cliente, db):
    token = token_csrf(cliente.get("/oportunidades/00000000002").text)
    sin_motivo = cliente.post("/oportunidades/00000000002/revision",
                              data={"decision": "no_interesa", "responsable": "Ivania", "comentario": "Caro",
                                    "csrf_token": token})
    assert sin_motivo.status_code == 400
    assert "hay que elegir el motivo" in sin_motivo.text
    assert "Caro" in sin_motivo.text  # lo escrito no se pierde

    guardada = cliente.post("/oportunidades/00000000002/revision", follow_redirects=False,
                            data={"decision": "no_interesa", "motivo": "presupuesto", "responsable": "Ivania",
                                  "comentario": "Caro", "csrf_token": token})
    assert guardada.status_code == 303
    assert guardada.headers["location"] == "/oportunidades/00000000002#revisiones"

    detalle = cliente.get("/oportunidades/00000000002").text
    assert "No interesa" in detalle and "Presupuesto" in detalle and "Caro" in detalle
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 1


def test_revision_web_se_guarda_a_nombre_de_la_sesion_aunque_el_formulario_diga_otro(cliente, db):
    pagina = cliente.get("/oportunidades/00000000002").text
    assert 'name="responsable"' not in pagina and "Se guarda a nombre de <strong>Ivania</strong>" in pagina

    cliente.post("/oportunidades/00000000002/revision",
                 data={"decision": "interesa", "responsable": "Oscar", "csrf_token": token_csrf(pagina)})

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT u.email, r.responsable FROM reviews r JOIN users u ON u.id = r.user_id"
                            ).fetchall() == [("ivania@ejemplo.test", "Ivania")]
    assert "(escrito a mano)" not in cliente.get("/oportunidades/00000000002").text


def test_aviso_si_las_reglas_cambiaron(cliente, db, tmp_path):
    otras = tmp_path / "reglas.yaml"
    otras.write_text('familias:\n  gps_flotas:\n    producto: fleetmatix\n    senales_alta: ["gps"]\n',
                     encoding="utf-8")
    with closing(connect(db)) as conn:
        evaluar_base(conn, cargar_reglas(otras), AHORA)  # la última evaluación ya no es la del YAML actual

    assert "Las reglas cambiaron" in cliente.get("/oportunidades").text


def test_base_sin_migrar(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "no_existe.db"))

    respuesta = iniciar_sesion(TestClient(app))  # sin base no hay usuarios: lo dice el login

    assert respuesta.status_code == 503 and "migrate" in respuesta.text


# --- Portada: contadores, cuenta regresiva y montos ------------------------------------------------

@pytest.mark.parametrize("delta, texto", [
    (timedelta(days=3, hours=2), "Cierra en 3 días"),
    (timedelta(days=1, hours=1), "Cierra en 1 día"),
    (timedelta(hours=5, minutes=10), "Cierra en 5 h"),
    (timedelta(minutes=20), "Cierra en menos de 1 h"),
    (timedelta(hours=-2), "Cerró hoy"),
    (timedelta(days=-12, hours=-1), "Cerró hace 12 días"),
])
def test_cuenta_regresiva(delta, texto):
    assert panel.cuenta_regresiva((AHORA + delta).isoformat(), AHORA) == texto


def test_cuenta_regresiva_sin_fecha_o_sin_zona():
    assert panel.cuenta_regresiva(None, AHORA) == panel.cuenta_regresiva("2026-11-30T10:00:00", AHORA) == "Sin fecha de cierre"


def test_lista_suma_las_lineas_por_moneda_sin_mezclarlas(db):
    t = "2026-10-01T00:00:00+00:00"
    with closing(connect(db)) as conn:
        conn.executemany(
            "INSERT INTO tender_lines (nro_sicop, numero_linea, estimado_linea, moneda, content_hash, first_seen, last_seen)"
            " VALUES ('00000000001', ?, ?, ?, 'h', ?, ?)",
            [("1", "1000.50", "CRC", t, t), ("2", "2000", "CRC", t, t), ("3", "15.25", "USD", t, t)])

    fila = _listar(db).filas[0]

    assert {m: str(v.valor) for m, v in fila.estimado.items()} == {"CRC": "3000.50", "USD": "15.25"}
    assert panel.monto(fila.estimado["CRC"].valor, "CRC") == "3 000.50 CRC"


# --- Lista en tarjetas: buscador, chips de decisión y «Nuevo» -------------------------------------

@pytest.mark.parametrize("q, esperado", [
    ("flotilla", ["00000000002"]),
    ("ministerio sintético", ["00000000002", "00000000004"]),   # institución, sin distinguir mayúsculas
    ("0000000004", ["00000000004"]),                           # Número SICOP
    ("100%_", []),                                             # comodines tomados como texto
])
def test_buscador(db, q, esperado):
    assert _nros(_listar(db, q=q)) == esperado


def test_chips_filtran_por_decision(db):
    _revisar(db, "00000000001", "interesa")
    _revisar(db, "00000000002", "no_interesa", motivo="plazo")

    assert _nros(_listar(db, revisado="interesa")) == ["00000000001"]
    assert _nros(_listar(db, revisado="no_interesa")) == ["00000000002"]
    assert _nros(_listar(db, revisado="revisar_requisitos")) == []


def test_nuevo_es_lo_que_llego_en_la_ultima_importacion(db):
    t = "2026-10-01T00:00:00+00:00"
    with closing(connect(db)) as conn:
        for n in (1, 2):
            conn.execute("INSERT INTO imports (report, file_name, file_hash, data_origin, imported_at)"
                         " VALUES ('carteles', ?, ?, 'sintetico', ?)", (f"c{n}.csv", f"h{n}", t))
        conn.execute("UPDATE tenders SET first_import_id = 1")
        conn.execute("UPDATE tenders SET first_import_id = 2 WHERE nro_sicop = '00000000004'")

    assert {f.nro_sicop: f.es_nuevo for f in _listar(db).filas} == {
        "00000000001": False, "00000000002": False, "00000000004": True}


def test_tarjeta_web_muestra_datos_clave_y_palabras_detectadas(cliente):
    texto = cliente.get("/oportunidades").text

    assert 'class="card' in texto and "Monto estimado" in texto and "Cierre de ofertas" in texto
    assert "Palabras clave detectadas" in texto and "monitoreo GPS" in texto
    assert "Me interesa" not in texto  # la revisión se hace en el detalle, no con botones en la lista
    assert "Oportunidades para Hermatix" not in texto and "Por familia" not in texto


def test_espacios_duros_se_muestran_como_normales_para_poder_cortar_la_linea(cliente, db):
    with closing(connect(db)) as conn:
        conn.execute("UPDATE tenders SET descripcion = 'Servicio de monitoreo GPS de vehículos'"
                     " WHERE nro_sicop = '00000000001'")
        evaluar_base(conn, cargar_reglas(), AHORA)

    lista = cliente.get("/oportunidades").text
    detalle = cliente.get("/oportunidades/00000000001").text

    assert "Servicio de monitoreo GPS de vehículos" in lista and " " not in lista
    assert "<mark>monitoreo GPS</mark>" in detalle and " " not in detalle
    with closing(sqlite3.connect(db)) as conn:  # el texto guardado no cambia
        assert " " in conn.execute("SELECT descripcion FROM tenders WHERE nro_sicop = '00000000001'").fetchone()[0]


# --- Títulos en MAYÚSCULAS → mayúscula inicial (solo al mostrar) ------------------------------------

@pytest.mark.parametrize("original, esperado", [
    ("COMPRA DE CÁMARAS CORPORALES BODY CAM PARA INSPECTORES", "Compra de cámaras corporales body cam para inspectores"),
    ("ALQUILER SISTEMA DE MONITOREO GPS PARA LA FLOTA", "Alquiler sistema de monitoreo GPS para la flota"),
    ("II ETAPA: MANTENIMIENTO SM5697 / L-352-2026 PARA LA CCSS", "II etapa: mantenimiento SM5697 / L-352-2026 para la CCSS"),
    ("SOLUCIÓN IOT PARA AYA", "Solución IoT para AyA"),
    ("Contratación de monitoreo GPS para la Municipalidad de Desamparados",   # ya trae minúsculas: no se toca
     "Contratación de monitoreo GPS para la Municipalidad de Desamparados"),
    ("Insumos varios II", "Insumos varios II"),
    ("compra medidor de condiciones ambientales", "Compra medidor de condiciones ambientales"),  # mayúscula inicial
    ("SERVICIO DE GPS", "Servicio de GPS"),     # mismo largo; los NBSP los cambia «legible»
])
def test_formato_titulo(original, esperado):
    assert panel.formato_titulo(original) == esperado


def test_titulo_en_mayusculas_se_muestra_con_mayuscula_inicial_y_conserva_el_resaltado(cliente, db):
    with closing(connect(db)) as conn:
        conn.execute("UPDATE tenders SET descripcion = 'SERVICIO DE MONITOREO GPS DE VEHÍCULOS' WHERE nro_sicop = '00000000001'")
        evaluar_base(conn, cargar_reglas(), AHORA)

    assert "Servicio de monitoreo GPS de vehículos" in cliente.get("/oportunidades").text
    # «vehículos» también se marca: es un término de contexto de la regla.
    assert "Servicio de <mark>monitoreo GPS</mark> de <mark>vehículos</mark>" in cliente.get("/oportunidades/00000000001").text
