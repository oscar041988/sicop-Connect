"""Ayuda, lección 2: marcadores de las misiones, base de EJEMPLO y capturas automáticas.

Todo en tmp_path con datos inventados (EJEMPLO); nunca toca data/ ni app/web/static/ayuda/.
La prueba con navegador se salta sola si Chromium de Playwright no está instalado.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.ayuda import capturas, ejemplo, misiones, pantallas
from app.ayuda.misiones import Marcador
from app.cli import main


# --- Marcadores ---------------------------------------------------------------------------------------------------

def test_cada_marcador_de_las_misiones_tiene_pantalla_y_elemento():
    marcadores = misiones.leer()
    assert len(marcadores) >= 100
    for m in marcadores:
        url, objetivo = pantallas.resolver(m)          # lanza SinObjetivo si falta algo
        assert url.startswith("/") and (objetivo.texto or objetivo.selector)
    imagenes = [m.imagen for m in marcadores]
    assert len(imagenes) == len(set(imagenes))           # una imagen por marcador
    assert all(m.alt.startswith("Pantalla «") for m in marcadores)


def test_numera_por_paso_y_cuenta_las_capturas_del_mismo_paso(tmp_path):
    (tmp_path / "05-prueba.md").write_text(
        "# Prueba\n\n1. Haz clic en «Entrar».\n   [captura: Iniciar sesión · resaltar «Entrar»]\n"
        "   [captura: Iniciar sesión · resaltar «Correo»]\n2. Mira.\n"
        "12. Haz clic.\n    [captura: Panel de carteles · resaltar la prioridad]\n", encoding="utf-8")
    a, b, c = misiones.leer(tmp_path)
    assert (a.paso, a.orden, a.imagen) == (1, 1, "05-prueba/01.png")
    assert (b.paso, b.orden, b.imagen, b.objetivo) == (1, 2, "05-prueba/01-2.png", "«Correo»")
    assert (c.paso, c.pantalla, c.objetivo, c.imagen) == (12, "Panel de carteles", "la prioridad", "05-prueba/12.png")


def test_un_marcador_mal_escrito_dice_mision_y_linea(tmp_path):
    (tmp_path / "07-mal.md").write_text("1. Paso.\n   [captura: Cartel resaltar «Ver»]\n", encoding="utf-8")
    with pytest.raises(misiones.MarcadorInvalido, match="07-mal, línea 2"):
        misiones.leer(tmp_path)


def test_un_objetivo_sin_comillas_y_sin_especial_da_un_error_claro():
    m = Marcador("09-x", 3, 1, "Cartel", "el botón azul", 5)
    with pytest.raises(pantallas.SinObjetivo, match="09-x, paso 3: no sé qué resaltar para «el botón azul»"):
        pantallas.resolver(m)
    with pytest.raises(pantallas.SinObjetivo, match="la pantalla «Pantalla inventada»"):
        pantallas.resolver(Marcador("09-x", 3, 1, "Pantalla inventada", "«Entrar»", 5))


def test_la_cli_avisa_si_la_mision_no_existe(capsys):
    assert main(["ayuda", "capturas", "--mision", "99-no-existe"]) == 1
    assert "no hay capturas en la misión «99-no-existe»" in capsys.readouterr().err


# --- Base de ejemplo ----------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def base_ejemplo(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("ayuda") / "ejemplo"
    return carpeta, ejemplo.crear(carpeta)


def test_la_base_de_ejemplo_solo_tiene_datos_inventados_y_marcados(base_ejemplo):
    carpeta, claves = base_ejemplo
    with closing(sqlite3.connect(carpeta / "sicop.db")) as conn:
        titulos = [t for (t,) in conn.execute("SELECT descripcion FROM tenders")]
        origenes = {o for (o,) in conn.execute("SELECT DISTINCT data_origin FROM imports")}
        correos = [e for (e,) in conn.execute("SELECT email FROM users")]
        destinos = [e for (e,) in conn.execute("SELECT email FROM notification_recipients")]
        instituciones = [n for (n,) in conn.execute("SELECT nombre FROM institutions")]
        encajes = {e for (e,) in conn.execute("SELECT DISTINCT encaje FROM opportunity_assessments")}
        resumenes = conn.execute("SELECT estado FROM ia_summaries").fetchall()
    assert len(titulos) > 25 and all(t.startswith("EJEMPLO · ") for t in titulos)
    assert origenes == {"sintetico"}
    assert all(e.endswith("@ejemplo.test") for e in correos + destinos)
    assert all("EJEMPLO" in n for n in instituciones)
    assert {"alta", "media", "baja"} <= encajes
    assert resumenes == [("ok",)]
    assert json.loads((carpeta / "claves.json").read_text(encoding="utf-8"))["principal"] == claves.principal
    golden = (carpeta / "golden" / "golden_set.csv").read_text(encoding="utf-8-sig")
    assert all(linea.split(";")[1].startswith("EJEMPLO") for linea in golden.splitlines()[1:])


def test_se_niega_a_usar_la_base_real(tmp_path, monkeypatch):
    carpeta = tmp_path / "ejemplo"
    monkeypatch.setenv("DATABASE_PATH", str(carpeta / "sicop.db"))   # «la real» apunta adonde iría la de ejemplo
    with pytest.raises(ejemplo.EjemploInseguro, match="no puede ser la base real"):
        ejemplo.crear(carpeta)
    assert not carpeta.exists()


def test_no_borra_una_carpeta_que_no_es_de_ejemplo(tmp_path):
    carpeta = tmp_path / "otra"
    carpeta.mkdir()
    (carpeta / "importante.txt").write_text("no borrar")
    with pytest.raises(ejemplo.EjemploInseguro, match="no es una carpeta de ejemplo"):
        ejemplo.crear(carpeta)
    assert (carpeta / "importante.txt").read_text() == "no borrar"


# --- Capturas con el navegador ------------------------------------------------------------------------------------

def _hay_chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).is_file()
    except Exception:  # noqa: BLE001 — sin Playwright o sin navegador: la prueba se salta
        return False


@pytest.mark.skipif(not _hay_chromium(), reason="Chromium de Playwright no está instalado")
def test_capturas_de_una_mision_y_error_claro_si_falta_un_boton(tmp_path):
    entrar = [m for m in misiones.leer() if m.mision == "01-entrar"]
    falso = Marcador("99-falsa", 4, 1, "Iniciar sesión", "«Botón que no existe»", 9)
    r = capturas.tomar([*entrar, falso], carpeta=tmp_path / "ejemplo", salida=tmp_path / "capturas",
                       avisar=lambda texto: None)

    assert r.hechas == entrar
    assert r.errores == ["99-falsa, paso 4: no encontré «Botón que no existe» en «Iniciar sesión» (/login)."]
    for m in entrar:
        imagen = tmp_path / "capturas" / m.imagen
        assert imagen.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    indice = json.loads((tmp_path / "capturas" / "indice.json").read_text(encoding="utf-8"))
    assert [x["imagen"] for x in indice] == [m.imagen for m in entrar]
    assert indice[0]["alt"] == "Pantalla «Iniciar sesión»: el título «Iniciar sesión» resaltado."
