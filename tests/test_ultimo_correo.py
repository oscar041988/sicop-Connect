"""«Último correo» arriba del panel y el resumen semanal en el panel (Ivania, 2026-11-13).

Base temporal de test_panel.py (carteles SINTÉTICOS); envíos SIMULADOS escritos a mano en la outbox. Nunca toca data/.
"""

import sqlite3
from contextlib import closing

from fastapi.testclient import TestClient

from app import avisos
from app.database import connect
from app.main import app
from tests.test_panel import cliente, db  # noqa: F401 (fixtures)

LUNES = "2026-11-09T08:00:02-06:00"
MARTES = "2026-11-10T08:00:01-06:00"


def _fila(db, para, motivo, status, momento, nro=None, version="1"):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("INSERT INTO notification_outbox (dedup_key, recipient, nro_sicop, version, motivo, rules_version,"
                     " status, detalle, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'r1', ?, 'SIMULADO', ?, ?)",
                     (f"{para}|{nro}|{version}|{motivo}|{momento}", para, nro, version, motivo, status, momento,
                      None if status == "preparado" else momento))


def test_el_ultimo_envio_cuenta_personas_por_estado_y_no_cuenta_la_vista_previa(db):
    with closing(connect(db)) as conn:
        assert avisos.ultimo_envio(conn, ("resumen_semanal",)) is None
    for para in ("a@ejemplo.test", "b@ejemplo.test"):
        _fila(db, para, "nueva", "aceptado", LUNES, nro="00000000001")
    _fila(db, "a@ejemplo.test", "nueva", "aceptado", MARTES, nro="00000000002")
    _fila(db, "a@ejemplo.test", "cambio_plazo", "aceptado", MARTES, nro="00000000001")  # misma persona: cuenta 1
    _fila(db, "c@ejemplo.test", "nueva", "fallido", MARTES, nro="00000000002")
    _fila(db, "d@ejemplo.test", "nueva", "preparado", "2026-11-11T08:00:00-06:00", nro="00000000002")
    with closing(connect(db)) as conn:
        e = avisos.ultimo_envio(conn, tuple(avisos.MOTIVOS))
    assert (e.momento, e.aceptados, e.fallidos, e.inciertos) == (MARTES, 1, 1, 0)


def test_el_panel_dice_cuando_salio_cada_correo_y_lleva_al_resumen(cliente, db):
    html = cliente.get("/oportunidades").text
    assert html.count("todavía no se ha enviado ninguno") == 2
    for para in ("a@ejemplo.test", "b@ejemplo.test", "c@ejemplo.test"):
        _fila(db, para, "resumen_semanal", "aceptado", LUNES, version="2026-W46")
    html = cliente.get("/oportunidades").text
    assert "Último resumen semanal:" in html and "aceptado por Gmail para 3 personas" in html
    assert '<a href="/resumen-semanal">Ver el resumen</a>' in html
    assert html.count("todavía no se ha enviado ninguno") == 1  # el diario sigue sin envíos


def test_la_pagina_del_resumen_semanal_trae_el_cuerpo_del_correo(cliente, db):
    _fila(db, "a@ejemplo.test", "resumen_semanal", "incierto", LUNES, version="2026-W46")
    html = cliente.get("/resumen-semanal").text
    assert "Nuevas oportunidades:" in html and "Próximos cierres (7 días):" in html
    assert "incierto para 1" in html and "armado ahora con los datos de hoy" in html
    assert "Recibes este resumen" not in html  # el pie es solo del correo
    anonimo = TestClient(app)
    assert anonimo.get("/resumen-semanal", follow_redirects=False).status_code == 303
