"""Niveles de acceso (aprobados por Oscar, 2026-10-12) y página «Usuarios» con su historial.

Datos SINTÉTICOS en una base temporal; nunca toca data/.
"""

import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app import historial, usuarios
from app.cli import main
from app.config import load_settings
from app.database import connect
from app.main import app
from tests.test_panel import CONTRASENA, db, iniciar_sesion, token_csrf  # noqa: F401  (db es un fixture)

NUEVA = "otra contraseña sintética larga"


def _crear(db, email, nombre, rol):
    with closing(connect(db)) as conn:
        return usuarios.crear_usuario(conn, email, nombre, CONTRASENA, rol)


def _entrar(email):
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, email).status_code == 303
    return cliente


@pytest.fixture
def equipo(db, monkeypatch):
    """Ivania (administradora) y Anabelle (encargada), cada una con su sesión abierta."""
    monkeypatch.setenv("DATABASE_PATH", str(db))
    ids = {"ivania": _crear(db, "ivania@ejemplo.test", "Ivania", "admin"),
           "anabelle": _crear(db, "anabelle@ejemplo.test", "Anabelle", "encargado")}
    return ids, _entrar("ivania@ejemplo.test"), _entrar("anabelle@ejemplo.test")


def _post(cliente, ruta, **datos):
    token = token_csrf(cliente.get("/oportunidades").text)
    return cliente.post(ruta, data={"csrf_token": token, **datos}, follow_redirects=False)


def _usuario(db, email):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT role, active FROM users WHERE email = ?", (email,)).fetchone()


def _historial(db):
    with closing(connect(db)) as conn:
        return [(e.actor, e.accion, e.detalle) for e in historial.ultimos(conn, historial.DE_USUARIOS)]


# --- Qué puede hacer cada nivel ------------------------------------------------------------------------

def test_la_encargada_revisa_y_sube_archivos_pero_no_ve_usuarios(equipo, db):
    ids, _, anabelle = equipo

    assert anabelle.get("/cargar").status_code == 200
    assert _post(anabelle, "/oportunidades/00000000001/revision", decision="interesa").status_code == 303
    assert 'href="/usuarios"' not in anabelle.get("/oportunidades").text

    pagina = anabelle.get("/usuarios")  # aunque escriba la dirección a mano
    assert pagina.status_code == 403 and "solo para administradores" in pagina.text
    for ruta, datos in [("/usuarios", {"email": "x@ejemplo.test", "nombre": "X", "rol": "admin",
                                       "contrasena": NUEVA, "repetir": NUEVA}),
                        (f"/usuarios/{ids['anabelle']}/nivel", {"rol": "admin"}),
                        (f"/usuarios/{ids['ivania']}/estado", {"activo": "0"}),
                        (f"/usuarios/{ids['ivania']}/contrasena", {"contrasena": NUEVA, "repetir": NUEVA})]:
        assert _post(anabelle, ruta, **datos).status_code == 403, ruta
    assert _usuario(db, "anabelle@ejemplo.test") == ("encargado", 1)
    assert _usuario(db, "ivania@ejemplo.test") == ("admin", 1) and _usuario(db, "x@ejemplo.test") is None
    assert iniciar_sesion(TestClient(app), "ivania@ejemplo.test").status_code == 303  # su contraseña no cambió


def test_la_administradora_ve_la_pagina_de_usuarios_sin_hashes(equipo):
    _, ivania, _ = equipo

    pagina = ivania.get("/usuarios")

    assert pagina.status_code == 200 and 'href="/usuarios" aria-current="page"' in pagina.text
    assert "anabelle@ejemplo.test" in pagina.text and "Encargado" in pagina.text
    assert "argon2" not in pagina.text and CONTRASENA not in pagina.text


# --- Gestión desde el panel ----------------------------------------------------------------------------

def test_crear_un_usuario_desde_el_panel(equipo, db):
    _, ivania, _ = equipo

    respuesta = _post(ivania, "/usuarios", email="oscar@ejemplo.test", nombre="Oscar", rol="admin",
                      contrasena=NUEVA, repetir=NUEVA)

    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/usuarios"
    pagina = ivania.get("/usuarios").text
    assert "Usuario creado: oscar@ejemplo.test." in pagina and NUEVA not in pagina
    assert "Usuario creado" not in ivania.get("/usuarios").text  # el mensaje se muestra una sola vez
    assert _usuario(db, "oscar@ejemplo.test") == ("admin", 1)
    assert _historial(db)[0] == ("Ivania", "crear_usuario", "oscar@ejemplo.test (Administrador)")
    assert iniciar_sesion(TestClient(app), "oscar@ejemplo.test", NUEVA).status_code == 303


@pytest.mark.parametrize("datos, mensaje", [
    ({"contrasena": NUEVA, "repetir": NUEVA + "x"}, "no coinciden"),
    ({"contrasena": "corta", "repetir": "corta"}, "al menos 10 caracteres"),
    ({"email": "anabelle@ejemplo.test"}, "Ya existe"),
    ({"email": "no-es-correo"}, "correo no es válido"),
    ({"rol": "jefe"}, "Administrador o Encargado"),
])
def test_crear_un_usuario_invalido(equipo, db, datos, mensaje):
    _, ivania, _ = equipo
    formulario = {"email": "oscar@ejemplo.test", "nombre": "Oscar", "rol": "encargado",
                  "contrasena": NUEVA, "repetir": NUEVA, **datos}

    respuesta = _post(ivania, "/usuarios", **formulario)

    assert respuesta.status_code == 400 and mensaje in respuesta.text
    assert formulario["contrasena"] not in respuesta.text  # la contraseña nunca vuelve al formulario
    assert _usuario(db, "oscar@ejemplo.test") is None


def test_cambiar_el_nivel_aplica_en_el_siguiente_clic(equipo, db):
    ids, ivania, anabelle = equipo

    assert _post(ivania, f"/usuarios/{ids['anabelle']}/nivel", rol="admin").status_code == 303

    assert anabelle.get("/usuarios").status_code == 200  # sin volver a iniciar sesión
    assert _post(ivania, f"/usuarios/{ids['anabelle']}/nivel", rol="encargado").status_code == 303
    assert anabelle.get("/usuarios").status_code == 403
    assert _historial(db)[:2] == [("Ivania", "cambiar_nivel", "anabelle@ejemplo.test: Administrador → Encargado"),
                                  ("Ivania", "cambiar_nivel", "anabelle@ejemplo.test: Encargado → Administrador")]


def test_desactivar_desde_el_panel_cierra_su_sesion(equipo, db):
    ids, ivania, anabelle = equipo

    assert _post(ivania, f"/usuarios/{ids['anabelle']}/estado", activo="0").status_code == 303

    assert anabelle.get("/oportunidades", follow_redirects=False).status_code == 303
    assert "Usuario desactivado" in ivania.get("/usuarios").text
    assert _post(ivania, f"/usuarios/{ids['anabelle']}/estado", activo="1").status_code == 303
    assert _usuario(db, "anabelle@ejemplo.test") == ("encargado", 1)
    assert [a for _, a, _ in _historial(db)[:2]] == ["activar", "desactivar"]


def test_poner_contrasena_a_otra_persona_cierra_su_sesion(equipo):
    ids, ivania, anabelle = equipo

    assert _post(ivania, f"/usuarios/{ids['anabelle']}/contrasena", contrasena=NUEVA, repetir=NUEVA).status_code == 303

    assert anabelle.get("/oportunidades", follow_redirects=False).status_code == 303
    assert iniciar_sesion(TestClient(app), "anabelle@ejemplo.test", NUEVA).status_code == 303


def test_cambiar_su_propia_contrasena_no_la_saca_del_panel(equipo):
    ids, ivania, _ = equipo
    otra_ventana = _entrar("ivania@ejemplo.test")

    assert _post(ivania, f"/usuarios/{ids['ivania']}/contrasena", contrasena=NUEVA, repetir=NUEVA).status_code == 303

    assert "Tu contraseña cambió" in ivania.get("/usuarios").text  # esta sesión sigue
    assert otra_ventana.get("/oportunidades", follow_redirects=False).status_code == 303  # la otra se cerró


@pytest.mark.parametrize("ruta, datos, mensaje", [
    ("estado", {"activo": "0"}, "No puedes desactivarte"),
    ("nivel", {"rol": "encargado"}, "No puedes quitarte"),
])
def test_nadie_se_quita_a_si_mismo_el_acceso(equipo, db, ruta, datos, mensaje):
    ids, ivania, _ = equipo

    respuesta = _post(ivania, f"/usuarios/{ids['ivania']}/{ruta}", **datos)

    assert respuesta.status_code == 400 and mensaje in respuesta.text
    assert _usuario(db, "ivania@ejemplo.test") == ("admin", 1)


def test_siempre_queda_un_administrador_activo(equipo, db):
    ids, _, _ = equipo
    with closing(connect(db)) as conn:
        for cambio in (lambda: usuarios.cambiar_estado(conn, ids["ivania"], False),
                       lambda: usuarios.cambiar_nivel(conn, ids["ivania"], "encargado")):
            with pytest.raises(usuarios.UsuarioInvalido, match="al menos un administrador"):
                cambio()
        # Con un segundo administrador, ya se puede.
        usuarios.cambiar_nivel(conn, ids["anabelle"], "admin")
        assert usuarios.cambiar_estado(conn, ids["ivania"], False) is True


def test_un_id_que_no_existe(equipo):
    _, ivania, _ = equipo

    respuesta = _post(ivania, "/usuarios/999/estado", activo="0")

    assert respuesta.status_code == 400 and "no existe" in respuesta.text


# --- Historial --------------------------------------------------------------------------------------------

def test_el_historial_no_se_borra_ni_se_modifica(equipo, db):
    with closing(sqlite3.connect(db)) as conn:
        for sql in ("DELETE FROM audit_log", "UPDATE audit_log SET actor = 'otra'"):
            with pytest.raises(sqlite3.IntegrityError, match="historial no se"):
                conn.execute(sql)


def test_el_historial_se_muestra_y_no_guarda_contrasenas(equipo, db):
    ids, ivania, _ = equipo
    _post(ivania, f"/usuarios/{ids['anabelle']}/contrasena", contrasena=NUEVA, repetir=NUEVA)

    pagina = ivania.get("/usuarios").text

    assert "Puso una contraseña nueva: anabelle@ejemplo.test · Ivania" in pagina
    assert "Creó un usuario: anabelle@ejemplo.test (Encargado) · terminal" in pagina
    with closing(sqlite3.connect(db)) as conn:
        assert NUEVA not in " ".join(str(c) for fila in conn.execute("SELECT * FROM audit_log") for c in fila)


# --- Terminal ---------------------------------------------------------------------------------------------

def _cli(db, *argumentos):
    return main(list(argumentos), load_settings(env_file=None, environ={"DATABASE_PATH": str(db)}))


def test_set_role_y_list_users(equipo, db, capsys):
    assert _cli(db, "set-role", "--email", "anabelle@ejemplo.test", "--rol", "admin") == 0
    assert "ahora es Administrador" in capsys.readouterr().out
    assert _historial(db)[0] == ("terminal", "cambiar_nivel", "anabelle@ejemplo.test: Encargado → Administrador")

    assert _cli(db, "list-users") == 0
    salida = capsys.readouterr().out
    assert "anabelle@ejemplo.test" in salida and "Administrador" in salida and "argon2" not in salida


def test_set_role_valida(equipo, db, capsys):
    assert _cli(db, "set-role", "--email", "ivania@ejemplo.test", "--rol", "encargado") == 1  # única administradora
    assert "al menos un administrador" in capsys.readouterr().err
    assert _cli(db, "set-role", "--email", "nadie@ejemplo.test", "--rol", "admin") == 1
    assert "No hay un usuario" in capsys.readouterr().err


def test_create_user_pregunta_el_nivel(db, monkeypatch, capsys):
    _cli(db, "migrate")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": CONTRASENA)
    monkeypatch.setattr("builtins.input", lambda prompt="": "Encargado")

    assert _cli(db, "create-user", "--email", "oscar@ejemplo.test", "--nombre", "Oscar") == 0

    assert "(Encargado)" in capsys.readouterr().out
    assert _usuario(db, "oscar@ejemplo.test") == ("encargado", 1)
