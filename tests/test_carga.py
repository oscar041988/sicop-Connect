"""Carga de archivos desde el panel (lección 6, encargo B).

Datos SINTÉTICOS (tests/fixtures/) en una base y carpetas temporales; nunca toca data/.
"""

import io
import re
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import pytest

from app.web import carga
from tests.test_panel import cliente, db, token_csrf  # noqa: F401  (fixtures)

FIXTURES = Path(__file__).parent / "fixtures"
CARTELES = (FIXTURES / "carteles_sintetico.csv").read_bytes()
INSTITUCIONES = (FIXTURES / "instituciones_sintetico.csv").read_bytes()


@pytest.fixture
def carpetas(cliente, tmp_path, monkeypatch):
    """Carpeta de entrada y de originales temporales para el cliente con sesión."""
    entrada, originales = tmp_path / "incoming", tmp_path / "raw"
    monkeypatch.setenv("INCOMING_DIR", str(entrada))
    monkeypatch.setenv("RAW_DATA_DIR", str(originales))
    return entrada, originales


def _subir(cliente, contenido, nombre, reporte="carteles", origen="sintetico", token=None):
    token = token if token is not None else token_csrf(cliente.get("/cargar").text)
    return cliente.post("/cargar", data={"csrf_token": token, "reporte": reporte, "origen": origen},
                        files={"archivo": (nombre, contenido, "text/csv")})


def _importaciones(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT report, file_name, data_origin, rows_accepted, rows_rejected FROM imports").fetchall()


# --- Página y resumen -----------------------------------------------------------------------------

def test_la_pagina_muestra_el_formulario_protegido(cliente):
    pagina = cliente.get("/cargar")

    assert pagina.status_code == 200 and 'enctype="multipart/form-data"' in pagina.text
    assert 'name="csrf_token"' in pagina.text and "máximo 25 MB" in pagina.text
    for reporte in ("carteles", "lineas", "catalogo", "instituciones"):
        assert f'value="{reporte}"' in pagina.text


def test_subir_carteles_sinteticos_importa_y_muestra_el_resumen(cliente, carpetas, db):
    entrada, originales = carpetas

    respuesta = _subir(cliente, CARTELES, "carteles_sintetico.csv")

    assert respuesta.status_code == 200
    texto = respuesta.text
    assert "Resumen de la importación" in texto and "carteles_sintetico.csv" in texto
    assert "<dt>Filas leídas</dt><dd>8</dd>" in texto
    assert "<dt>Aceptadas</dt><dd>3</dd>" in texto and "<dt>Rechazadas</dt><dd>5</dd>" in texto
    assert "Línea 4: «Cédula» en notación científica" in texto  # el motivo, igual que en la CLI
    assert "Advertencias (las filas se aceptaron)" in texto
    guardados = list(entrada.iterdir())
    assert len(guardados) == 1 and guardados[0].name.endswith("_carteles_sintetico.csv")
    assert guardados[0].read_bytes() == CARTELES  # se guarda byte a byte
    assert len(list((originales / "importados").iterdir())) == 1  # la copia fiel del importador
    assert _importaciones(db) == [("carteles", guardados[0].name, "sintetico", 3, 5)]


def test_al_subir_se_evalua_enseguida_y_repetido_no(cliente, carpetas, db):
    respuesta = _subir(cliente, CARTELES, "carteles_sintetico.csv")

    with closing(sqlite3.connect(db)) as conn:
        carteles = conn.execute("SELECT count(*) FROM tenders").fetchone()[0]
    assert f"se evaluaron {carteles} carteles con las reglas de Hermatix" in respuesta.text
    assert "Ya se ven en el" in respuesta.text
    otra_vez = _subir(cliente, CARTELES, "copia.csv")  # nada nuevo: no se evalúa otra vez
    assert "Este archivo ya se import" in otra_vez.text and "se evaluaron" not in otra_vez.text


def test_el_aviso_del_correo_de_las_8_solo_con_el_horario_activo(cliente, carpetas, monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    assert "El correo de avisos sale a las 8:00" in _subir(cliente, CARTELES, "carteles_sintetico.csv").text


def test_subir_el_mismo_archivo_otra_vez_no_duplica(cliente, carpetas, db):
    entrada, _ = carpetas
    _subir(cliente, CARTELES, "carteles_sintetico.csv")

    otra_vez = _subir(cliente, CARTELES, "copia con otro nombre.csv")

    assert otra_vez.status_code == 200
    # Dice qué fue la importación anterior y con qué nombre, aunque ahora se suba con otro.
    nombre_guardado = next(entrada.iterdir()).name
    assert re.search(r"Este archivo ya se importó \(importación #\d+: carteles,\s+\d\d/\d\d/\d{4} \d\d:\d\d\)",
                     otra_vez.text)
    assert f"Se importó con el nombre «{nombre_guardado}»" in otra_vez.text
    assert len(_importaciones(db)) == 1
    assert len(list(entrada.iterdir())) == 1  # la copia repetida no queda en la carpeta de entrada


def test_catalogo_acepta_el_zip_del_portal(cliente, carpetas, db):
    contenido = io.BytesIO()
    with zipfile.ZipFile(contenido, "w") as zf:
        zf.writestr("Codigos Identificacion.csv", (FIXTURES / "catalogo_identificacion_sintetico.csv").read_bytes())

    respuesta = _subir(cliente, contenido.getvalue(), "Reporte de catálogo de bienes y servicios.zip", "catalogo")

    assert respuesta.status_code == 200 and "Resumen de la importación" in respuesta.text
    assert [fila[0] for fila in _importaciones(db)] == ["catalogo"]


def _zip_pliegos(lineas=True):
    contenido = io.BytesIO()
    with zipfile.ZipFile(contenido, "w") as zf:
        zf.writestr("Detalle de pliegos de condiciones.csv", CARTELES)
        if lineas:
            zf.writestr("Detalles lineas.csv", (FIXTURES / "lineas_sintetico.csv").read_bytes())
    return contenido.getvalue()


def test_pliegos_acepta_el_zip_del_portal_e_importa_carteles_y_lineas(cliente, carpetas, db):
    entrada, _ = carpetas

    respuesta = _subir(cliente, _zip_pliegos(), "Reporte de detalle pliego de condiciones.zip", "pliegos")

    assert respuesta.status_code == 200
    assert respuesta.text.count("Resumen de la importación") == 2
    assert "Reporte de detalle pliego de condiciones.zip › Detalle de pliegos de condiciones.csv" in respuesta.text
    assert "reporte carteles" in respuesta.text and "reporte lineas" in respuesta.text
    assert [(f[0], f[1]) for f in _importaciones(db)] == [("carteles", "Detalle de pliegos de condiciones.csv"),
                                                          ("lineas", "Detalles lineas.csv")]
    assert len(list(entrada.iterdir())) == 1  # el ZIP queda en la carpeta de entrada, como un CSV subido

    otra_vez = _subir(cliente, _zip_pliegos(), "copia.zip", "pliegos")
    assert otra_vez.text.count("Este archivo ya se importó") == 2 and len(_importaciones(db)) == 2
    assert len(list(entrada.iterdir())) == 1  # la copia repetida no queda


def test_pliegos_rechaza_un_zip_incompleto(cliente, carpetas, db):
    entrada, _ = carpetas

    respuesta = _subir(cliente, _zip_pliegos(lineas=False), "pliegos.zip", "pliegos")

    assert respuesta.status_code == 400 and "faltan Detalles lineas.csv" in respuesta.text
    assert _importaciones(db) == [] and not any(entrada.iterdir())


# --- Validaciones -----------------------------------------------------------------------------------

@pytest.mark.parametrize("nombre, reporte", [
    ("carteles.xlsx", "carteles"),
    ("carteles.zip", "carteles"),     # el ZIP solo se acepta para el catálogo y para «pliegos»
    ("pliegos.csv", "pliegos"),       # «pliegos» es solo el ZIP
    ("programa.exe", "instituciones"),
    ("sin_extension", "lineas"),
    ("carteles.csv.exe", "carteles"),
])
def test_extension_no_permitida(cliente, carpetas, db, nombre, reporte):
    entrada, _ = carpetas

    respuesta = _subir(cliente, CARTELES, nombre, reporte)

    assert respuesta.status_code == 400 and "acepta archivos" in respuesta.text
    assert not entrada.exists() or not any(entrada.iterdir())
    assert _importaciones(db) == []


@pytest.mark.parametrize("datos, mensaje", [
    ({"reporte": "inventado", "origen": "sintetico"}, "Elige el tipo de reporte"),
    ({"reporte": "carteles", "origen": "inventado"}, "Elige el tipo de reporte"),
])
def test_reporte_u_origen_no_validos(cliente, carpetas, datos, mensaje):
    token = token_csrf(cliente.get("/cargar").text)

    respuesta = cliente.post("/cargar", data={"csrf_token": token, **datos},
                             files={"archivo": ("carteles.csv", CARTELES, "text/csv")})

    assert respuesta.status_code == 400 and mensaje in respuesta.text


def test_sin_archivo(cliente, carpetas):
    token = token_csrf(cliente.get("/cargar").text)

    respuesta = cliente.post("/cargar", data={"csrf_token": token, "reporte": "carteles", "origen": "sintetico"})

    assert respuesta.status_code == 400 and "Elige un archivo" in respuesta.text


def test_archivo_vacio(cliente, carpetas):
    entrada, _ = carpetas

    respuesta = _subir(cliente, b"", "vacio.csv")

    assert respuesta.status_code == 400 and "vacío" in respuesta.text
    assert not any(entrada.iterdir())


def test_reporte_equivocado_no_importa_y_no_deja_el_archivo(cliente, carpetas, db):
    entrada, _ = carpetas

    respuesta = _subir(cliente, INSTITUCIONES, "instituciones.csv", "carteles")  # no es un archivo de carteles

    assert respuesta.status_code == 400 and "No se importó: Faltan encabezados" in respuesta.text
    assert not any(entrada.iterdir()) and _importaciones(db) == []


def test_archivo_ilegible_no_da_error_500_ni_deja_el_archivo(cliente, carpetas, db):
    """Revisión del 2026-10-23: un byte que no existe en cp1252 (0x81) hacía caer la carga con un error 500."""
    entrada, _ = carpetas
    danado = CARTELES.replace(b"\n", b"\x81\xff\n", 2)  # ni UTF-8 ni cp1252

    respuesta = _subir(cliente, danado, "carteles.csv")

    assert respuesta.status_code == 400 and "no es UTF-8 ni cp1252 (byte 0x81" in respuesta.text
    assert not any(entrada.iterdir()) and _importaciones(db) == []


def test_archivo_mas_grande_que_el_limite(cliente, carpetas, db, monkeypatch):
    entrada, _ = carpetas
    monkeypatch.setenv("UPLOAD_MAX_MB", "0.001")  # ~1 KB; el CSV sintético pesa más

    respuesta = _subir(cliente, CARTELES, "carteles.csv")

    assert respuesta.status_code == 413 and "supera el límite de 0.001 MB" in respuesta.text
    assert not any(entrada.iterdir()) and _importaciones(db) == []


def test_una_peticion_que_declara_demasiados_bytes_se_rechaza_antes_de_recibirla(cliente, carpetas, monkeypatch):
    monkeypatch.setenv("UPLOAD_MAX_MB", "0.001")

    respuesta = _subir(cliente, b"x" * 200_000, "grande.csv")  # más que el límite + el margen del formulario

    assert respuesta.status_code == 413 and respuesta.headers["content-type"].startswith("text/plain")


def test_el_limite_se_cumple_aunque_la_peticion_no_declare_su_tamano(tmp_path):
    with pytest.raises(carga.ArchivoMuyGrande):
        carga.guardar_subida(io.BytesIO(b"x" * 5000), "grande.csv", "carteles", tmp_path, limite=4096)

    assert list(tmp_path.iterdir()) == []  # el pedazo copiado se borra


# --- Nombre de archivo seguro --------------------------------------------------------------------

@pytest.mark.parametrize("original, esperado", [
    ("Detalles lineas.csv", "Detalles_lineas.csv"),
    ("Reporte de catálogo de bienes y servicios (1).zip", "Reporte_de_catalogo_de_bienes_y_servicios_1.zip"),
    ("../../app/main.csv", "main.csv"),
    ("..\\..\\Windows\\system32\\x.csv", "x.csv"),
    ("C:\\Users\\Ivania\\Descargas\\Carteles.CSV", "Carteles.csv"),
    ("<script>alert(1)</script>.csv", "script.csv"),  # la «/» de </script> también separa carpetas
    ("..csv", "archivo.csv"),
    ("....", "archivo.csv"),
    ("a" * 300 + ".csv", "a" * 100 + ".csv"),
])
def test_nombre_seguro(original, esperado):
    assert carga.nombre_seguro(original, ".csv" if not esperado.endswith(".zip") else ".zip") == esperado


def test_un_nombre_con_carpetas_se_guarda_dentro_de_la_carpeta_de_entrada(cliente, carpetas, db):
    entrada, _ = carpetas

    respuesta = _subir(cliente, CARTELES, "../../../afuera.csv")

    assert respuesta.status_code == 200
    guardados = list(entrada.iterdir())
    assert len(guardados) == 1 and guardados[0].name.endswith("_afuera.csv")
    assert not (entrada.parent.parent / "afuera.csv").exists()


def test_el_nombre_original_se_muestra_escapado(cliente, carpetas):
    respuesta = _subir(cliente, CARTELES, "<b>carteles</b>.csv")

    assert "&lt;b&gt;carteles&lt;/b&gt;.csv" in respuesta.text and "<b>carteles</b>" not in respuesta.text


# --- Acceso ---------------------------------------------------------------------------------------

def test_sin_sesion_no_se_puede_subir(db, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setenv("INCOMING_DIR", str(tmp_path / "incoming"))

    respuesta = TestClient(app).post("/cargar", data={"reporte": "carteles", "origen": "sintetico"},
                                     files={"archivo": ("carteles.csv", CARTELES, "text/csv")}, follow_redirects=False)

    assert respuesta.status_code == 303 and respuesta.headers["location"].startswith("/login")
    assert not (tmp_path / "incoming").exists() and _importaciones(db) == []


def test_sin_token_no_se_sube_nada(cliente, carpetas, db):
    entrada, _ = carpetas

    respuesta = _subir(cliente, CARTELES, "carteles.csv", token="token-inventado")

    assert respuesta.status_code == 403
    assert not entrada.exists() and _importaciones(db) == []


# --- Ayuda: dónde está el reporte (pedido de Oscar, 2026-10-26) ------------------------------------

def test_la_ayuda_trae_los_enlaces_a_gmail_y_sicop(cliente, monkeypatch):
    monkeypatch.setenv("SICOP_REQUEST_EMAIL", "buzon-sintetico@example.com")
    monkeypatch.setenv("SOURCE_MODE", "manual")

    texto = cliente.get("/cargar").text

    assert 'href="https://www.sicop.go.cr/app/module/pcont/public/ce-open-data"' in texto
    assert "https://mail.google.com/mail/u/?authuser=buzon-sintetico%40example.com#search/" in texto
    assert "obtención automática está apagada" in texto
    for parte in ("<dt>real</dt>", "<dt>sintetico</dt>", "<dt>simulado</dt>", "No lo abra, no lo descomprima",
                  "Elegir archivo", "Subir e importar", "Leer el resumen", "Evaluación automática",
                  "sale a las 8:00"):
        assert parte in texto


def test_el_css_lleva_su_huella_para_que_el_navegador_no_use_una_copia_vieja(cliente):
    from app.web.rutas import version_estatico

    assert f"estilo.css?v={version_estatico('estilo.css')}" in cliente.get("/cargar").text


def test_formulario_con_los_botones_al_lado_e_instrucciones_al_final(cliente):
    texto = cliente.get("/cargar").text

    columnas = texto.index('class="carga-columnas"')
    formulario, botones = texto.index('action="/cargar"'), texto.index("Abrir el correo de SICOP en Gmail")
    assert columnas < formulario < botones < texto.index("Instrucciones: cómo cargar el reporte")


def test_con_obtencion_automatica_la_ayuda_lo_dice(cliente, monkeypatch):
    monkeypatch.setenv("SOURCE_MODE", "auto")

    assert "obtención automática está encendida" in cliente.get("/cargar").text


def test_el_origen_real_viene_elegido(cliente):
    assert re.search(r'<option value="real"\s+selected>', cliente.get("/cargar").text)


def test_los_enlaces_coinciden_con_la_obtencion_automatica():
    """Si cambia la URL de SICOP o el asunto del correo, la ayuda tiene que cambiar también."""
    from app.sources import gmail_reader, sicop_browser

    assert carga.URL_SICOP == sicop_browser.URL
    assert carga.BUSQUEDA_GMAIL == f'from:{gmail_reader.REMITENTE_SICOP} subject:"{gmail_reader.ASUNTOS["enlace"]}"'
    assert carga.enlace_gmail("").startswith("https://mail.google.com/mail/u/0/#search/from%3Ainfo%40sicop.go.cr")
