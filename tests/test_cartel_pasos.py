"""Detalle del cartel rediseñado (2026-11-06): franja a lo ancho y 4 pestañas con ?paso=.

Base temporal con los carteles SINTÉTICOS de test_panel.py y la ficha y los documentos SIMULADOS de
test_panel_enriquecimiento.py. Nunca toca data/.
"""

import re
import sqlite3
from contextlib import closing

import pytest

from tests.test_panel import cliente, db  # noqa: F401 (fixtures)
from tests.test_panel_enriquecimiento import NRO, _cliente, _documento, _ficha, entorno  # noqa: F401

PASOS = ("entender", "requisitos", "condiciones", "evidencia")


def _encabezado(html):
    return re.search(r"<header>.*?</header>", html, re.S).group(0)


@pytest.mark.parametrize("paso", PASOS + ("", "otro"))
def test_cada_paso_responde_sin_resumen_lista_ni_documentos(cliente, paso):  # noqa: F811
    respuesta = cliente.get(f"/oportunidades/{NRO}?paso={paso}")
    assert respuesta.status_code == 200
    html = respuesta.text
    # Solo el paso elegido se ve (un paso desconocido abre «Entender»); los otros quedan ocultos.
    elegido = paso if paso in PASOS else "entender"
    for p in PASOS:
        oculto = f'data-paso="{p}" hidden' in html
        assert oculto == (p != elegido), p
    assert 'aria-current="step"' in html
    assert "Todavía no se consultó en SICOP" in html and "no encontrado" in html
    assert "Sin documentos de SICOP para este cartel." in html


def test_encabezado_de_la_base_no_cambia(cliente):  # noqa: F811
    detalle = cliente.get(f"/oportunidades/{NRO}?paso=condiciones").text
    panel = cliente.get("/oportunidades").text
    assert _encabezado(detalle) == _encabezado(panel)


def test_titulo_con_script_se_escapa(cliente, db):  # noqa: F811
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE tenders SET descripcion = ? WHERE nro_sicop = ?",
                     ("GPS <script>alert(1)</script>", NRO))
    html = cliente.get(f"/oportunidades/{NRO}").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_condiciones_y_documentos_con_ficha(entorno):  # noqa: F811
    db, tmp = entorno
    detalle = _ficha(db)
    _documento(db, tmp / "documentos", detalle)
    admin = _cliente("admin@ejemplo.test")
    html = admin.get(f"/oportunidades/{NRO}?paso=condiciones").text
    assert "Reajuste de precios" in html and "Leer texto completo del pliego" in html
    assert "<script>alert(1)</script>" not in html          # la multa SIMULADA trae un <script>
    assert "Garantía de cumplimiento" in html and "Cláusula penal" in html
    html = admin.get(f"/oportunidades/{NRO}?paso=evidencia").text
    assert ">Abrir</a>" in html
    assert "Pliego &lt;b&gt;SIMULADO&lt;/b&gt;.pdf" in html
