"""Revisión a mano de avisos fallidos o inciertos: reintentar o confirmar que sí salió (página /avisos).

Datos SINTÉTICOS (los de tests/test_avisos.py); el envío usa un proveedor SIMULADO: nunca sale un correo.
"""

import sqlite3
from contextlib import closing
from datetime import timedelta

import pytest

from app import destinatarios, reintentos, resumen
from app.database import connect
from app.historial import Quien
from tests.test_avisos import (ProveedorSimulado, _enviar, _hace, _post, _registrar_version, _settings,  # noqa: F401
                               admin_y_encargada, base)
from tests.test_panel import AHORA, CR, db  # noqa: F401

OSCAR = "oscar@ejemplo.test"
IVANIA = Quien(None, "Ivania")


def _ids(db, estado, para=OSCAR):
    with closing(sqlite3.connect(db)) as conn:
        return [i for (i,) in conn.execute("SELECT id FROM notification_outbox WHERE recipient = ? AND status = ?"
                                           " ORDER BY nro_sicop", (para, estado))]


def _estado(db, outbox_id):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT status, detalle FROM notification_outbox WHERE id = ?", (outbox_id,)).fetchone()


def _historial(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT actor, accion, detalle FROM audit_log WHERE accion LIKE '%aviso'"
                            " ORDER BY id").fetchall()


def _reintentar(db, outbox_id, ahora=AHORA, revise_enviados=False):
    with closing(connect(db)) as conn:
        return reintentos.reintentar(conn, outbox_id, ahora.astimezone(CR), IVANIA, revise_enviados)


def _confirmar(db, outbox_id):
    with closing(connect(db)) as conn:
        return reintentos.confirmar_salida(conn, outbox_id, AHORA.astimezone(CR), IVANIA)


@pytest.fixture
def fallido(base, tmp_path):
    """Gmail rechazó el correo de Oscar (3 avisos «fallido»); el de Anabelle salió."""
    _enviar(base, tmp_path, ProveedorSimulado(oscar="rechazar"))
    return base


@pytest.fixture
def incierto(base, tmp_path):
    _enviar(base, tmp_path, ProveedorSimulado(oscar="incierto"))
    return base


def test_lista_solo_fallidos_e_inciertos(fallido):
    with closing(connect(fallido)) as conn:
        lista = reintentos.por_revisar(conn, AHORA)

    assert {(a.para, a.estado) for a in lista} == {(OSCAR, "fallido")} and len(lista) == 3
    assert {a.detalle for a in lista} == {"HTTP 400: Invalid To header (SIMULADO)"}


def test_reintentar_un_fallido_lo_envia_en_el_siguiente_envio(fallido, tmp_path):
    primero = _ids(fallido, "fallido")[0]

    _reintentar(fallido, primero)

    assert _estado(fallido, primero) == ("preparado", "reintento pedido por Ivania")
    sim = ProveedorSimulado()
    resultado = _enviar(fallido, tmp_path, sim, ahora=AHORA + timedelta(minutes=5))
    assert [p for p, *_ in sim.llamadas] == [OSCAR] and resultado.envios[OSCAR].avisos == 1  # solo el reintentado
    assert _estado(fallido, primero)[0] == "aceptado"
    assert len(_ids(fallido, "fallido")) == 2  # los otros siguen esperando una decisión
    # El historial guarda lo de antes, porque el envío reemplazó el detalle de la outbox.
    assert _historial(fallido) == [("Ivania", "reintentar_aviso",
                                    f"{OSCAR} · cartel 00000000001 · antes fallido: HTTP 400: Invalid To header"
                                    " (SIMULADO)")]


def test_un_incierto_se_reintenta_solo_si_se_reviso_enviados(incierto):
    primero = _ids(incierto, "incierto")[0]

    with pytest.raises(reintentos.AvisoInvalido, match="Gmail › Enviados"):
        _reintentar(incierto, primero)
    assert _estado(incierto, primero)[0] == "incierto" and _historial(incierto) == []

    _reintentar(incierto, primero, revise_enviados=True)
    assert _estado(incierto, primero)[0] == "preparado"


def test_confirmar_que_si_salio_no_reenvia(incierto, tmp_path):
    primero = _ids(incierto, "incierto")[0]

    _confirmar(incierto, primero)

    assert _estado(incierto, primero) == ("aceptado", "confirmado a mano por Ivania: sí salió (está en Enviados)")
    assert _historial(incierto)[0][1] == "confirmar_aviso"
    sim = ProveedorSimulado()
    _enviar(incierto, tmp_path, sim, ahora=AHORA + timedelta(minutes=5))
    assert sim.llamadas == []


def test_un_fallido_no_se_confirma(fallido):
    with pytest.raises(reintentos.AvisoInvalido, match="Solo un aviso incierto"):
        _confirmar(fallido, _ids(fallido, "fallido")[0])


def test_no_se_toca_un_aviso_aceptado_ni_uno_que_no_existe(fallido):
    with pytest.raises(reintentos.AvisoInvalido, match="ya no está fallido ni incierto"):
        _reintentar(fallido, _ids(fallido, "aceptado", "anabelle@ejemplo.test")[0])
    with pytest.raises(reintentos.AvisoInvalido, match="no existe"):
        _reintentar(fallido, 9999)
    primero = _ids(fallido, "fallido")[0]
    _reintentar(fallido, primero)
    with pytest.raises(reintentos.AvisoInvalido, match="ya no está fallido"):  # doble clic: no se repite
        _reintentar(fallido, primero)
    assert len(_historial(fallido)) == 1


def test_no_se_reintenta_si_ya_llego_una_version_mas_nueva(fallido, tmp_path):
    viejo = _ids(fallido, "fallido")[0]  # 00000000001
    with closing(connect(fallido)) as conn:
        _registrar_version(conn, "00000000001", "h2", _hace(0))
    _enviar(fallido, tmp_path, ProveedorSimulado(), ahora=AHORA + timedelta(minutes=5))  # la nueva sí llega

    with pytest.raises(reintentos.AvisoInvalido, match="versión más nueva"):
        _reintentar(fallido, viejo)


def test_no_se_reintenta_un_cartel_cerrado_ni_a_un_destinatario_quitado(fallido):
    primero = _ids(fallido, "fallido")[0]  # 00000000001 cierra en 3 días
    with pytest.raises(reintentos.AvisoInvalido, match="ya cerró"):
        _reintentar(fallido, primero, ahora=AHORA + timedelta(days=4))

    with closing(connect(fallido)) as conn:
        oscar = next(d.id for d in destinatarios.listar(conn) if d.email.lower() == OSCAR)
        destinatarios.cambiar_estado(conn, oscar, False)
    with pytest.raises(reintentos.AvisoInvalido, match="ya no recibe avisos"):
        _reintentar(fallido, primero)
    assert _estado(fallido, primero)[0] == "fallido"


# --- Página /avisos (solo administradores) ------------------------------------------------------------------

def test_la_administradora_reintenta_desde_el_panel(admin_y_encargada, fallido):
    ivania, _ = admin_y_encargada
    primero = _ids(fallido, "fallido")[0]

    pagina = ivania.get("/avisos").text
    assert 'href="/avisos"' in pagina and "HTTP 400: Invalid To header (SIMULADO)" in pagina

    assert _post(ivania, f"/avisos/{primero}/reintentar").status_code == 303
    pagina = ivania.get("/avisos").text
    assert "preparado otra vez: sale en el siguiente envío" in pagina
    assert f"Volvió a preparar un aviso: {OSCAR} · cartel 00000000001" in pagina
    assert _estado(fallido, primero)[0] == "preparado"


def test_incierto_desde_el_panel(admin_y_encargada, incierto):
    ivania, _ = admin_y_encargada
    primero, segundo, _ = _ids(incierto, "incierto")

    sin_casilla = _post(ivania, f"/avisos/{primero}/reintentar")
    assert sin_casilla.status_code == 400 and "Gmail › Enviados" in sin_casilla.text
    assert _post(ivania, f"/avisos/{primero}/reintentar", revise_enviados="1").status_code == 303
    assert _post(ivania, f"/avisos/{segundo}/confirmar").status_code == 303
    assert (_estado(incierto, primero)[0], _estado(incierto, segundo)[0]) == ("preparado", "aceptado")


def test_la_encargada_no_revisa_avisos(admin_y_encargada, fallido):
    _, encargada = admin_y_encargada
    primero = _ids(fallido, "fallido")[0]

    assert 'href="/avisos"' not in encargada.get("/oportunidades").text
    assert encargada.get("/avisos").status_code == 403
    assert _post(encargada, f"/avisos/{primero}/reintentar").status_code == 403
    assert _post(encargada, f"/avisos/{primero}/confirmar").status_code == 403
    assert _estado(fallido, primero)[0] == "fallido"


# --- Resumen semanal (revisión del 2026-10-23: antes no aparecía en /avisos) --------------------------------

def _resumen(db, tmp_path, proveedor, ahora=AHORA):
    with closing(connect(db)) as conn:
        return resumen.notify(conn, _settings(db, tmp_path), ahora.astimezone(CR), dry_run=False,
                              proveedor=proveedor)


@pytest.fixture
def resumen_fallido(base, tmp_path):
    """Gmail rechazó el resumen semanal de Oscar; el de Anabelle salió."""
    _resumen(base, tmp_path, ProveedorSimulado(oscar="rechazar"))
    return base


def test_el_resumen_fallido_se_lista_y_se_reintenta_en_su_semana(resumen_fallido, tmp_path):
    semana = resumen.semana(AHORA)[0]
    with closing(connect(resumen_fallido)) as conn:
        lista = reintentos.por_revisar(conn, AHORA)
    assert [(a.para, a.estado, a.es_resumen, a.semana) for a in lista] == [(OSCAR, "fallido", True, semana)]
    assert lista[0].titulo == f"Resumen semanal {semana}" and not lista[0].vencido

    (outbox_id,) = _ids(resumen_fallido, "fallido")
    _reintentar(resumen_fallido, outbox_id)
    assert _estado(resumen_fallido, outbox_id)[0] == "preparado"
    assert _historial(resumen_fallido)[0][2].startswith(f"{OSCAR} · resumen semanal {semana} · antes fallido")

    sim = ProveedorSimulado()
    _resumen(resumen_fallido, tmp_path, sim, ahora=AHORA + timedelta(minutes=5))  # el siguiente envío lo lleva
    assert [para for para, *_ in sim.llamadas] == [OSCAR] and _estado(resumen_fallido, outbox_id)[0] == "aceptado"


def test_el_resumen_de_otra_semana_no_se_reintenta(resumen_fallido):
    (outbox_id,) = _ids(resumen_fallido, "fallido")
    with pytest.raises(reintentos.AvisoInvalido, match="es de otra semana"):
        _reintentar(resumen_fallido, outbox_id, ahora=AHORA + timedelta(days=7))
    assert _estado(resumen_fallido, outbox_id)[0] == "fallido"


def test_el_resumen_fallido_desde_el_panel(admin_y_encargada, resumen_fallido):
    ivania, _ = admin_y_encargada
    semana = resumen.semana(AHORA)[0]
    (outbox_id,) = _ids(resumen_fallido, "fallido")

    pagina = ivania.get("/avisos").text
    assert f"Resumen semanal {semana}" in pagina and "HTTP 400: Invalid To header (SIMULADO)" in pagina
    assert _post(ivania, f"/avisos/{outbox_id}/reintentar").status_code == 303
    assert "notify --resumen-semanal --send" in ivania.get("/avisos").text
