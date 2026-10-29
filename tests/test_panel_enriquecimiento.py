"""Panel del enriquecimiento (lección 4, entrega 4B): «Información de SICOP», documentos y bitácora con videos.

Base y carpetas en tmp_path: fichas SIMULADAS (formato de tender_details) sobre los carteles SINTÉTICOS de
test_panel.py; documentos y grabaciones SIMULADOS. Nunca toca data/.
"""

import io
import json
import sqlite3
import zipfile
from contextlib import closing
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import usuarios
from app.database import connect
from app.main import app
from app.sources import enriquecimiento as en
from tests.test_panel import CONTRASENA, db, iniciar_sesion, token_csrf  # noqa: F401 (db es una fixture)

NRO = "00000000001"   # Alta, cierra en 3 días (test_panel.CARTELES)
OTRO = "00000000002"
CIERRE_SICOP = "2026-12-01T23:59:00-06:00"
GARANTIAS = {"fulfillmentGuarnRcvYnNm": "Sí", "fulfillmentGuarnAmt": "1000000", "fulfillmentGuarnAmtType": "CRC",
             "fulfillmentGuarnDur": "12", "participationGuarnRcvYnNm": "No", "amtReadjustYnNm": "Sí",
             "contractDur": "1", "contractDurUnitNm": "Años", "fine": "0,50% diario <script>alert(1)</script>",
             # Tipo «RAT» = porcentaje (20261002726: SICOP manda 5 y RAT, la pantalla dice «5 %»).
             "collateralGuarnRcvYnNm": "Sí", "collateralGuarnAmt": 4, "collateralGuarnAmtType": "RAT"}
CRITERIOS = {"criterios": ["Precio 80%", "Experiencia 20%"], "impactos": ["Ambiental SIMULADO"]}


@pytest.fixture
def entorno(db, tmp_path, monkeypatch):  # noqa: F811
    """La base de test_panel con un admin y un encargado; DOCUMENTS_DIR y RECORDINGS_DIR en tmp_path."""
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setenv("DOCUMENTS_DIR", str(tmp_path / "documentos"))
    monkeypatch.setenv("RECORDINGS_DIR", str(tmp_path / "grabaciones"))
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "admin@ejemplo.test", "Admin Sintética", CONTRASENA, rol=usuarios.ADMIN)
        usuarios.crear_usuario(conn, "encargado@ejemplo.test", "Encargado Sintético", CONTRASENA)
    return db, tmp_path


def _cliente(email):
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, email).status_code == 303
    return cliente


def _sql(db, sql, params=()):
    with closing(sqlite3.connect(db)) as conn, conn:
        return conn.execute(sql, params).lastrowid


def _ficha(db, nro=NRO, cierre=CIERRE_SICOP):
    return _sql(db, "INSERT INTO tender_details (nro_sicop, consultado_en, content_hash, copia_fiel, campos_quitados,"
                    " estado_concurso, version_pliego, modificado, cierre_recepcion, apertura, monto_estimado,"
                    " moneda_monto, tipo_procedimiento, lineas_total, garantias, criterios) VALUES (?,"
                    " '2026-10-27T09:38:00-06:00', ?, '{}', '[]', 'En recepción de ofertas', '2610202684644', 'Y', ?,"
                    " '2026-12-02T08:00:00-06:00', '652190', 'CRC', 'LICITACIÓN MENOR', 1, ?, ?)",
                (nro, f"h-{nro}-{cierre}", cierre, json.dumps(GARANTIAS), json.dumps(CRITERIOS)))


def _documento(db, carpeta, detalle, nombre="pliego.pdf", estado="guardado", nro=NRO, contenido=b"%PDF SIMULADO",
               ruta=None, original="Pliego <b>SIMULADO</b>.pdf"):
    if estado == "guardado":
        (carpeta / nro).mkdir(parents=True, exist_ok=True)
        (carpeta / nro / nombre).write_bytes(contenido)
    guardado = estado == "guardado"
    return _sql(db, "INSERT INTO tender_documents (nro_sicop, detalle_id, tipo_documento, nombre_documento,"
                    " nombre_original, server_file, tamano_bytes, sha256, ruta_local, registrado_en, estado, motivo,"
                    " texto_estado, paginas) VALUES (?, ?, 'Pliego', 'PLIEGO', ?, ?, ?, ?, ?,"
                    " '2026-10-27T09:40:00-06:00', ?, ?, ?, ?)",
                (nro, detalle, original, nombre, len(contenido) if guardado else None, "sha" if guardado else None,
                 (ruta or f"{nro}/{nombre}") if guardado else None, estado,
                 None if guardado else "no llegó en 60 s", "extraido" if guardado else None, 3 if guardado else None))


# --- Detalle: Información de SICOP y documentos ------------------------------------------------------------

def test_el_detalle_muestra_la_ficha_de_sicop(entorno):
    db, _ = entorno
    _ficha(db)
    html = _cliente("encargado@ejemplo.test").get(f"/oportunidades/{NRO}").text
    assert "Información de SICOP" in html and "En recepción de ofertas" in html
    assert "01/12/2026 23:59" in html and "Vale la fecha de SICOP" in html  # el cierre de SICOP no es el de los datos
    assert "652 190.00 CRC" in html and "1 000 000.00 CRC" in html and "plazo 12 meses" in html
    assert "Sí · 4 %" in html and "RAT" not in html                         # porcentaje, no una moneda «RAT»
    assert "Garantía de cumplimiento" in html and "Duración del contrato" in html and "1 Años" in html
    assert "Precio 80%" in html and "Ambiental SIMULADO" in html
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html  # textos de SICOP escapados


def test_sin_ficha_y_despues_del_borrado_al_cierre(entorno):
    db, _ = entorno
    cliente = _cliente("encargado@ejemplo.test")
    assert "Todavía no se consultó en SICOP" in cliente.get(f"/oportunidades/{NRO}").text
    _sql(db, "INSERT INTO enrich_retiros (nro_sicop, retirado_en, cierre, hasta_detalle_id, fichas, documentos,"
             " paginas, bytes) VALUES (?, '2026-10-28T10:00:00-06:00', 'x', 1, 1, 1, 1, 1)", (NRO,))
    html = cliente.get(f"/oportunidades/{NRO}").text
    assert "se borraron al cierre" in html and "28/10/2026 10:00" in html


def test_documentos_y_descarga(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    doc = _documento(db, tmp / "documentos", detalle)
    _documento(db, tmp / "documentos", detalle, nombre="anexo.xlsx", estado="fallo")
    cliente = _cliente("encargado@ejemplo.test")

    html = cliente.get(f"/oportunidades/{NRO}").text
    assert "Documentos (1 guardados de 2)" in html and "con texto, 3 páginas" in html
    assert "FALLO</span>: no llegó en 60 s" in html and "Pliego &lt;b&gt;SIMULADO&lt;/b&gt;.pdf" in html

    r = cliente.get(f"/oportunidades/{NRO}/documentos/{doc}")
    assert r.status_code == 200 and r.content == b"%PDF SIMULADO"
    assert r.headers["content-disposition"].startswith("attachment;")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-type"] == "application/octet-stream"


def test_la_descarga_solo_sirve_lo_guardado_de_ese_cartel_dentro_de_su_carpeta(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    doc = _documento(db, tmp / "documentos", detalle)
    fallo = _documento(db, tmp / "documentos", detalle, nombre="anexo.xlsx", estado="fallo")
    (tmp / "secreto.txt").write_text("fuera de DOCUMENTS_DIR")
    afuera = _documento(db, tmp / "documentos", detalle, nombre="otro.pdf", ruta="../secreto.txt")
    cliente = _cliente("encargado@ejemplo.test")

    for url in (f"/oportunidades/{OTRO}/documentos/{doc}", f"/oportunidades/{NRO}/documentos/{fallo}",
                f"/oportunidades/{NRO}/documentos/{afuera}", f"/oportunidades/{NRO}/documentos/9999"):
        r = cliente.get(url)
        assert r.status_code == 404 and "fuera de DOCUMENTS_DIR" not in r.text
    (tmp / "documentos" / NRO / "pliego.pdf").unlink()  # p. ej. borrado al cierre
    assert cliente.get(f"/oportunidades/{NRO}/documentos/{doc}").status_code == 404


# --- «Ver» sin descargar (pedido de Oscar, 2026-10-29) ------------------------------------------------------

def _excel(filas, hoja="Insumos"):
    """Un .xlsx SIMULADO en memoria."""
    from openpyxl import Workbook
    libro = Workbook()
    libro.active.title = hoja
    for fila in filas:
        libro.active.append(fila)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _zip(entradas):
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in entradas:
            zf.writestr(nombre, datos)
    return salida.getvalue()


def test_ver_un_pdf_lo_abre_en_el_navegador_y_descargar_sigue_igual(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    pdf = _documento(db, tmp / "documentos", detalle)
    _documento(db, tmp / "documentos", detalle, nombre="carta.docx", original="Carta.docx", contenido=b"PK SIMULADO")
    cliente = _cliente("encargado@ejemplo.test")

    html = cliente.get(f"/oportunidades/{NRO}").text
    assert html.count('">Ver</a>') == 1   # el PDF sí; el Word solo «Descargar»
    assert f'href="/oportunidades/{NRO}/documentos/{pdf}/ver" target="_blank" rel="noopener">Ver</a>' in html
    assert html.count(">Descargar</a>") == 2

    r = cliente.get(f"/oportunidades/{NRO}/documentos/{pdf}/ver")
    assert r.status_code == 200 and r.content == b"%PDF SIMULADO"
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("inline;")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert cliente.get(f"/oportunidades/{NRO}/documentos/{pdf}").headers["content-disposition"].startswith("attachment;")


def test_ver_una_imagen_y_un_word(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    foto = _documento(db, tmp / "documentos", detalle, nombre="foto.jpg", original="Kiosco.JPG", contenido=b"\xff\xd8JPG")
    word = _documento(db, tmp / "documentos", detalle, nombre="carta.docx", original="Carta.docx", contenido=b"PK")
    cliente = _cliente("encargado@ejemplo.test")

    r = cliente.get(f"/oportunidades/{NRO}/documentos/{foto}/ver")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["content-disposition"].startswith("inline;")
    r = cliente.get(f"/oportunidades/{NRO}/documentos/{word}/ver")
    assert r.status_code == 422 and "solo se puede descargar" in r.text
    assert f'href="/oportunidades/{NRO}/documentos/{word}"' in r.text   # el botón para descargarlo


def test_ver_un_excel_muestra_sus_hojas_como_texto(entorno, monkeypatch):
    db, tmp = entorno
    detalle = _ficha(db)
    datos = _excel([["Código", "Descripción", "Fecha"], ["000123", "Guantes <script>alert(1)</script>", date(2026, 10, 30)],
                    ["000124", "Mascarillas", None], [None, None, None]])
    doc = _documento(db, tmp / "documentos", detalle, nombre="insumos.xlsx", original="Lista de insumos.xlsx",
                     contenido=datos)
    cliente = _cliente("encargado@ejemplo.test")

    html = cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver").text
    assert "Lista de insumos.xlsx" in html and "Hoja «Insumos»" in html
    assert "<td>000123</td>" in html and "<td>30/10/2026</td>" in html   # el código con sus ceros, la fecha legible
    assert "&lt;script&gt;" in html and "<script>alert" not in html
    assert html.count("<tr>") == 3 and "más de" not in html   # sin la fila vacía del final

    monkeypatch.setattr("app.visor.MAX_FILAS", 2)
    assert "La hoja tiene más de 2 filas" in cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver").text


def test_un_excel_danado_no_rompe_la_pagina(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    doc = _documento(db, tmp / "documentos", detalle, nombre="malo.xlsx", original="Malo.xlsx", contenido=b"no es Excel")
    r = _cliente("encargado@ejemplo.test").get(f"/oportunidades/{NRO}/documentos/{doc}/ver")
    assert r.status_code == 422 and "No se puede ver" in r.text and "Descargar el documento" in r.text


def test_ver_un_zip_lista_sus_archivos_y_abre_los_de_adentro(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    datos = _zip([("pliego/condiciones.pdf", b"%PDF INTERNO"), ("carta.docx", b"PK"),
                  ("precios.xlsx", _excel([["Línea", "Precio"], ["1", "1000"]], hoja="Precios")),
                  ("otro.zip", b"PK"), ("<b>raro</b>.pdf", b"%PDF")])
    doc = _documento(db, tmp / "documentos", detalle, nombre="anexos.zip", original="Anexos.zip", contenido=datos)
    cliente = _cliente("encargado@ejemplo.test")

    html = cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver").text
    assert "ZIP con 5 archivos" in html and "pliego/condiciones.pdf" in html and "&lt;b&gt;raro&lt;/b&gt;.pdf" in html
    for i in (0, 2, 4):
        assert f'/documentos/{doc}/ver/{i}"' in html
    assert f'/documentos/{doc}/ver/1"' not in html and f'/documentos/{doc}/ver/3"' not in html   # Word y ZIP: no

    r = cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver/0")
    assert r.status_code == 200 and r.content == b"%PDF INTERNO" and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == "inline; filename*=utf-8''condiciones.pdf"
    html = cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver/2").text
    assert "Anexos.zip › precios.xlsx" in html and "Hoja «Precios»" in html and "<td>1000</td>" in html
    assert cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver/1").status_code == 422
    assert cliente.get(f"/oportunidades/{NRO}/documentos/{doc}/ver/99").status_code == 404
    assert not any(p.name == "condiciones.pdf" for p in tmp.rglob("*"))   # nada se descomprime a disco


def test_un_archivo_del_zip_mas_grande_que_el_maximo_no_se_lee(entorno, monkeypatch):
    db, tmp = entorno
    monkeypatch.setenv("DOCUMENT_MAX_MB", "1")
    detalle = _ficha(db)
    datos = _zip([("enorme.pdf", b"0" * (2 * 1024 * 1024))])   # 2 MB descomprimido, pocos KB comprimido
    doc = _documento(db, tmp / "documentos", detalle, nombre="bomba.zip", original="Bomba.zip", contenido=datos)
    r = _cliente("encargado@ejemplo.test").get(f"/oportunidades/{NRO}/documentos/{doc}/ver/0")
    assert r.status_code == 422 and "descargue el ZIP" in r.text


def test_ver_solo_sirve_lo_guardado_de_ese_cartel_dentro_de_su_carpeta(entorno):
    db, tmp = entorno
    detalle = _ficha(db)
    pdf = _documento(db, tmp / "documentos", detalle)
    fallo = _documento(db, tmp / "documentos", detalle, nombre="anexo.pdf", estado="fallo")
    (tmp / "secreto.txt").write_text("fuera de DOCUMENTS_DIR")
    afuera = _documento(db, tmp / "documentos", detalle, nombre="otro.pdf", ruta="../secreto.txt")
    cliente = _cliente("encargado@ejemplo.test")

    for url in (f"/oportunidades/{OTRO}/documentos/{pdf}/ver", f"/oportunidades/{NRO}/documentos/{fallo}/ver",
                f"/oportunidades/{NRO}/documentos/{afuera}/ver", f"/oportunidades/{NRO}/documentos/9999/ver",
                f"/oportunidades/{NRO}/documentos/{pdf}/ver/0"):   # un PDF no tiene archivos adentro
        r = cliente.get(url)
        assert r.status_code == 404 and "fuera de DOCUMENTS_DIR" not in r.text


# --- Bitácora de consultas y grabaciones (solo administradores) --------------------------------------------

def _consulta(db, resultado="fallo", grabacion="2026-10-27/00000000001/132428", motivo="no encontró <i>el</i> cartel"):
    run = _sql(db, "INSERT INTO enrich_runs (iniciada_en, terminada_en, estado, maximo, en_cola, consultados, fallos)"
                   " VALUES ('2026-10-27T13:24:00-06:00', '2026-10-27T13:26:00-06:00', 'con_fallos', 20, 2, 2, 1)")
    return _sql(db, "INSERT INTO enrich_consultas (run_id, nro_sicop, iniciada_en, duracion_s, resultado, motivo,"
                    " grabacion) VALUES (?, ?, '2026-10-27T13:24:28-06:00', 33.8, ?, ?, ?)",
                (run, NRO, resultado, motivo, grabacion))


def _grabacion(tmp, nombres=("132428-video.webm", "132428-1-inicio.png", "132428-4-ficha.png")):
    carpeta = tmp / "grabaciones" / "2026-10-27" / NRO
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in nombres:
        (carpeta / nombre).write_bytes(b"SIMULADO " + nombre.encode())
    return carpeta


def test_la_bitacora_es_solo_para_administradores(entorno):
    db, tmp = entorno
    consulta = _consulta(db)
    _grabacion(tmp)
    encargado = _cliente("encargado@ejemplo.test")
    for url in ("/bitacora", f"/bitacora/consultas/{consulta}",
                f"/bitacora/consultas/{consulta}/archivos/132428-video.webm"):
        assert encargado.get(url).status_code == 403
    assert "Bitácora de consultas" not in encargado.get("/oportunidades").text


def test_la_bitacora_muestra_corridas_consultas_y_lo_que_falta_revisar(entorno):
    db, _ = entorno
    _consulta(db)
    _consulta(db, resultado="nueva", motivo=None)
    _sql(db, "INSERT INTO enrich_retiros (nro_sicop, retirado_en, cierre, hasta_detalle_id, fichas, documentos,"
             " paginas, bytes) VALUES (?, '2026-10-28T10:00:00-06:00', '2026-10-27T23:59:00-06:00', 1, 1, 2, 1, 2500000)",
         (OTRO,))
    admin = _cliente("admin@ejemplo.test")
    html = admin.get("/bitacora").text
    assert "1 grabación de un FALLO o CAPTCHA\n    espera revisión" in html
    assert "Con FALLO" in html and "Ficha nueva" in html and "corrida #1" in html
    assert "no encontró &lt;i&gt;el&lt;/i&gt; cartel" in html  # el motivo se escapa
    assert f'<a href="/oportunidades/{OTRO}">{OTRO}</a>' in html and "2 · 2.5 MB" in html
    solo = admin.get("/bitacora?por_revisar=1").text
    assert solo.count("Ver grabación") == 1 and "Bitácora de consultas" in admin.get("/oportunidades").text


def test_la_grabacion_muestra_video_y_capturas(entorno):
    db, tmp = entorno
    consulta = _consulta(db)
    _grabacion(tmp, nombres=("132428-video.webm", "132428-1-inicio.png", "132428-4-ficha.png", "999999-video.webm"))
    admin = _cliente("admin@ejemplo.test")
    html = admin.get(f"/bitacora/consultas/{consulta}").text
    assert f'src="/bitacora/consultas/{consulta}/archivos/132428-video.webm"' in html
    assert "Capturas (2)" in html and "999999" not in html  # solo los archivos de ESTA consulta
    r = admin.get(f"/bitacora/consultas/{consulta}/archivos/132428-video.webm")
    assert r.status_code == 200 and r.content == b"SIMULADO 132428-video.webm"
    assert r.headers["content-type"] == "video/webm" and r.headers["x-content-type-options"] == "nosniff"
    assert admin.get(f"/bitacora/consultas/{consulta}/archivos/132428-1-inicio.png").headers["content-type"] == \
        "image/png"


def test_la_grabacion_no_sirve_archivos_ajenos(entorno):
    db, tmp = entorno
    consulta = _consulta(db)
    carpeta = _grabacion(tmp, nombres=("132428-video.webm", "999999-video.webm", "132428-notas.txt"))
    (tmp / "grabaciones" / "132428-video.webm").write_bytes(b"fuera")
    admin = _cliente("admin@ejemplo.test")
    for nombre in ("999999-video.webm", "132428-notas.txt", "..%2F132428-video.webm", "132428-falta.png"):
        assert admin.get(f"/bitacora/consultas/{consulta}/archivos/{nombre}").status_code == 404
    assert admin.get("/bitacora/consultas/9999/archivos/132428-video.webm").status_code == 404
    for archivo in carpeta.iterdir():
        archivo.unlink()
    assert "La grabación ya no está en este equipo" in admin.get(f"/bitacora/consultas/{consulta}").text


def test_marcar_revisada_y_despues_sigue_la_retencion(entorno):
    db, tmp = entorno
    consulta = _consulta(db)
    _grabacion(tmp)
    exitosa = _consulta(db, resultado="nueva", motivo=None)
    admin = _cliente("admin@ejemplo.test")
    pagina = admin.get(f"/bitacora/consultas/{consulta}").text
    assert "Marcar revisada" in pagina

    assert admin.post(f"/bitacora/consultas/{consulta}/revisada", data={}).status_code == 403  # sin CSRF
    r = admin.post(f"/bitacora/consultas/{consulta}/revisada", data={"csrf_token": token_csrf(pagina)},
                   follow_redirects=True)
    assert "Grabación marcada como revisada" in r.text and "Revisada por Admin Sintética" in r.text
    otra = admin.post(f"/bitacora/consultas/{consulta}/revisada", data={"csrf_token": token_csrf(pagina)})
    assert otra.status_code == 400 and "Ya la revisó Admin Sintética" in otra.text
    assert admin.post(f"/bitacora/consultas/{exitosa}/revisada",
                      data={"csrf_token": token_csrf(pagina)}).status_code == 400  # solo FALLO o CAPTCHA
    with pytest.raises(sqlite3.IntegrityError):
        _sql(db, "DELETE FROM enrich_revisiones")

    # Revisada: a los 30 días se borra como las demás.
    from app.config import load_settings
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "RECORDINGS_DIR": str(tmp / "grabaciones")})
    with closing(connect(db)) as conn:
        assert en.limpiar_grabaciones(conn, settings, date(2026, 12, 1)) == 1
    assert not (tmp / "grabaciones" / "2026-10-27").exists()


def test_sin_revisar_la_grabacion_de_un_fallo_se_conserva(entorno):
    db, tmp = entorno
    _consulta(db)
    _grabacion(tmp)
    from app.config import load_settings
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "RECORDINGS_DIR": str(tmp / "grabaciones")})
    with closing(connect(db)) as conn:
        assert en.limpiar_grabaciones(conn, settings, date(2026, 12, 1)) == 0
    assert (tmp / "grabaciones" / "2026-10-27" / NRO).exists()
