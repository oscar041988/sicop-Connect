"""Adaptador de Gmail (lección 7, encargo B) con sesión y flujo SIMULADOS: nunca se conecta a Google."""

import base64
import json
from email import message_from_bytes, policy

import pytest
import requests

from app.notifications import EnvioIncierto, EnvioRechazado
from app.notifications import gmail

REMITENTE = "licitaciones@ejemplo.test"


class _Respuesta:
    def __init__(self, status, cuerpo=None, texto=""):
        self.status_code, self._cuerpo, self.text = status, cuerpo, texto

    def json(self):
        if self._cuerpo is None:
            raise ValueError("sin JSON")
        return self._cuerpo


class _SesionSimulada:
    """SIMULADA: devuelve la respuesta indicada (o lanza la excepción) y guarda lo que se le pidió."""

    def __init__(self, respuesta):
        self.respuesta, self.peticiones = respuesta, []

    def post(self, url, json, timeout):
        self.peticiones.append((url, json, timeout))
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        return self.respuesta


def _proveedor(respuesta):
    sesion = _SesionSimulada(respuesta)
    return gmail.GmailProveedor(credenciales=None, remitente=REMITENTE, session=sesion), sesion


def test_envia_un_mime_con_texto_y_html_en_base64url():
    proveedor, sesion = _proveedor(_Respuesta(200, {"id": "18c2f", "labelIds": ["SENT"]}))

    assert proveedor.enviar("oscar@ejemplo.test", "SICOP · 1 oportunidad", "<p>Hola, equipo.</p>", "Hola, equipo.") == "18c2f"
    url, cuerpo, timeout = sesion.peticiones[0]
    assert url == gmail.URL_ENVIAR and timeout == gmail.TIMEOUT_S
    msg = message_from_bytes(base64.urlsafe_b64decode(cuerpo["raw"]), policy=policy.default)
    assert msg["From"] == "Hermatix · SICOP <licitaciones@ejemplo.test>"
    assert (msg["To"], msg["Subject"]) == ("oscar@ejemplo.test", "SICOP · 1 oportunidad")
    assert msg.get_body("plain").get_content().strip() == "Hola, equipo."
    assert msg.get_body("html").get_content().strip() == "<p>Hola, equipo.</p>"


@pytest.mark.parametrize("respuesta, error, texto", [
    (_Respuesta(400, {"error": {"message": "Invalid To header"}}), EnvioRechazado, "HTTP 400: Invalid To header"),
    (_Respuesta(403, None, "Forbidden"), EnvioRechazado, "HTTP 403: Forbidden"),
    (_Respuesta(500, {"error": {"message": "Backend Error"}}), EnvioIncierto, "HTTP 500: Backend Error"),
    (_Respuesta(200, {}), EnvioIncierto, "sin id"),
    (requests.Timeout(), EnvioIncierto, "no respondió en 30 s"),
    (requests.ConnectionError(), EnvioIncierto, "Conexión interrumpida"),
])
def test_cada_respuesta_de_gmail_tiene_su_estado(respuesta, error, texto):
    proveedor, _ = _proveedor(respuesta)

    with pytest.raises(error, match=texto):
        proveedor.enviar("oscar@ejemplo.test", "a", "<p>b</p>", "b")


def test_sin_token_no_hay_credenciales(tmp_path):
    with pytest.raises(gmail.GmailError, match="Falta GOOGLE_TOKEN_FILE"):
        gmail.cargar_credenciales(None)
    with pytest.raises(gmail.GmailError, match="google-auth"):
        gmail.cargar_credenciales(tmp_path / "no_existe.json")
    roto = tmp_path / "roto.json"
    roto.write_text("esto no es un token", encoding="utf-8")
    with pytest.raises(gmail.GmailError, match="no se puede leer"):
        gmail.cargar_credenciales(roto)


# --- Autorización única con un flujo SIMULADO ------------------------------------------------------------

def _id_token(email):
    def parte(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{parte({'alg': 'RS256'})}.{parte({'email': email})}.{parte('firma SIMULADA')}"


class _Credenciales:
    def __init__(self, email):
        self.id_token = _id_token(email)

    def to_json(self):
        return '{"token": "SIMULADO"}'


class _FlujoSimulado:
    def __init__(self, email):
        self.email, self.kwargs = email, None

    def run_local_server(self, **kwargs):
        self.kwargs = kwargs
        return _Credenciales(self.email)


def test_autorizar_guarda_el_token_de_la_cuenta_remitente(tmp_path):
    cliente = tmp_path / "cliente.json"
    cliente.write_text("{}", encoding="utf-8")
    token = tmp_path / "secretos" / "token.json"
    flujo = _FlujoSimulado("Licitaciones@Ejemplo.test")

    assert gmail.autorizar(cliente, token, REMITENTE, flujo=flujo) == REMITENTE
    assert token.read_text(encoding="utf-8") == '{"token": "SIMULADO"}'
    assert flujo.kwargs["login_hint"] == REMITENTE


def test_autorizar_con_otra_cuenta_no_guarda_nada(tmp_path):
    cliente = tmp_path / "cliente.json"
    cliente.write_text("{}", encoding="utf-8")
    token = tmp_path / "token.json"

    with pytest.raises(gmail.GmailError, match="Autorizaste con oscar@ejemplo.test, pero MAIL_FROM es"):
        gmail.autorizar(cliente, token, REMITENTE, flujo=_FlujoSimulado("oscar@ejemplo.test"))
    assert not token.exists()


def test_doctor_dice_si_existen_los_archivos_sin_mostrarlos(tmp_path, capsys):
    from app.cli import main
    from app.config import load_settings
    token = tmp_path / "token.json"
    token.write_text('{"refresh_token": "SECRETO-SIMULADO"}', encoding="utf-8")
    settings = load_settings(env_file=None, environ={
        "DATABASE_PATH": str(tmp_path / "x.db"), "MAIL_PROVIDER": "gmail_api",
        "GOOGLE_CLIENT_FILE": str(tmp_path / "falta.json"), "GOOGLE_TOKEN_FILE": str(token)})

    assert main(["doctor"], settings) == 0
    salida = capsys.readouterr().out
    assert "Gmail: archivo del cliente NO EXISTE · token existe" in salida
    assert "SECRETO-SIMULADO" not in salida


def test_autorizar_exige_la_configuracion(tmp_path):
    with pytest.raises(gmail.GmailError, match="GOOGLE_CLIENT_FILE"):
        gmail.autorizar(None, tmp_path / "t.json", REMITENTE, flujo=_FlujoSimulado(REMITENTE))
    with pytest.raises(gmail.GmailError, match="MAIL_FROM"):
        gmail.autorizar(tmp_path / "c.json", tmp_path / "t.json", "", flujo=_FlujoSimulado(REMITENTE))
    with pytest.raises(gmail.GmailError, match="No se encuentra"):
        gmail.autorizar(tmp_path / "c.json", tmp_path / "t.json", REMITENTE, flujo=_FlujoSimulado(REMITENTE))
