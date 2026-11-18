"""La oferta completa en Word (app/propuesta_word.py; DECISION_IA.md §10.6 bis): el mismo documento que el PDF.

Reusa la base, el pliego, los requisitos, los documentos y las tarifas SINTÉTICOS de tests/test_propuesta.py. Nunca
se llama a OpenAI (IA SIMULADA) ni a Chromium: el Word lo escribe python-docx.
"""

import hashlib
import io
from contextlib import closing
from types import SimpleNamespace

from docx import Document

from app import propuesta, propuesta_word
from app.database import connect
from tests.test_propuesta import (ANA, AHORA, Impresora, OpenAISimulado, _acciones, _armar, _oferta, _pliego,
                                  _requisitos, _settings, _tarifas, panel_oferta)  # noqa: F401
from tests.test_seguimiento import NRO, _dar_seguimiento, clientes, db  # noqa: F401


def _word(db, settings, simulado=None, tarifas=None):
    with closing(connect(db)) as conn:
        return propuesta.armar_word(conn, settings, NRO, ANA, AHORA, cliente=simulado, dormir=lambda s: None,
                                    tarifas=tarifas)


def _texto(doc) -> str:
    """Todo el texto del cuerpo: párrafos y tablas, en orden de aparición aproximado."""
    partes = [p.text for p in doc.paragraphs]
    for tabla in doc.tables:
        for fila in tabla.rows:
            partes += [c.text for c in fila.cells]
    return " ".join(" ".join(partes).split())


def _huellas(carpeta) -> dict:
    return {r: hashlib.sha256(r.read_bytes()).hexdigest() for r in sorted(carpeta.rglob("*")) if r.is_file()}


def test_la_oferta_en_word_tiene_lo_mismo_que_el_pdf(db, tmp_path):
    settings = _settings(db, tmp_path)
    _pliego(db)
    _requisitos(db, settings)
    simulado = OpenAISimulado()
    antes = _huellas(tmp_path / "asistente")

    armada = _word(db, settings, simulado, _tarifas(db))

    assert armada.contenido[:2] == b"PK"                                  # un .docx es un ZIP
    doc = Document(io.BytesIO(armada.contenido))
    texto = _texto(doc)
    assert "OFERTA" in texto and "BORRADOR: hay" in texto
    assert texto.count("Respuesta Sección") == 4                          # la sección inventada se descartó
    assert "Reporte de posición cada 60 segundos (SINTÉTICO)." in texto    # el pliego se copia tal cual
    assert "Respuesta Sección 01 – Llamado a Cotizar Entendemos y aceptamos lo indicado." in texto
    assert "Listado de Anexos:" in texto and "Anexo 2.1" in texto and "Ficha técnica del equipo ofertado" in texto
    assert "Doscientos veintiséis mil colones exactos." in texto           # la oferta económica, calculada por la app
    assert "*****Última Línea********" in texto and "DESGLOSE DE PRECIO" in texto and "Fórmula Matemática" in texto
    # La sección 4 no cumple: su respuesta sale en rojo, como en el PDF.
    respuesta4 = next(p for p in doc.paragraphs if p.text.startswith("Respuesta Sección 04"))
    assert respuesta4.runs[0].font.color.rgb == propuesta_word.ROJO
    # Adjuntos: la patente (PDF de 2 páginas) y la declaración (JPG), como imágenes; los originales no cambian.
    assert len(doc.inline_shapes) == 2 + 1
    assert _huellas(tmp_path / "asistente") == antes
    # Membrete de Hermatix arriba y abajo, y tamaño carta.
    seccion = doc.sections[0]
    assert seccion.header.paragraphs[0]._p.xml.count("<pic:pic") == 1
    assert round(seccion.page_width.mm) == 216 and round(seccion.page_height.mm) == 279
    assert _acciones(db, "generar_oferta_word") == 1 and _acciones(db, "adjuntar_documento_oferta") == 2

    # El PDF sale de los mismos datos: los mismos pendientes.
    pdf = _armar(db, settings, simulado, Impresora(), _tarifas(db))
    assert pdf.pendientes == armada.pendientes
    assert len(simulado.llamadas) == 1                                    # mismo pliego: la IA no se repite


def test_sin_tarifa_el_word_dice_precio_pendiente(db, tmp_path):
    settings = _settings(db, tmp_path)
    _pliego(db)
    armada = _word(db, settings, OpenAISimulado(), tarifas={})
    texto = _texto(Document(io.BytesIO(armada.contenido)))
    assert "PRECIO PENDIENTE" in texto and "Monto en Letras" not in texto
    assert any(p.startswith("PRECIO PENDIENTE") for p in armada.pendientes)


def test_caracteres_raros_del_pliego_no_rompen_el_word():
    # Algunos PDF traen caracteres de control (salto de página, etc.) que un .docx no admite: se quitan.
    bloque = propuesta.Bloque("1", "SECCIÓN\x01 SINTÉTICA", "Texto\x0c con\x01 control (SINTÉTICO)",
                              respuesta=["Entendemos y aceptamos lo indicado.\x0b"])
    doc = propuesta_word._preparar_documento()
    propuesta_word._pliego(doc, SimpleNamespace(bloques=[bloque]))
    salida = io.BytesIO()
    doc.save(salida)
    texto = _texto(Document(io.BytesIO(salida.getvalue())))
    assert "Texto con control (SINTÉTICO)" in texto and "1. SECCIÓN SINTÉTICA" in texto


def test_el_boton_entrega_el_word_y_guarda_una_copia(panel_oferta, db, tmp_path):  # noqa: F811
    oscar = panel_oferta["oscar"]
    _dar_seguimiento(oscar)
    _pliego(db)
    pagina = oscar.get(f"/oportunidades/{NRO}").text
    assert 'name="formato" value="docx"' in pagina and "Oferta en Word" in pagina
    token = _token(pagina)
    r = oscar.post(f"/oportunidades/{NRO}/oferta", data={"csrf_token": token, "formato": "docx"},
                   follow_redirects=False)
    assert r.status_code == 200
    assert r.headers["content-type"] == propuesta_word_tipo()
    assert r.content[:2] == b"PK" and f'oferta_{NRO}_' in r.headers["content-disposition"]
    assert r.headers["content-disposition"].endswith('.docx"')
    assert list((tmp_path / "exports" / "ofertas").rglob("oferta_*.docx"))
    assert _acciones(db, "generar_oferta_word") == 1 and _acciones(db, "generar_oferta") == 0


def _token(pagina: str) -> str:
    from tests.test_panel import token_csrf
    return token_csrf(pagina)


def propuesta_word_tipo() -> str:
    from app.web.rutas import TIPOS_OFERTA
    return TIPOS_OFERTA["docx"]
