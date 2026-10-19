"""Acceso al panel (lección 6): sesión obligatoria, CSRF, hash de contraseñas y create-user.

Datos SINTÉTICOS en una base temporal; nunca toca data/.
"""

import logging
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from app import usuarios
from app.cli import main
from app.config import load_settings
from app.database import connect
from app.main import app, crear_app
from app.web.intentos import LimiteIntentos
from app.web.rutas import router
from app.web.seguridad import exigir_admin, verificar_csrf
from tests.test_panel import CONTRASENA, db, iniciar_sesion, token_csrf  # noqa: F401  (db es un fixture)

EMAIL = "ivania@ejemplo.test"


@pytest.fixture
def anonimo(db, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(db))
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, EMAIL, "Ivania", CONTRASENA)
    return TestClient(app)


def _rutas_post():
    """Rutas POST de la app y del router del panel, con sus dependencias."""
    rutas = [*app.routes, *router.routes]
    return {r.path: [d.dependency for d in r.dependencies] for r in rutas if "POST" in (getattr(r, "methods", None) or ())}


# --- Sin sesión -----------------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", ["/", "/oportunidades", "/oportunidades?familia=gps_flotas",
                                  "/oportunidades/00000000001", "/cargar"])
def test_anonimo_es_redirigido_al_login(anonimo, ruta):
    respuesta = anonimo.get(ruta, follow_redirects=False)

    assert respuesta.status_code == 303
    assert respuesta.headers["location"].startswith("/login?siguiente=")
    assert respuesta.text == ""  # ningún dato del panel


def test_anonimo_no_puede_guardar_revisiones(anonimo, db):
    respuesta = anonimo.post("/oportunidades/00000000001/revision", follow_redirects=False,
                             data={"decision": "interesa", "responsable": "Intruso"})

    assert respuesta.status_code == 303 and respuesta.headers["location"].startswith("/login")
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_health_es_publico_y_sin_datos_sensibles(anonimo):
    respuesta = anonimo.get("/health")

    assert respuesta.status_code == 200
    assert set(respuesta.json()) == {"app", "version", "environment", "database"}
    assert EMAIL not in respuesta.text and "sicop.db" not in respuesta.text


@pytest.mark.parametrize("ruta", ["/docs", "/redoc", "/openapi.json"])
def test_la_documentacion_automatica_no_se_publica(anonimo, ruta):
    assert anonimo.get(ruta, follow_redirects=False).status_code in {303, 404}
    iniciar_sesion(anonimo)
    assert anonimo.get(ruta).status_code == 404


# --- Inicio y cierre de sesión ---------------------------------------------------------------------

def test_login_correcto_da_acceso_y_vuelve_a_la_pagina_pedida(anonimo):
    destino = anonimo.get("/oportunidades/00000000001", follow_redirects=False).headers["location"]
    login = anonimo.get(destino)
    respuesta = anonimo.post("/login", follow_redirects=False, data={
        "csrf_token": token_csrf(login.text), "email": EMAIL, "contrasena": CONTRASENA,
        "siguiente": "/oportunidades/00000000001"})

    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/oportunidades/00000000001"
    detalle = anonimo.get("/oportunidades/00000000001")
    assert detalle.status_code == 200 and "<mark>monitoreo GPS</mark>" in detalle.text
    assert detalle.headers["cache-control"] == "no-store"  # «atrás» tras cerrar sesión no muestra datos


@pytest.mark.parametrize("email, contrasena", [
    (EMAIL, "otra contraseña equivocada"),
    ("nadie@ejemplo.test", CONTRASENA),
    (EMAIL, ""),
    (EMAIL, "x" * 10_000),  # demasiado larga: se rechaza sin calcular el hash
])
def test_login_incorrecto_no_da_acceso_ni_revela_que_fallo(anonimo, email, contrasena):
    respuesta = iniciar_sesion(anonimo, email, contrasena)

    assert respuesta.status_code == 401 and "Correo o contraseña incorrectos." in respuesta.text
    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303


def test_usuario_inactivo_no_entra(anonimo, db):
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE users SET active = 0")

    assert iniciar_sesion(anonimo).status_code == 401


@pytest.mark.parametrize("siguiente", ["//otro-sitio.test/robar", "https://otro-sitio.test", "/\\otro-sitio.test"])
def test_login_no_redirige_a_otro_sitio(anonimo, siguiente):
    token = token_csrf(anonimo.get("/login").text)
    respuesta = anonimo.post("/login", follow_redirects=False, data={
        "csrf_token": token, "email": EMAIL, "contrasena": CONTRASENA, "siguiente": siguiente})

    assert respuesta.headers["location"] == "/oportunidades"


# --- Límite de intentos de login ---------------------------------------------------------------------

def _fallar(cliente, veces, email=EMAIL):
    return [iniciar_sesion(cliente, email, "contraseña equivocada").status_code for _ in range(veces)]


def test_al_quinto_fallo_se_bloquea_aunque_despues_acierte(anonimo, caplog):
    caplog.set_level(logging.WARNING)

    assert _fallar(anonimo, 5) == [401, 401, 401, 401, 429]
    correcta = iniciar_sesion(anonimo)

    assert correcta.status_code == 429 and "Demasiados intentos. Espera 15 minutos" in correcta.text
    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303  # no entró
    assert caplog.text.count("Login fallido para 'ivania@ejemplo.test' desde testclient") == 5
    assert "Login bloqueado 15 min" in caplog.text and "contraseña equivocada" not in caplog.text


def test_el_bloqueo_no_afecta_a_otro_correo(anonimo, db):
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "oscar@ejemplo.test", "Oscar", CONTRASENA)
    _fallar(anonimo, 5)

    assert iniciar_sesion(anonimo, "oscar@ejemplo.test").status_code == 303


def test_entrar_bien_pone_el_contador_en_cero(anonimo):
    assert _fallar(anonimo, 4) == [401] * 4
    assert iniciar_sesion(anonimo).status_code == 303

    otra_ventana = TestClient(app)  # misma app, mismo contador
    assert _fallar(otra_ventana, 4) == [401] * 4


class _Reloj:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora


def test_el_bloqueo_dura_15_minutos_y_cuenta_por_correo_e_ip():
    reloj = _Reloj()
    limite = LimiteIntentos(reloj)
    clave = limite.clave("  Ivania@Ejemplo.TEST ", "1.2.3.4")
    assert clave == ("ivania@ejemplo.test", "1.2.3.4")  # mayúsculas y espacios no esquivan el contador

    assert [limite.registrar_fallo(clave) for _ in range(5)] == [False] * 4 + [True]
    assert limite.segundos_de_bloqueo(clave) == 15 * 60 + 1
    assert limite.segundos_de_bloqueo(limite.clave("ivania@ejemplo.test", "5.6.7.8")) == 0  # otra IP

    reloj.ahora += 15 * 60
    assert limite.segundos_de_bloqueo(clave) == 0
    assert limite.registrar_fallo(clave) is False  # vuelve a empezar desde cero


def test_los_fallos_viejos_no_cuentan():
    reloj = _Reloj()
    limite = LimiteIntentos(reloj)
    clave = limite.clave(EMAIL, "1.2.3.4")
    for _ in range(4):
        limite.registrar_fallo(clave)

    reloj.ahora += 15 * 60  # pasaron los 15 minutos de la ventana
    assert limite.registrar_fallo(clave) is False and limite.segundos_de_bloqueo(clave) == 0


def test_cerrar_sesion(anonimo):
    iniciar_sesion(anonimo)
    token = token_csrf(anonimo.get("/oportunidades").text)

    respuesta = anonimo.post("/logout", data={"csrf_token": token}, follow_redirects=False)

    assert respuesta.status_code == 303 and respuesta.headers["location"] == "/login"
    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303


def test_la_sesion_vence(anonimo, monkeypatch):
    iniciar_sesion(anonimo)
    duracion = load_settings().session_max_age
    hora_del_login = TimestampSigner.get_timestamp(TimestampSigner("x"))
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: hora_del_login + duracion + 1)

    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303


# --- Cookie ---------------------------------------------------------------------------------------

def test_cookie_firmada_httponly_lax_y_con_vencimiento(anonimo):
    cookie = iniciar_sesion(anonimo).headers["set-cookie"].lower()

    assert cookie.startswith("sicop_sesion=")
    assert "httponly" in cookie and "samesite=lax" in cookie and f"max-age={8 * 3600}" in cookie
    assert "secure" not in cookie  # development: http://127.0.0.1 no usa HTTPS


def test_cookie_alterada_no_sirve(anonimo):
    iniciar_sesion(anonimo)
    valor = anonimo.cookies["sicop_sesion"]
    anonimo.cookies.set("sicop_sesion", valor[:-2] + ("AA" if not valor.endswith("AA") else "BB"))

    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303


def test_en_produccion_la_cookie_es_secure_y_el_secreto_es_obligatorio(db):
    entorno = {"APP_ENV": "production", "DATABASE_PATH": str(db), "SESSION_MAX_AGE_HOURS": "2"}
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        crear_app(load_settings(env_file=None, environ=entorno))

    produccion = crear_app(load_settings(env_file=None, environ={**entorno, "SESSION_SECRET": "s" * 48}))
    cookie = TestClient(produccion, base_url="https://testserver").get("/login").headers["set-cookie"].lower()
    assert "secure" in cookie and f"max-age={2 * 3600}" in cookie


# --- CSRF -----------------------------------------------------------------------------------------

def test_todas_las_rutas_post_exigen_el_token():
    rutas = _rutas_post()

    assert sorted(rutas) == ["/cargar", "/destinatarios", "/destinatarios/{destinatario_id}/estado", "/login",
                             "/logout", "/oportunidades/{nro_sicop}/revision",  # una ruta nueva se agrega aquí
                             "/usuarios", "/usuarios/{user_id}/contrasena", "/usuarios/{user_id}/estado",
                             "/usuarios/{user_id}/nivel"]
    assert all(verificar_csrf in dependencias for dependencias in rutas.values())
    assert all(exigir_admin in dependencias for ruta, dependencias in rutas.items() if ruta.startswith(("/usuarios", "/destinatarios")))


@pytest.mark.parametrize("token", [None, "", "token-inventado"])
@pytest.mark.parametrize("ruta", ["/login", "/logout", "/oportunidades/00000000001/revision", "/cargar"])
def test_post_sin_token_valido_es_rechazado(anonimo, db, ruta, token):
    iniciar_sesion(anonimo)
    datos = {"decision": "interesa", "responsable": "Ivania", "email": EMAIL, "contrasena": CONTRASENA}
    if token is not None:
        datos["csrf_token"] = token

    respuesta = anonimo.post(ruta, data=datos, follow_redirects=False)

    assert respuesta.status_code == 403 and "Recarga la página" in respuesta.text
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0
    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 200  # la sesión sigue


def test_el_token_de_otra_sesion_no_sirve(anonimo, db):
    otro = TestClient(app)
    token_ajeno = token_csrf(otro.get("/login").text)
    iniciar_sesion(anonimo)

    respuesta = anonimo.post("/oportunidades/00000000001/revision",
                             data={"decision": "interesa", "responsable": "Ivania", "csrf_token": token_ajeno})

    assert respuesta.status_code == 403


# --- Contraseñas: hash y logs ----------------------------------------------------------------------

def test_la_base_guarda_un_hash_argon2_y_no_la_contrasena(anonimo, db):
    with closing(sqlite3.connect(db)) as conn:
        guardado = conn.execute("SELECT password_hash FROM users").fetchone()[0]

    assert guardado.startswith("$argon2id$") and CONTRASENA not in guardado
    assert CONTRASENA.encode() not in db.read_bytes()


def test_la_contrasena_nunca_aparece_en_logs_ni_en_pantalla(db, monkeypatch, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": CONTRASENA)
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})

    assert main(["create-user", "--email", EMAIL, "--nombre", "Ivania", "--rol", "admin"], settings) == 0
    cliente = TestClient(app)
    ok = iniciar_sesion(cliente)
    malo = iniciar_sesion(TestClient(app), EMAIL, CONTRASENA + " equivocada")

    salida = capsys.readouterr()
    assert ok.status_code == 303 and malo.status_code == 401
    assert "Usuario creado" in salida.out
    for texto in (caplog.text, salida.out, salida.err, malo.text, ok.headers["set-cookie"]):
        assert CONTRASENA not in texto


# --- create-user ----------------------------------------------------------------------------------

@pytest.mark.parametrize("contrasenas, mensaje", [
    (["corta", "corta"], "al menos 10 caracteres"),
    ([CONTRASENA, "otra contraseña distinta"], "no coinciden"),
])
def test_create_user_valida_la_contrasena(db, monkeypatch, capsys, contrasenas, mensaje):
    respuestas = iter(contrasenas)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(respuestas))
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})

    assert main(["create-user", "--email", EMAIL, "--nombre", "Ivania", "--rol", "admin"], settings) == 1
    assert mensaje in capsys.readouterr().err
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 0


def test_minimo_de_10_caracteres_y_consejo_de_frase():
    with pytest.raises(usuarios.UsuarioInvalido, match="al menos 10 caracteres. Consejo: usa 3 o 4 palabras"):
        usuarios.validar_contrasena("x" * 9)
    usuarios.validar_contrasena("x" * 10)               # 10 exactos sirven
    usuarios.validar_contrasena("cafe verde lunes")     # una frase con espacios también


def test_create_user_muestra_el_consejo(db, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": CONTRASENA)
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})

    assert main(["create-user", "--email", EMAIL, "--nombre", "Ivania", "--rol", "admin"], settings) == 0
    assert "al menos 10 caracteres. Consejo: usa 3 o 4 palabras" in capsys.readouterr().out


def test_create_user_no_duplica_el_correo(anonimo, db, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": CONTRASENA)
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})

    assert main(["create-user", "--email", EMAIL.upper(), "--nombre", "Otra", "--rol", "encargado"], settings) == 1
    assert "Ya existe" in capsys.readouterr().err


# --- set-password, deactivate-user, activate-user, list-users ---------------------------------------------

NUEVA = "otra contraseña sintética larga"


def _cli(db, *argumentos):
    return main(list(argumentos), load_settings(env_file=None, environ={"DATABASE_PATH": str(db)}))


def test_set_password_cambia_la_contrasena_y_cierra_las_sesiones_abiertas(anonimo, db, monkeypatch, capsys):
    iniciar_sesion(anonimo)
    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 200
    monkeypatch.setattr("getpass.getpass", lambda prompt="": NUEVA)

    assert _cli(db, "set-password", "--email", EMAIL) == 0

    salida = capsys.readouterr()
    assert "Contraseña cambiada" in salida.out and NUEVA not in salida.out + salida.err
    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303  # la sesión abierta ya no vale
    assert iniciar_sesion(TestClient(app)).status_code == 401              # la vieja ya no entra
    assert iniciar_sesion(TestClient(app), EMAIL, NUEVA).status_code == 303  # la nueva sí


@pytest.mark.parametrize("argumentos, contrasenas, mensaje", [
    (["--email", EMAIL], ["corta", "corta"], "al menos 10 caracteres"),
    (["--email", EMAIL], [NUEVA, "otra distinta y larga"], "no coinciden"),
    (["--email", "nadie@ejemplo.test"], [NUEVA, NUEVA], "No hay un usuario"),
])
def test_set_password_valida(anonimo, db, monkeypatch, capsys, argumentos, contrasenas, mensaje):
    respuestas = iter(contrasenas)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(respuestas))

    assert _cli(db, "set-password", *argumentos) == 1
    assert mensaje in capsys.readouterr().err
    assert iniciar_sesion(anonimo).status_code == 303  # la contraseña de antes sigue sirviendo


def test_desactivar_cierra_la_sesion_abierta_y_conserva_las_revisiones(anonimo, db, capsys):
    iniciar_sesion(anonimo)
    token = token_csrf(anonimo.get("/oportunidades/00000000001").text)
    anonimo.post("/oportunidades/00000000001/revision", data={"decision": "interesa", "csrf_token": token})

    assert _cli(db, "deactivate-user", "--email", EMAIL.upper()) == 0
    assert "Usuario desactivado" in capsys.readouterr().out

    assert anonimo.get("/oportunidades", follow_redirects=False).status_code == 303
    assert iniciar_sesion(TestClient(app)).status_code == 401
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT responsable FROM reviews").fetchall() == [("Ivania",)]

    assert _cli(db, "deactivate-user", "--email", EMAIL) == 0
    assert "ya estaba desactivado" in capsys.readouterr().out
    assert _cli(db, "activate-user", "--email", EMAIL) == 0
    assert iniciar_sesion(TestClient(app)).status_code == 303


def test_activar_un_correo_que_no_existe(db, capsys):
    assert _cli(db, "activate-user", "--email", "nadie@ejemplo.test") == 1
    assert "No hay un usuario" in capsys.readouterr().err


def test_list_users_no_muestra_el_hash(anonimo, db, capsys):
    _cli(db, "deactivate-user", "--email", EMAIL)
    capsys.readouterr()

    assert _cli(db, "list-users") == 0

    salida = capsys.readouterr().out
    assert EMAIL in salida and "Ivania" in salida and "desactivado" in salida
    assert "argon2" not in salida


def test_una_sesion_de_antes_de_la_huella_tiene_que_volver_a_entrar(anonimo, db):
    iniciar_sesion(anonimo)
    with closing(connect(db)) as conn:
        assert not usuarios.sesion_vigente(conn, 1, None)  # sesiones viejas no guardaban la huella
