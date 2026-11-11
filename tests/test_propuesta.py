"""Oferta completa con un botón (app/propuesta.py, app/ai/oferta.py; DECISION_PROPUESTA.md §12).

Base, usuarios y cartel SINTÉTICOS de tests/test_seguimiento.py; pliego, requisitos, documentos y tarifas INVENTADOS
en tmp_path. Nunca se llama a OpenAI (IA SIMULADA). La impresión a PDF es simulada (una página en blanco por hoja)
salvo en la prueba marcada con el navegador.
"""

import io
import json
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace

import pypdfium2 as pdfium
import pytest
from PIL import Image

from app import asistente, propuesta
from app.ai import oferta as ia_oferta
from app.ai import verificacion
from app.config import load_settings
from app.database import connect
from app.historial import Quien
from tests.test_enriquecimiento import navegador
from tests.test_panel import token_csrf
from tests.test_seguimiento import NRO, OTRO, _asignar, _dar_seguimiento, _id, clientes, db  # noqa: F401

ANA = Quien(None, "Ana Sintética")
AHORA = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)
PAGINAS = [
    "1. LLAMADO A COTIZAR\nLa institución recibirá ofertas solo por SICOP (SINTÉTICO).\n"
    "2. ASPECTOS GENERALES\nLa oferta debe venir firmada digitalmente (SINTÉTICO).",
    "3. REQUISITOS DE ADMISIBILIDAD\nPatente municipal vigente y experiencia mínima de tres años (SINTÉTICO).",
    "4. ESPECIFICACIONES TÉCNICAS\nReporte de posición cada 60 segundos (SINTÉTICO).",
]
SECCIONES = [
    {"numero": "1", "titulo": "LLAMADO A COTIZAR", "doc": "1", "pagina": "1",
     "inicio_literal": "1. LLAMADO A COTIZAR La institución recibirá ofertas", "tipo_respuesta": "acepta"},
    {"numero": "2", "titulo": "ASPECTOS GENERALES", "doc": "1", "pagina": "1",
     "inicio_literal": "2. ASPECTOS GENERALES La oferta debe venir", "tipo_respuesta": "acepta"},
    {"numero": "3", "titulo": "REQUISITOS DE ADMISIBILIDAD", "doc": "1", "pagina": "2",
     "inicio_literal": "3. REQUISITOS DE ADMISIBILIDAD Patente municipal", "tipo_respuesta": "cumple"},
    {"numero": "4", "titulo": "ESPECIFICACIONES TÉCNICAS", "doc": "1", "pagina": "3",
     "inicio_literal": "4. ESPECIFICACIONES TÉCNICAS Reporte de posición", "tipo_respuesta": "cumple"},
    {"numero": "9", "titulo": "INVENTADA", "doc": "1", "pagina": "3",          # no está en el texto: se descarta
     "inicio_literal": "9. SECCIÓN QUE NO EXISTE en el pliego", "tipo_respuesta": "cumple"},
]


class OpenAISimulado:
    """Imita client.responses.create: devuelve las secciones de arriba y anota cada llamada."""

    def __init__(self):
        self.llamadas = []
        self.responses = SimpleNamespace(create=self._crear)

    def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps({"secciones": SECCIONES}), output=[],
                               model="modelo-simulado", usage=SimpleNamespace(input_tokens=900, output_tokens=200),
                               incomplete_details=None)


class Impresora:
    """Imita oferta_economica.pdf: un PDF con una página en blanco por hoja y guarda el HTML para revisarlo."""

    def __init__(self):
        self.html = []

    def principal(self) -> str:
        return " ".join(next(h for h in self.html if "Listado de Anexos" in h).split())

    def __call__(self, contenido_html, procedimiento):
        self.html.append(contenido_html)
        return _pdf(max(1, contenido_html.count('<section class="hoja"')))


def _pdf(paginas=1) -> bytes:
    doc = pdfium.PdfDocument.new()
    for _ in range(paginas):
        doc.new_page(612, 792)
    salida = io.BytesIO()
    doc.save(salida)
    return salida.getvalue()


def _jpg() -> bytes:
    salida = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 200, 200)).save(salida, "JPEG")
    return salida.getvalue()


def _paginas(doc: bytes) -> int:
    d = pdfium.PdfDocument(doc)
    try:
        return len(d)
    finally:
        d.close()


def _settings(db, tmp_path, ia=True, **extra):
    valores = {"DATABASE_PATH": str(db), "ASSISTANT_DOCS_DIR": str(tmp_path / "asistente"),
               "PROFILE_DOCS_DIR": str(tmp_path / "perfil"), "EXPORTS_DIR": str(tmp_path / "exports"),
               "ASSISTANT_DOC_MAX_MB": "1", "AI_MODE": "none"}
    if ia:
        valores.update({"AI_MODE": "openai", "OPENAI_API_KEY": "clave-simulada", "OPENAI_MODEL": "modelo-simulado",
                        "IA_PRECIO_ENTRADA_USD": "1.00", "IA_PRECIO_SALIDA_USD": "5.00", "IA_MAX_DAILY_COST": "1.00"})
    return load_settings(env_file=None, environ={**valores, **extra})


def _pliego(db, nro=NRO):
    """Ficha y pliego SINTÉTICOS del cartel: DOC 1, tres páginas con texto."""
    with closing(connect(db)) as conn, conn:
        conn.execute("BEGIN")
        detalle = conn.execute(
            "INSERT INTO tender_details (nro_sicop, consultado_en, content_hash, copia_fiel, campos_quitados)"
            " VALUES (?, '2026-11-10T10:00:00-06:00', 'h-ficha', '{}', '[]')", (nro,)).lastrowid
        doc = conn.execute(
            "INSERT INTO tender_documents (nro_sicop, detalle_id, tipo_documento, nombre_documento, nombre_original,"
            " server_file, extension, tamano_bytes, sha256, ruta_local, registrado_en, estado, texto_estado, paginas)"
            " VALUES (?, ?, 'Pliego', 'Pliego de condiciones', 'pliego.pdf', 'srv-1', '.pdf', 100, ?, 'x/pliego.pdf',"
            " '2026-11-10T10:00:00-06:00', 'guardado', 'extraido', 3)", (nro, detalle, "a" * 64)).lastrowid
        conn.executemany("INSERT INTO tender_document_text (documento_id, pagina, texto) VALUES (?, ?, ?)",
                         [(doc, n, t) for n, t in enumerate(PAGINAS, start=1)])
        conn.execute("UPDATE tenders SET nro_procedimiento = '2026LD-000099-0009999999',"
                     " tipo_procedimiento = 'Licitación Reducida' WHERE nro_sicop = ?", (nro,))
        conn.execute("INSERT INTO tender_lines (nro_sicop, numero_linea, codigo_identificacion, cantidad_solicitada,"
                     " precio_unitario_estimado, estimado_linea, moneda, content_hash, first_seen, last_seen)"
                     " VALUES (?, '1', '0000000000000000', '8', '30000.00', '240000.00', 'CRC', 'h', ?, ?)",
                     (nro, "2026-10-01T00:00:00+00:00", "2026-10-01T00:00:00+00:00"))
        conn.execute("COMMIT")


def _requisitos(db, settings):
    """Requisitos del asistente: patente (PDF), declaración (JPG) y experiencia en la pág. 2; reporte en la pág. 3,
    respondido «No» (no cumple)."""
    def req(texto, evidencia, excluyente=False, minimo="", numero="", unidad=""):
        return verificacion.Cambios(texto, "legal", evidencia, minimo, numero, "", unidad, excluyente)
    with closing(connect(db)) as conn:
        ids = {
            "patente": verificacion.agregar(conn, NRO, req("Aportar patente municipal vigente. [DOC 1 · pág. 2]",
                                                           "documento"), ANA),
            "declaracion": verificacion.agregar(conn, NRO, req("Declaración jurada de no prohibición. [DOC 1 · pág. 2]",
                                                               "documento"), ANA),
            "anos": verificacion.agregar(conn, NRO, req("Al menos tres años de experiencia. [DOC 1 · pág. 2]",
                                                        "numero", True, "al menos 3 años", "3", "años"), ANA),
            "reporte": verificacion.agregar(conn, NRO, req("Reporte de posición cada 60 s. [DOC 1 · pág. 3]",
                                                           "si_no"), ANA),
        }
        asistente.empezar(conn, NRO, ANA, AHORA)
        for clave, entrada, archivo in (
                ("patente", asistente.Entrada(), (io.BytesIO(_pdf(2)), "patente.pdf")),
                ("declaracion", asistente.Entrada(), (io.BytesIO(_jpg()), "declaracion.jpg")),
                ("anos", asistente.Entrada(valor_numero="8"), None),
                ("reporte", asistente.Entrada(valor_si_no="0"), None)):
            asistente.responder(conn, settings, NRO, ids[clave], entrada, archivo, ANA, AHORA)
    return ids


def _armar(db, settings, simulado=None, impresora=None, tarifas=None):
    with closing(connect(db)) as conn:
        return propuesta.armar(conn, settings, NRO, ANA, AHORA, cliente=simulado, dormir=lambda s: None,
                               imprimir=impresora or Impresora(), tarifas=tarifas)


def _tarifas(db, precio="25000.00"):
    with closing(connect(db)) as conn:
        producto = propuesta.producto_del_cartel(conn, NRO)
    assert producto                                                    # las reglas reales asignan un producto
    return {producto: {"moneda": "CRC", "precio": precio, "periodo": "mensual", "iva": 13,
                       "desglose": {"mano_de_obra": 30, "insumos": 40, "gastos_administrativos": 15, "utilidad": 15}}}


def _acciones(db, accion):
    with closing(connect(db)) as conn:
        return conn.execute("SELECT count(*) FROM audit_log WHERE accion = ?", (accion,)).fetchone()[0]


# --- El documento -------------------------------------------------------------------------------------------------

def test_oferta_como_navsat_con_pendientes_en_rojo_y_anexos_adjuntos(db, tmp_path):
    settings = _settings(db, tmp_path)
    _pliego(db)
    _requisitos(db, settings)
    simulado, impresora = OpenAISimulado(), Impresora()

    armada = _armar(db, settings, simulado, impresora, _tarifas(db))

    principal = impresora.principal()
    assert principal.count("Respuesta Sección") == 4                    # la sección inventada se descartó
    assert "Reporte de posición cada 60 segundos (SINTÉTICO)." in principal          # el texto se copia tal cual
    assert principal.count("LLAMADO A COTIZAR") == 1                    # el título va una vez, como encabezado
    assert "Respuesta Sección 01 – Llamado a Cotizar <span>Entendemos y aceptamos lo indicado.</span>" in principal
    assert "Respuesta Sección 03 – Requisitos de Admisibilidad <span>Entendemos, aceptamos y cumplimos" in principal
    # La sección 4 tiene un requisito que no cumple: no dice «cumplimos», lo dice en rojo; la portada dice BORRADOR.
    assert 'class="respuesta pendiente">Respuesta Sección 04' in principal and "No cumple: Reporte de posición" in principal
    assert "BORRADOR: hay" in principal and "Ficha técnica del equipo ofertado" in principal
    assert "Anexo 2.1" in principal and "Aportar patente municipal vigente." in principal
    # A la IA solo fue el pliego: ni los documentos ni las respuestas del asistente.
    enviado = simulado.llamadas[0]["input"]
    assert "Patente municipal vigente" in enviado and "patente.pdf" not in enviado and "declaracion" not in enviado
    # Páginas: principal 1 · título 1.1 · económica 1 · título 2.1 + patente (2) · título 2.2 + imagen.
    assert _paginas(armada.contenido) == 1 + 1 + 1 + 1 + 2 + 1 + 1
    assert _acciones(db, "adjuntar_documento_oferta") == 2 and _acciones(db, "generar_oferta") == 1
    assert any("representante legal" in p for p in armada.pendientes)
    assert not any(p.startswith("PRECIO PENDIENTE") for p in armada.pendientes), armada.pendientes   # con tarifa
    economica = next(h for h in impresora.html if "Monto en Letras" in h)
    assert "Doscientos veintiséis mil colones exactos." in economica      # 8 × 25 000 + 13 % de IVA (sin meses)

    _armar(db, settings, simulado, Impresora(), _tarifas(db))               # mismo pliego: no se vuelve a pedir
    assert len(simulado.llamadas) == 1


def test_sin_tarifa_sale_precio_pendiente_y_no_se_calcula_el_total(db, tmp_path):
    settings = _settings(db, tmp_path)
    _pliego(db)
    impresora = Impresora()
    armada = _armar(db, settings, OpenAISimulado(), impresora, tarifas={})
    assert any(p.startswith("PRECIO PENDIENTE") for p in armada.pendientes)
    anexos = next(h for h in impresora.html if 'class="hoja"' in h)
    assert "PRECIO PENDIENTE" in anexos and "oferta_economica" not in "".join(impresora.html)
    # Sin asistente empezado, nada está comprobado: también va en la portada.
    assert any("asistente de elegibilidad" in p for p in armada.pendientes)


def test_con_la_ia_apagada_el_pliego_va_entero_en_una_seccion(db, tmp_path):
    settings = _settings(db, tmp_path, ia=False)
    _pliego(db)
    impresora = Impresora()
    armada = _armar(db, settings, None, impresora, tarifas={})
    principal = impresora.principal()
    assert principal.count("Respuesta Sección") == 1 and "Pliego de condiciones" in principal
    assert "4. ESPECIFICACIONES TÉCNICAS" in principal and "apagada" in armada.motivo_ia


def test_sin_pliego_no_se_arma(db, tmp_path):
    settings = _settings(db, tmp_path)
    with pytest.raises(propuesta.PropuestaError, match="Falta el pliego"):
        _armar(db, settings, OpenAISimulado())


def test_las_secciones_se_comprueban_contra_el_texto():
    paginas = [ia_oferta.Pagina(1, "pliego.pdf", n, t) for n, t in enumerate(PAGINAS, start=1)]
    lista = ia_oferta.comprobar({"secciones": SECCIONES}, paginas)
    assert [s.numero for s in lista] == ["1", "2", "3", "4"]
    bloques = propuesta.cortar(paginas, lista)
    assert [b.titulo for b in bloques] == ["LLAMADO A COTIZAR", "ASPECTOS GENERALES", "REQUISITOS DE ADMISIBILIDAD",
                                           "ESPECIFICACIONES TÉCNICAS"]
    assert bloques[0].texto.endswith("(SINTÉTICO).") and "ASPECTOS" not in bloques[0].texto


def test_el_texto_vertical_no_se_copia_a_la_oferta():
    # Una etiqueta girada del PDF (SINTÉTICA), como salió en el pliego de cámaras corporales: letra por letra.
    vertical = "\n".join("G re r g a is b t a r c o i ó d n".split())
    pagina = f"10. Entrega de la información (SINTÉTICO).\n{vertical}\nAl finalizar el contrato, el proveedor..."
    limpio = propuesta.sin_texto_vertical(pagina)
    assert limpio == "10. Entrega de la información (SINTÉTICO).\nAl finalizar el contrato, el proveedor..."
    # Se quedan: una lista de números, pocas líneas cortas y las líneas normales.
    numeros = "Cantidades:\n1\n2\n3\n4\n5\n6\n7"
    assert propuesta.sin_texto_vertical(numeros) == numeros
    pocas = "Sí\nNo\nN/A\nTexto normal"
    assert propuesta.sin_texto_vertical(pocas) == pocas
    paginas = [ia_oferta.Pagina(1, "pliego.pdf", 1, pagina)]
    assert "\nre\n" not in propuesta.cortar(paginas, [])[0].texto


@pytest.mark.parametrize("texto, meses", [("1 año", 12), ("24 meses", 24), ("un año", 12), ("doce meses", 12),
                                          ("no encontrado", None), ("hasta 4 años", 48), ("", None)])
def test_meses_del_contrato(texto, meses):
    assert propuesta.meses_de(texto) == meses


# --- Panel --------------------------------------------------------------------------------------------------------

@pytest.fixture
def panel_oferta(clientes, db, tmp_path, monkeypatch):  # noqa: F811
    """Panel con la IA apagada y carpetas temporales: nunca toca data/ ni llama a OpenAI."""
    for clave, valor in (("AI_MODE", "none"), ("EXPORTS_DIR", str(tmp_path / "exports")),
                         ("ASSISTANT_DOCS_DIR", str(tmp_path / "asistente")),
                         ("PROFILE_DOCS_DIR", str(tmp_path / "perfil"))):
        monkeypatch.setenv(clave, valor)
    return clientes


def _oferta(cliente, nro=NRO):
    token = token_csrf(cliente.get(f"/oportunidades/{nro}").text)
    return cliente.post(f"/oportunidades/{nro}/oferta", data={"csrf_token": token}, follow_redirects=False)


def test_el_boton_solo_para_quien_entra_al_expediente(panel_oferta, db):
    oscar, ana = panel_oferta["oscar"], panel_oferta["ana"]
    assert _oferta(oscar, OTRO).status_code == 404                                  # sin seguimiento
    _dar_seguimiento(oscar)
    _asignar(oscar, _id(db, "ivania@ejemplo.test"))
    assert 'action="/oportunidades/00000000001/oferta"' in oscar.get(f"/oportunidades/{NRO}").text
    assert 'action="/oportunidades/00000000001/oferta"' not in ana.get(f"/oportunidades/{NRO}").text
    token = token_csrf(ana.get(f"/oportunidades/{NRO}").text)
    assert ana.post(f"/oportunidades/{NRO}/oferta", data={"csrf_token": token}).status_code == 403   # otra encargada
    assert oscar.post(f"/oportunidades/{NRO}/oferta", data={}).status_code in (400, 403)            # sin CSRF


def test_sin_pliego_vuelve_al_cartel_con_el_aviso(panel_oferta):
    oscar = panel_oferta["oscar"]
    _dar_seguimiento(oscar)
    r = _oferta(oscar)
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}"
    assert "Falta el pliego" in oscar.get(f"/oportunidades/{NRO}").text


@navegador
def test_el_boton_entrega_el_pdf_y_guarda_una_copia(panel_oferta, db, tmp_path):
    oscar = panel_oferta["oscar"]
    _dar_seguimiento(oscar)
    _pliego(db)
    r = _oferta(oscar)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and f"oferta_{NRO}_" in r.headers["content-disposition"]
    assert list((tmp_path / "exports" / "ofertas").rglob("oferta_*.pdf"))
    assert _acciones(db, "generar_oferta") == 1
