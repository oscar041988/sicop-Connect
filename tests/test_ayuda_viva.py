"""Ayuda viva (Página de ayuda, lección 4): «¿Te sirvió esta ayuda?» y la prueba de botones que ya no existen.

Base SINTÉTICA de tests/test_panel.py; las misiones son las reales de docs/ayuda/misiones/.
"""

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.ayuda import votos
from app.database import apply_migrations, connect
from app.historial import Quien
from tests.test_ayuda_pagina import clientes  # noqa: F401 (fixture: administradora y encargada)
from tests.test_panel import db, token_csrf  # noqa: F401 (db es una fixture)

RAIZ = Path(__file__).resolve().parents[1]
MISIONES = RAIZ / "docs" / "ayuda" / "misiones"
MISION = "08-revision"
ADMIN = "13-usuarios"


def _votar(cliente, mision, util, comentario=""):
    token = token_csrf(cliente.get(f"/ayuda/{mision}").text)
    return cliente.post(f"/ayuda/{mision}/voto", data={"csrf_token": token, "util": util, "comentario": comentario},
                        follow_redirects=False)


# --- «¿Te sirvió esta ayuda?» ------------------------------------------------------------------------------------

def test_el_voto_se_guarda_y_da_las_gracias(clientes, db):  # noqa: F811
    _, encargada = clientes
    assert "¿Te sirvió esta ayuda?" in encargada.get(f"/ayuda/{MISION}").text
    r = _votar(encargada, MISION, "no", "  No encontré el botón «Guardar».  ")
    assert r.status_code == 303 and r.headers["location"] == f"/ayuda/{MISION}#te-sirvio"
    assert "Gracias: tu respuesta ayuda a mejorar la ayuda." in encargada.get(f"/ayuda/{MISION}").text
    assert _votar(encargada, MISION, "si").status_code == 303
    with closing(sqlite3.connect(db)) as conn:
        filas = conn.execute("SELECT mision, util, comentario, usuario_nombre FROM ayuda_votos ORDER BY id").fetchall()
    assert filas == [(MISION, 0, "No encontré el botón «Guardar».", "Encargada Sintética"),
                     (MISION, 1, "", "Encargada Sintética")]


def test_un_voto_sin_si_ni_no_o_muy_largo_no_se_guarda(clientes, db):  # noqa: F811
    _, encargada = clientes
    _votar(encargada, MISION, "tal vez")
    assert "Elige «Sí» o «No»." in encargada.get(f"/ayuda/{MISION}").text
    _votar(encargada, MISION, "no", "x" * 501)
    assert "hasta 500 caracteres" in encargada.get(f"/ayuda/{MISION}").text
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ayuda_votos").fetchone() == (0,)


def test_mision_inexistente_da_404_y_la_de_administracion_no_la_vota_una_encargada(clientes, db):  # noqa: F811
    admin, encargada = clientes
    token = token_csrf(encargada.get(f"/ayuda/{MISION}").text)
    assert encargada.post("/ayuda/99-no-existe/voto", data={"csrf_token": token, "util": "si"}).status_code == 404
    assert encargada.post(f"/ayuda/{ADMIN}/voto", data={"csrf_token": token, "util": "si"}).status_code == 403
    assert encargada.post(f"/ayuda/{MISION}/voto", data={"util": "si"}).status_code == 403          # sin token
    assert _votar(admin, ADMIN, "si").status_code == 303
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT mision FROM ayuda_votos").fetchall() == [(ADMIN,)]


def test_solo_los_administradores_ven_la_tabla_ordenada_por_mas_no(clientes):
    admin, encargada = clientes
    assert "Todavía nadie respondió" in admin.get("/ayuda").text
    _votar(encargada, "03-buscar-y-filtrar", "si")
    _votar(encargada, MISION, "no", "<script>alert(1)</script>")
    _votar(admin, MISION, "no")
    html = admin.get("/ayuda").text
    assert "Cómo les fue con la ayuda" in html
    tabla = html[html.index('id="votos"'):html.index('id="glosario"')]
    assert tabla.index(MISION) < tabla.index("03-buscar-y-filtrar")                             # primero la de más «no»
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in tabla and "<script>alert(1)" not in tabla
    assert "Cómo les fue con la ayuda" not in encargada.get("/ayuda").text


def test_resumen_cuenta_y_los_votos_no_se_borran_ni_se_modifican(db):  # noqa: F811
    ana = Quien(None, "Ana Sintética")
    ahora = datetime(2026, 11, 4, 15, 0, tzinfo=timezone.utc)
    assert apply_migrations(db) == []                                                 # la 0037 dos veces: nada
    with closing(connect(db)) as conn:
        for util, comentario in (("si", ""), ("no", "Confuso"), ("no", ""), ("si", "Bien")):
            votos.votar(conn, MISION, util, comentario, ana, ahora)
        votos.votar(conn, "03-buscar-y-filtrar", "no", "", ana, ahora)
        assert votos.resumen(conn) == [votos.Resumen(MISION, 2, 2, "Bien"), votos.Resumen("03-buscar-y-filtrar", 0, 1, "")]
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM ayuda_votos")
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE ayuda_votos SET util = 1")


# --- Botones que ya no existen ----------------------------------------------------------------------------------

_BOTON = re.compile(r"(?:clic en|[Pp]ulsa) «([^»]+)»")


def _texto_de_la_app() -> str:
    """Todo lo que la app puede mostrar: plantillas (con su Jinja), código y el mapa de la ayuda, en minúsculas."""
    archivos = [*(RAIZ / "app" / "web" / "templates").rglob("*.html"), *(RAIZ / "app").rglob("*.py"),
                RAIZ / "config" / "ayuda.yaml"]
    return "\n".join(a.read_text(encoding="utf-8") for a in archivos).lower()


def botones_que_faltan(texto_mision: str, texto_app: str) -> list[str]:
    """Los botones que la misión manda pulsar y la app ya no tiene. «…» vale por cualquier texto."""
    faltan = []
    for boton in _BOTON.findall(texto_mision):
        partes = [p.strip().lower() for p in boton.split("…") if p.strip()]
        if not all(p in texto_app for p in partes):
            faltan.append(boton)
    return faltan


def test_cada_boton_que_nombra_una_mision_existe_en_la_app():
    texto_app = _texto_de_la_app()
    faltan = {m.name: f for m in sorted(MISIONES.glob("*.md"))
              if (f := botones_que_faltan(m.read_text(encoding="utf-8"), texto_app))}
    assert faltan == {}, ("Estas misiones nombran botones que ya no están en la app; corrige la misión "
                          "(docs/OPERACION.md, «Mantener la ayuda al día»): " + repr(faltan))
    assert len(_BOTON.findall("".join(m.read_text(encoding="utf-8") for m in MISIONES.glob("*.md")))) > 20


def test_la_prueba_de_botones_detecta_un_boton_borrado():
    app_inventada = "<button>Guardar revisión</button> <a>Ver los 3 ganadores</a>"
    mision = "1. Haz clic en «Guardar revisión».\n2. Pulsa «Ver los … ganadores».\n3. Haz clic en «Botón borrado»."
    assert botones_que_faltan(mision, app_inventada.lower()) == ["Botón borrado"]
