"""Ayuda, lección 3: página «¿Cómo se usa?», misiones, buscador, glosario y botón «?» en cada pantalla.

Base SINTÉTICA de tests/test_panel.py; las misiones y el glosario son los de docs/ayuda/ (los reales del proyecto).
"""

import re
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import seguimiento, usuarios
from app.ayuda import pagina
from app.database import connect
from app.historial import Quien
from app.main import app
from tests.test_panel import CONTRASENA, db, iniciar_sesion  # noqa: F401 (db es una fixture)

PLANTILLAS = Path(__file__).resolve().parents[1] / "app" / "web" / "templates"
NRO = "00000000001"


@pytest.fixture
def clientes(db, monkeypatch):  # noqa: F811
    """(administradora, encargada) con la sesión iniciada; el cartel NRO en seguimiento."""
    monkeypatch.setenv("DATABASE_PATH", str(db))
    with closing(connect(db)) as conn:
        admin = usuarios.crear_usuario(conn, "admin@ejemplo.test", "Admin Sintética", CONTRASENA, rol=usuarios.ADMIN)
        usuarios.crear_usuario(conn, "encargada@ejemplo.test", "Encargada Sintética", CONTRASENA)
        seguimiento.abrir(conn, NRO, Quien(admin, "Admin Sintética"), datetime.now(timezone.utc))
    resultado = []
    for email in ("admin@ejemplo.test", "encargada@ejemplo.test"):
        cliente = TestClient(app)
        assert iniciar_sesion(cliente, email).status_code == 303
        resultado.append(cliente)
    return resultado


# --- Índice y misiones ------------------------------------------------------------------------------------------

def test_el_indice_tiene_las_23_misiones_en_orden_y_toda_mision_se_abre(clientes):
    admin, _ = clientes
    nombres = [m.nombre for m in pagina.todas()]
    assert len(nombres) == 23 and nombres == sorted(nombres)
    html = admin.get("/ayuda").text
    assert "¿Cómo se usa?" in html and 'id="glosario"' in html
    for nombre in nombres:
        assert f'href="/ayuda/{nombre}"' in html
        r = admin.get(f"/ayuda/{nombre}")
        assert r.status_code == 200, nombre
        assert "← Todas las misiones" in r.text


def test_una_encargada_no_ve_las_misiones_de_administracion(clientes):
    _, encargada = clientes
    html = encargada.get("/ayuda").text
    assert 'href="/ayuda/12-cargar-archivo"' in html             # «Cargar archivo» está en el menú de todos
    for nombre in ("13-usuarios", "16-avisos", "18-bitacora"):
        assert f'href="/ayuda/{nombre}"' not in html
        r = encargada.get(f"/ayuda/{nombre}")
        assert r.status_code == 403 and "solo para administradores" in r.text


def test_la_mision_trae_sus_capturas_y_el_enlace_a_la_siguiente(clientes):
    admin, _ = clientes
    html = admin.get("/ayuda/08-revision").text
    assert "<h1>¿Cómo marco si un cartel interesa o no?</h1>" in html
    assert 'alt="Pantalla «Cartel»: «Guardar revisión» resaltado."' in html
    assert 'href="/ayuda/09-seguimiento"' in html                  # «Sigue con»
    assert "[captura:" not in html and "**" not in html


@pytest.mark.parametrize("nombre", ["99-no-existe", "..%2F..%2Fconfig", "%2E%2E", "08-REVISION", "08-revision.md"])
def test_un_nombre_invalido_da_404(clientes, nombre):
    admin, _ = clientes
    assert admin.get(f"/ayuda/{nombre}").status_code == 404


def test_la_ayuda_pide_sesion(db, monkeypatch):  # noqa: F811
    monkeypatch.setenv("DATABASE_PATH", str(db))
    r = TestClient(app).get("/ayuda/01-entrar", follow_redirects=False)
    assert r.status_code == 303 and "/login" in r.headers["location"]


# --- Convertidor ------------------------------------------------------------------------------------------------

def test_el_convertidor_escapa_todo_y_solo_enlaza_a_otras_misiones(tmp_path):
    texto = ("# Título <b>raro</b>\n\n**Para qué sirve:** <script>alert(1)</script>.\n\n"
             "1. Haz clic en [aquí](https://malo.example) o en [la 2](02-carteles-nuevos.md).\n"
             "   - una <i>sublista</i>\n"
             "   Explicación del paso.\n\n"
             "### Parte dos\n\n4. Otro paso.\n\n**Sigue con:** [Inicio](../MISIONES.md)\n")
    titulo, html = pagina.convertir(texto, {}, tmp_path)
    assert titulo == "Título <b>raro</b>"                     # el título lo escapa la plantilla
    assert "<script>" not in html and "&lt;script&gt;" in html and "&lt;i&gt;sublista" in html
    assert "malo.example" not in html and "aquí" in html
    assert '<a href="/ayuda/02-carteles-nuevos">la 2</a>' in html and '<a href="/ayuda">Inicio</a>' in html
    assert '<ol start="1">' in html and '<ol start="4">' in html and "<h3>Parte dos</h3>" in html
    assert "<strong>Para qué sirve:</strong>" in html


def test_sin_imagen_la_captura_queda_pendiente(tmp_path):
    from app.ayuda.misiones import Marcador
    m = Marcador("01-entrar", 1, 1, "Iniciar sesión", "«Entrar»", 2)
    _, html = pagina.convertir("1. Haz clic en «Entrar».\n   [captura: Iniciar sesión · resaltar «Entrar»]\n",
                               {2: m}, tmp_path)
    assert "Captura pendiente" in html and "<img" not in html
    (tmp_path / "01-entrar").mkdir()
    (tmp_path / "01-entrar" / "01.png").write_bytes(b"\x89PNG")
    _, html = pagina.convertir("1. Haz clic en «Entrar».\n   [captura: Iniciar sesión · resaltar «Entrar»]\n",
                               {2: m}, tmp_path)
    assert '<img src="/static/ayuda/01-entrar/01.png"' in html


# --- Buscador ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("consulta", ["reporte", "REPÓRTE", "  Reporte  "])
def test_el_buscador_encuentra_reporte_sin_importar_tildes_ni_mayusculas(clientes, consulta):
    admin, _ = clientes
    html = admin.get("/ayuda", params={"q": consulta}).text
    resultados = html.split("Resultados para", 1)[1].split("Ver todas las misiones", 1)[0]
    assert 'href="/ayuda/12-cargar-archivo"' in resultados


def test_el_buscador_dice_si_no_encuentra_y_escapa_la_consulta(clientes):
    admin, encargada = clientes
    assert "No encontré ninguna misión con «helicóptero»" in admin.get("/ayuda", params={"q": "helicóptero"}).text
    html = admin.get("/ayuda", params={"q": "<script>alert(1)</script>"}).text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    resultados = encargada.get("/ayuda", params={"q": "destinatarios"}).text.split("Resultados para", 1)[1]
    assert "/ayuda/15-destinatarios" not in resultados.split("Ver todas las misiones", 1)[0]


# --- Botón «?» y glosario ---------------------------------------------------------------------------------------

def test_cada_mision_del_mapa_existe():
    nombres = {m.nombre for m in pagina.todas()}
    for regla in pagina._config()["pantallas"]:
        assert regla["mision"] in nombres, regla
    assert set(pagina._config()["solo_admin"]) <= nombres


@pytest.mark.parametrize("url, mision", [
    ("/oportunidades", "02-carteles-nuevos"), (f"/oportunidades/{NRO}", "04-arriba-del-cartel"),
    ("/seguimiento", "09-seguimiento"), (f"/seguimiento/{NRO}", "10-expediente"),
    ("/competencia", "11-competencia"), ("/cargar", "12-cargar-archivo"), ("/usuarios", "13-usuarios"),
    ("/destinatarios", "15-destinatarios"), ("/avisos", "16-avisos"), ("/calidad", "17-calidad"),
    ("/bitacora", "18-bitacora"), ("/perfil", "21-perfil"),
    (f"/oportunidades/{NRO}/verificacion", "22-lista-verificacion"),
])
def test_cada_pantalla_tiene_su_boton_de_ayuda(clientes, url, mision):
    admin, _ = clientes
    r = admin.get(url)
    assert r.status_code == 200, url
    boton = re.search(r'<a class="boton-ayuda" href="([^"]+)"', r.text)
    assert boton and boton.group(1) == f"/ayuda/{mision}"
    assert admin.get(boton.group(1)).status_code == 200


def test_el_boton_del_resumen_y_una_pantalla_sin_mapa():
    assert pagina.ayuda_para(f"/oportunidades/{NRO}/resumen") == "/ayuda/05-resumen-ia"
    assert pagina.ayuda_para("/pantalla-nueva") == "/ayuda"


def test_la_ayuda_no_lleva_su_propio_boton(clientes):
    admin, _ = clientes
    assert "boton-ayuda" not in admin.get("/ayuda").text


def test_ayuda_no_esta_en_el_menu_sino_en_el_pie(clientes):
    # Quitada del menú (pedido de Ivania, 2026-11-03): ya está el botón «?» y el enlace del pie
    _, encargada = clientes
    pagina = encargada.get("/oportunidades").text
    menu = pagina.split("<nav>", 1)[1].split("</nav>", 1)[0]
    assert 'href="/ayuda"' not in menu
    assert '<a href="/ayuda">¿Cómo se usa? (ayuda)</a>' in pagina
    menu = encargada.get("/ayuda/08-revision").text.split("<nav>", 1)[1].split("</nav>", 1)[0]
    assert '<a href="/oportunidades" aria-current="page">' not in menu


def test_cada_termino_de_las_plantillas_esta_en_el_glosario():
    usados = {m for f in PLANTILLAS.glob("*.html")
              for m in re.findall(r'termino\("([^"]+)"', f.read_text(encoding="utf-8"))}
    assert usados >= {"Prioridad", "Revisión", "Encargado"}
    for palabra in usados:
        pagina.termino(palabra)                                 # KeyError si falta en GLOSARIO.md
    with pytest.raises(KeyError, match="no está en docs/ayuda/GLOSARIO.md"):
        pagina.termino("Palabra inventada")


def test_el_panel_muestra_la_explicacion_del_glosario(clientes):
    admin, _ = clientes
    html = admin.get("/oportunidades").text
    assert 'class="termino" tabindex="0" data-def="Qué tanto se parece el cartel' in html
