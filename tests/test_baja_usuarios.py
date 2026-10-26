"""Baja definitiva de usuarios («Eliminar», migración 0016; decisión de Ivania, 2026-10-26).

Datos SINTÉTICOS en una base temporal; nunca toca data/.
"""

import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app import destinatarios, usuarios
from app.database import connect
from app.historial import TERMINAL
from app.main import app
from tests.test_panel import CONTRASENA, iniciar_sesion, token_csrf
from tests.test_seguimiento import NRO, _asignar, _dar_seguimiento, _id, clientes, db  # noqa: F401  (fixtures)


def _eliminar(cliente, user_id, confirmar="si"):
    token = token_csrf(cliente.get("/usuarios").text)
    datos = {"csrf_token": token, **({"confirmar": confirmar} if confirmar else {})}
    return cliente.post(f"/usuarios/{user_id}/eliminar", data=datos, follow_redirects=False)


def test_eliminar_cierra_la_sesion_libera_el_correo_y_conserva_lo_que_hizo(clientes, db):
    ana = _id(db, "ana@ejemplo.test")
    assert _dar_seguimiento(clientes["ana"]).status_code == 303  # algo hecho por Ana, que debe quedar

    respuesta = _eliminar(clientes["oscar"], ana)

    assert respuesta.status_code == 303
    pagina = clientes["oscar"].get("/usuarios").text
    assert "Ana fue eliminado" in pagina and "ana@ejemplo.test" in pagina  # mensaje e historial
    assert "Eliminó un usuario: Ana (ana@ejemplo.test)" in pagina
    assert f'action="/usuarios/{ana}/' not in pagina  # ya no está en la lista
    # Su sesión abierta se cerró y no puede volver a entrar.
    assert clientes["ana"].get("/oportunidades", follow_redirects=False).status_code in (303, 401)
    assert iniciar_sesion(TestClient(app), "ana@ejemplo.test").status_code != 303
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT abierto_por, abierto_por_nombre FROM seguimientos").fetchone() == (ana, "Ana")
        assert conn.execute("SELECT nombre, active, email FROM users WHERE id = ?", (ana,)).fetchone() == (
            "Ana", 0, f"eliminado-{ana}@baja.invalid")
        # El correo quedó libre: se puede crear otra cuenta con él.
        usuarios.crear_usuario(conn, "ana@ejemplo.test", "Ana Nueva", CONTRASENA)


def test_sin_marcar_la_casilla_no_se_elimina(clientes, db):
    respuesta = _eliminar(clientes["oscar"], _id(db, "ana@ejemplo.test"), confirmar="")

    assert respuesta.status_code == 400 and "Entiendo que no se puede deshacer" in respuesta.text
    assert iniciar_sesion(TestClient(app), "ana@ejemplo.test").status_code == 303


def test_un_encargado_no_puede_eliminar(clientes, db):
    token = token_csrf(clientes["ivania"].get("/oportunidades").text)
    respuesta = clientes["ivania"].post(f"/usuarios/{_id(db, 'ana@ejemplo.test')}/eliminar",
                                        data={"csrf_token": token, "confirmar": "si"}, follow_redirects=False)

    assert respuesta.status_code == 403
    assert iniciar_sesion(TestClient(app), "ana@ejemplo.test").status_code == 303


def test_sin_token_csrf_no_se_elimina(clientes, db):
    respuesta = clientes["oscar"].post(f"/usuarios/{_id(db, 'ana@ejemplo.test')}/eliminar",
                                       data={"confirmar": "si"}, follow_redirects=False)

    assert respuesta.status_code == 403


def test_no_se_elimina_a_si_mismo_ni_al_ultimo_administrador(clientes, db):
    oscar = _id(db, "oscar@ejemplo.test")

    assert "No puedes eliminarte" in _eliminar(clientes["oscar"], oscar).text
    with closing(connect(db)) as conn, pytest.raises(usuarios.UsuarioInvalido, match="al menos un administrador"):
        usuarios.eliminar(conn, oscar, TERMINAL)


def test_encargado_de_expedientes_se_bloquea_hasta_reasignar(clientes, db):
    ana, ivania = _id(db, "ana@ejemplo.test"), _id(db, "ivania@ejemplo.test")
    _dar_seguimiento(clientes["oscar"])
    _asignar(clientes["oscar"], ana)

    bloqueado = _eliminar(clientes["oscar"], ana)

    assert bloqueado.status_code == 400 and NRO in bloqueado.text and "Asigna otro encargado" in bloqueado.text
    _asignar(clientes["oscar"], ivania)
    assert _eliminar(clientes["oscar"], ana).status_code == 303
    with closing(connect(db)) as conn:  # el historial de encargados conserva a Ana
        assert [n for (n,) in conn.execute("SELECT encargado_nombre FROM seguimiento_asignaciones ORDER BY id")] \
            == ["Ana", "Ivania"]


def test_destinatario_de_avisos_se_bloquea_hasta_quitarlo(clientes, db):
    ana = _id(db, "ana@ejemplo.test")
    with closing(connect(db)) as conn:
        destinatario = destinatarios.agregar(conn, "ANA@ejemplo.test", "Ana")

    assert "sigue recibiendo los avisos" in _eliminar(clientes["oscar"], ana).text
    with closing(connect(db)) as conn:
        destinatarios.cambiar_estado(conn, destinatario, False)
    assert _eliminar(clientes["oscar"], ana).status_code == 303


def test_un_eliminado_no_se_reactiva_ni_se_borra(db):
    with closing(connect(db)) as conn:
        ana = usuarios.buscar_id(conn, "ana@ejemplo.test")
        usuarios.eliminar(conn, ana, TERMINAL)

        with pytest.raises(usuarios.UsuarioInvalido, match="fue eliminado"):
            usuarios.cambiar_estado(conn, ana, True, TERMINAL)
        with pytest.raises(usuarios.UsuarioInvalido, match="fue eliminado"):
            usuarios.eliminar(conn, ana, TERMINAL)
        for sql in ("UPDATE users SET active = 1 WHERE id = ?", "UPDATE users SET eliminado_en = NULL WHERE id = ?",
                    "DELETE FROM users WHERE id = ?"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql, (ana,))
        assert [u.nombre for u in usuarios.listar(conn)] == ["Ivania", "Oscar"]
