"""Lo que el asistente pide para la oferta (app/oferta_datos.py; migración 0048; pedido de Ivania, 2026-11-18).

Base, usuarios y cartel SINTÉTICOS de tests/test_seguimiento.py; pliego, precios, fichas y representante INVENTADOS.
Nunca se llama a OpenAI: con AI_MODE=none la oferta no pide secciones.
"""

import importlib.util
import io
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app import oferta_datos, propuesta
from app.ai import oferta as ia_oferta
from app.database import connect
from tests.test_panel import token_csrf
from tests.test_propuesta import (AHORA, ANA, Impresora, _acciones, _armar, _pdf, _pliego, _settings,  # noqa: F401
                                  panel_oferta)
from tests.test_seguimiento import NRO, _asignar, _dar_seguimiento, _id, clientes, db  # noqa: F401

DOCS = Path(__file__).parent / "fixtures" / "documentos_simulados"
_spec = importlib.util.spec_from_file_location("hacer_documentos", DOCS / "hacer_documentos.py")
hacer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hacer)

DESGLOSE = {"mano_de_obra": "30", "insumos": "40", "gastos_administrativos": "15", "utilidad": "15"}


def _precio(db, precio="20000.00", desglose=None, **extra):
    campos = {"moneda": "CRC", "precio_unitario": precio, "periodo": "unico", "iva_modo": "tasa", "iva_tasa": "13",
              "iva_exento": "", "desglose": desglose or DESGLOSE, **extra}
    with closing(connect(db)) as conn:
        return oferta_datos.guardar_precio(conn, NRO, quien=ANA, ahora=AHORA, **campos)


def _falta(db, settings):
    with closing(connect(db)) as conn:
        return propuesta.lo_que_falta(conn, settings, NRO, AHORA, tarifas={})


def _textos(faltas):
    return " | ".join(f.texto for f in faltas)


# --- Precio del cartel ---------------------------------------------------------------------------------------------

def test_el_precio_del_cartel_manda_sobre_el_tarifario_y_el_historial_no_lleva_montos(db, tmp_path):
    settings = _settings(db, tmp_path, ia=False)
    _pliego(db)
    assert "PRECIO PENDIENTE" in _textos(_falta(db, settings))
    guardado = _precio(db)
    assert guardado.precio == "20000.00" and guardado.desglose["insumos"] == "40"        # Decimal como texto
    assert "PRECIO PENDIENTE" not in _textos(_falta(db, settings))
    impresora = Impresora()
    armada = _armar(db, settings, None, impresora, tarifas={})
    assert not any(p.startswith("PRECIO PENDIENTE") for p in armada.pendientes)
    economica = next(h for h in impresora.html if "Monto en Letras" in h)
    assert "Ciento ochenta mil ochocientos colones exactos." in economica              # 8 × 20 000 + 13 %
    with closing(connect(db)) as conn:
        detalle = conn.execute("SELECT detalle FROM audit_log WHERE accion = 'guardar_precio_oferta'").fetchone()[0]
    assert detalle == NRO and "20000" not in detalle


@pytest.mark.parametrize("cambio, mensaje", [
    ({"desglose": {**DESGLOSE, "utilidad": "20"}}, "sumar 100"),
    ({"precio": "0"}, "mayor que cero"),
    ({"precio": "veinte mil"}, "no es un número"),
    ({"moneda": "EUR"}, "moneda"),
    ({"iva_modo": "exento"}, "motivo"),
])
def test_un_precio_que_no_sirve_no_se_guarda(db, cambio, mensaje):
    with pytest.raises(oferta_datos.DatoInvalido, match=mensaje):
        _precio(db, **cambio)
    with closing(connect(db)) as conn:
        assert oferta_datos.precio(conn, NRO) is None


def test_cambiar_el_precio_agrega_una_fila_y_nada_se_borra(db):
    _precio(db, "20000.00")
    _precio(db, "21000.50")
    with closing(connect(db)) as conn:
        assert oferta_datos.precio(conn, NRO).precio == "21000.50"
        assert conn.execute("SELECT count(*) FROM oferta_precios").fetchone()[0] == 2
        for sql in ("DELETE FROM oferta_precios", "UPDATE oferta_precios SET precio = '1'"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


# --- Producto y ficha técnica --------------------------------------------------------------------------------------

def test_la_ficha_va_como_anexo_3_con_su_producto(db, tmp_path):
    settings = _settings(db, tmp_path, ia=False)
    _pliego(db)
    assert "Ficha técnica del equipo ofertado" in _textos(_falta(db, settings))
    with closing(connect(db)) as conn:
        with pytest.raises(oferta_datos.DatoInvalido, match="producto"):
            oferta_datos.guardar_ficha(conn, settings, NRO, "inventado", io.BytesIO(_pdf()), "ficha.pdf", ANA, AHORA)
        with pytest.raises(oferta_datos.ArchivoInvalido, match="no es un PDF"):
            oferta_datos.guardar_ficha(conn, settings, NRO, "fenova_ia", io.BytesIO(b"MZ no soy pdf"), "ficha.pdf",
                                       ANA, AHORA)
        ficha = oferta_datos.guardar_ficha(conn, settings, NRO, "fenova_ia", io.BytesIO(_pdf(2)),
                                           r"C:\Users\x\Ficha Fenova.pdf", ANA, AHORA)
        assert ficha.nombre == "Ficha Fenova.pdf" and (settings.assistant_docs_dir / ficha.ruta).is_file()
        anexo = next(a for a in propuesta.anexos(conn, settings, NRO, ANA, []) if a.grupo == 3)
    assert anexo.pendiente is None and anexo.titulo.endswith("(Fenova IA)") and anexo.ruta.is_file()
    assert "Ficha técnica" not in _textos(_falta(db, settings))
    _armar(db, settings, None, Impresora(), tarifas={})
    assert _acciones(db, "adjuntar_documento_oferta") == 1 and _acciones(db, "subir_ficha_oferta") == 1


# --- Pliego subido -------------------------------------------------------------------------------------------------

def test_sin_pliego_de_sicop_sirve_el_que_sube_una_persona(db, tmp_path):
    settings = _settings(db, tmp_path, ia=False)
    assert _falta(db, settings)[0].texto.startswith("Falta el pliego")
    with closing(connect(db)) as conn:
        with pytest.raises(oferta_datos.DatoInvalido, match="texto"):
            oferta_datos.guardar_pliego(conn, settings, NRO, io.BytesIO((DOCS / "escaneado.pdf").read_bytes()),
                                        "escaneado.pdf", ANA, AHORA)
        assert oferta_datos.pliego(conn, NRO) is None
        p = oferta_datos.guardar_pliego(conn, settings, NRO, io.BytesIO(hacer.pdf_con_texto(
            ["1. OBJETO (SINTÉTICO)", "2. REQUISITOS (SINTÉTICO)"])), "pliego.pdf", ANA, AHORA)
        assert p.paginas == 2
        paginas = ia_oferta.paginas_del_pliego(conn, NRO)
    assert [(x.doc, x.pagina) for x in paginas] == [(0, 1), (0, 2)] and paginas[0].archivo == "subido: pliego.pdf"
    assert not _textos(_falta(db, settings)).startswith("Falta el pliego")


def test_el_pliego_de_sicop_manda_sobre_el_subido(db, tmp_path):
    settings = _settings(db, tmp_path, ia=False)
    with closing(connect(db)) as conn:
        oferta_datos.guardar_pliego(conn, settings, NRO, io.BytesIO(hacer.pdf_con_texto(["SUBIDO (SINTÉTICO)"])),
                                    "pliego.pdf", ANA, AHORA)
    _pliego(db)
    with closing(connect(db)) as conn:
        assert {x.doc for x in ia_oferta.paginas_del_pliego(conn, NRO)} == {1}


# --- Representante legal -------------------------------------------------------------------------------------------

def test_el_representante_vale_para_todas_las_ofertas_y_la_cedula_no_va_al_historial(db, tmp_path):
    settings = _settings(db, tmp_path, ia=False)
    _pliego(db)
    with closing(connect(db)) as conn:
        with pytest.raises(oferta_datos.DatoInvalido, match="cédula"):
            oferta_datos.guardar_representante(conn, nombre="Persona Sintética Uno", cedula="abc", calidades="",
                                               cargo="", quien=ANA, ahora=AHORA)
        oferta_datos.guardar_representante(conn, nombre="Persona  Sintética Uno", cedula="0-0000-0001",
                                           calidades="mayor", cargo="", quien=ANA, ahora=AHORA)
        rep = oferta_datos.representante(conn)
        detalle = conn.execute("SELECT detalle FROM audit_log WHERE accion = 'guardar_representante'").fetchone()[0]
    assert rep["nombre"] == "Persona Sintética Uno" and rep["cedula"] == "0-0000-0001"    # texto, con su cero
    assert rep["cargo"] == "representante legal" and "0001" not in detalle
    assert "representante legal" not in _textos(_falta(db, settings))
    _precio(db)                                                       # sin precio no se imprime la carta
    impresora = Impresora()
    armada = _armar(db, settings, None, impresora, tarifas={})
    assert not any("representante legal" in p for p in armada.pendientes)
    assert "Persona Sintética Uno" in " ".join(impresora.html)


# --- En la página del asistente --------------------------------------------------------------------------------------

def _post(cliente, ruta, datos=None, archivos=None):
    token = token_csrf(cliente.get(f"/oportunidades/{NRO}/asistente").text)
    return cliente.post(ruta, data={"csrf_token": token, **(datos or {})}, files=archivos, follow_redirects=False)


def test_el_asistente_pide_todo_con_su_formulario(panel_oferta, db):
    oscar, ivania, ana = panel_oferta["oscar"], panel_oferta["ivania"], panel_oferta["ana"]
    _dar_seguimiento(oscar)
    _asignar(oscar, _id(db, "ivania@ejemplo.test"))
    html = ivania.get(f"/oportunidades/{NRO}/asistente").text
    for ancla in ("oferta-pliego", "oferta-precio", "oferta-ficha"):          # cada punto, con su «Resolver»
        assert f'id="{ancla}"' in html and f'href="#{ancla}">Resolver</a>' in html
    # El representante lo llena un administrador: la encargada no ve el formulario ni puede mandarlo.
    assert "Lo llena un administrador" in html and 'name="cedula"' not in html
    assert 'name="cedula"' in oscar.get(f"/oportunidades/{NRO}/asistente").text
    rep = {"nombre": "Persona Sintética Uno", "cedula": "0-0000-0001"}
    assert _post(ivania, f"/oportunidades/{NRO}/asistente/oferta/representante", rep).status_code == 403

    precio = {"moneda": "CRC", "precio": "20000", "periodo": "mensual", "iva_modo": "tasa", "iva_tasa": "13",
              **{f"des_{k}": v for k, v in DESGLOSE.items()}}
    r = _post(ivania, f"/oportunidades/{NRO}/asistente/oferta/precio", {**precio, "des_utilidad": "50"})
    assert r.status_code == 400 and "sumar 100" in r.text and 'value="50"' in r.text   # lo escrito no se pierde
    r = _post(ivania, f"/oportunidades/{NRO}/asistente/oferta/precio", precio)
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}/asistente#oferta-precio"
    r = _post(ivania, f"/oportunidades/{NRO}/asistente/oferta/ficha", {"producto": "bodycams"},
              {"archivo": ("ficha.pdf", _pdf(), "application/pdf")})
    assert r.status_code == 303
    r = _post(ivania, f"/oportunidades/{NRO}/asistente/oferta/pliego", None,
              {"archivo": ("pliego.pdf", hacer.pdf_con_texto(["1. OBJETO (SINTÉTICO)"]), "application/pdf")})
    assert r.status_code == 303
    assert _post(oscar, f"/oportunidades/{NRO}/asistente/oferta/representante", rep).status_code == 303
    with closing(connect(db)) as conn, conn:                          # una línea SINTÉTICA para cotizar
        conn.execute("INSERT INTO tender_lines (nro_sicop, numero_linea, codigo_identificacion, cantidad_solicitada,"
                     " precio_unitario_estimado, estimado_linea, moneda, content_hash, first_seen, last_seen)"
                     " VALUES (?, '1', '0000000000000000', '8', '30000.00', '240000.00', 'CRC', 'h', ?, ?)",
                     (NRO, "2026-10-01T00:00:00+00:00", "2026-10-01T00:00:00+00:00"))
        conn.execute("UPDATE tenders SET nro_procedimiento = '2026LD-000099-0009999999' WHERE nro_sicop = ?", (NRO,))
    html = ivania.get(f"/oportunidades/{NRO}/asistente").text
    assert "CRC 20000" in html and "BodyCams" in html and "Persona Sintética Uno" in html
    assert "0-0000-0001" not in html                                  # la cédula solo la ve el administrador
    assert "Falta el pliego" not in html and "PRECIO PENDIENTE" not in html
    # Otra encargada no entra; sin token CSRF tampoco.
    assert _post(ana, f"/oportunidades/{NRO}/asistente/oferta/precio", precio).status_code == 403
    assert ivania.post(f"/oportunidades/{NRO}/asistente/oferta/precio", data=precio).status_code in (400, 403)
