"""Envío por la API de Gmail (lección 7, encargo B). Ver docs/GOOGLE_API.md.

Permiso: OAuth de la cuenta remitente (licitaciones@), con gmail.send (solo enviar). La autorización se hace una
vez con python -m app.cli google-auth; el token queda en GOOGLE_TOKEN_FILE, fuera del proyecto.

Qué significa cada respuesta de Gmail:
* 2xx con id del mensaje → aceptado (Gmail lo tomó; no es lo mismo que «llegó a la bandeja»).
* 4xx → rechazado (fallido): Gmail dijo que no, el correo no salió.
* 5xx, timeout, conexión cortada o 2xx sin id → incierto: quizá salió. No se reintenta solo.

Nunca se escribe el token ni el contenido del JSON en mensajes, logs o la outbox.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path

import google.auth.exceptions
import requests
from google.auth import jwt
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials

from app.notifications import EnvioIncierto, EnvioRechazado

SCOPE_ENVIAR = "https://www.googleapis.com/auth/gmail.send"
# openid + email: solo para comprobar qué cuenta autorizó (debe ser MAIL_FROM). No dan acceso al correo.
SCOPES_CUENTA = ["openid", "https://www.googleapis.com/auth/userinfo.email"]
SCOPES = [SCOPE_ENVIAR, *SCOPES_CUENTA]
URL_ENVIAR = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
TIMEOUT_S = 30
NOMBRE_REMITENTE = "Hermatix · SICOP"
MAX_DETALLE = 300  # caracteres de la respuesta de Google que se guardan


class GmailError(Exception):
    """No se puede usar Gmail (falta el token, venció, cuenta equivocada…). Nada se envió ni se leyó."""


@dataclass(frozen=True)
class Permiso:
    """Un permiso de Gmail con su propio token: enviar avisos (este módulo) o leer el buzón (app/sources/gmail_reader)."""

    scope: str          # el permiso de Gmail (el token se carga solo con él)
    var_token: str      # variable de .env con la ruta del token
    var_cuenta: str     # variable de .env con la cuenta que debe autorizar
    para_que: str       # para qué es esa cuenta (mensajes de error)
    comando: str        # comando que repite la autorización
    pantalla: str       # lo que Google muestra al pedir el permiso

    @property
    def scopes(self) -> list[str]:
        return [self.scope, *SCOPES_CUENTA]


PERMISO_ENVIAR = Permiso(SCOPE_ENVIAR, "GOOGLE_TOKEN_FILE", "MAIL_FROM", "la cuenta que envía los avisos",
                         "python -m app.cli google-auth", "«Enviar correo en tu nombre»")


def construir_mensaje(remitente: str, para: str, asunto: str, html: str, texto: str) -> EmailMessage:
    """Correo con texto plano y, como alternativa, HTML (el programa de correo elige cuál mostrar)."""
    usuario, _, dominio = remitente.partition("@")
    msg = EmailMessage()
    msg["From"] = Address(NOMBRE_REMITENTE, usuario, dominio)
    msg["To"] = para
    msg["Subject"] = asunto
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")
    return msg


def _raw(msg: EmailMessage) -> str:
    """El formato que pide la API: el correo completo en base64 «url-safe»."""
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def _resumen_error(respuesta: requests.Response) -> str:
    try:
        mensaje = respuesta.json().get("error", {}).get("message", "")
    except ValueError:
        mensaje = respuesta.text
    return f"HTTP {respuesta.status_code}: {mensaje}"[:MAX_DETALLE]


class GmailProveedor:
    """Proveedor de app/avisos.py: enviar() devuelve el id de Gmail o lanza EnvioRechazado / EnvioIncierto."""

    def __init__(self, credenciales: Credentials, remitente: str, session: requests.Session | None = None):
        self.remitente = remitente
        self.session = session or AuthorizedSession(credenciales)

    def enviar(self, para: str, asunto: str, html: str, texto: str) -> str:
        cuerpo = {"raw": _raw(construir_mensaje(self.remitente, para, asunto, html, texto))}
        try:
            respuesta = self.session.post(URL_ENVIAR, json=cuerpo, timeout=TIMEOUT_S)
        except requests.Timeout:
            raise EnvioIncierto(f"Gmail no respondió en {TIMEOUT_S} s") from None
        except (requests.ConnectionError, google.auth.exceptions.TransportError) as exc:
            raise EnvioIncierto(f"Conexión interrumpida: {type(exc).__name__}") from None
        if 400 <= respuesta.status_code < 500:
            raise EnvioRechazado(_resumen_error(respuesta))
        if respuesta.status_code >= 300:
            raise EnvioIncierto(_resumen_error(respuesta))
        try:
            id_mensaje = respuesta.json().get("id")
        except ValueError:
            id_mensaje = None
        if not id_mensaje:
            raise EnvioIncierto(f"HTTP {respuesta.status_code} sin id de mensaje")
        return str(id_mensaje)


def cargar_credenciales(token_file: Path | None, permiso: Permiso = PERMISO_ENVIAR) -> Credentials:
    """Lee el token guardado y lo renueva si venció. Si no sirve, GmailError (antes de tocar la outbox o el buzón)."""
    rehacer = f"Repite la autorización: {permiso.comando} (entrando como {permiso.var_cuenta})."
    if token_file is None:
        raise GmailError(f"Falta {permiso.var_token} en .env.")
    if not token_file.is_file():
        raise GmailError(f"No hay token guardado en {permiso.var_token}. {rehacer}")
    try:
        credenciales = Credentials.from_authorized_user_file(str(token_file), [permiso.scope])
    except (ValueError, OSError, json.JSONDecodeError):
        raise GmailError(f"El token guardado no se puede leer. {rehacer}") from None
    if not credenciales.valid:
        try:
            credenciales.refresh(Request())
        except google.auth.exceptions.RefreshError:
            raise GmailError(f"Google ya no acepta el token (contraseña cambiada o acceso retirado). {rehacer}") from None
        except google.auth.exceptions.TransportError:
            raise GmailError("No se pudo conectar con Google para renovar el token.") from None
        token_file.write_text(credenciales.to_json(), encoding="utf-8")
    return credenciales


def cuenta_autorizada(credenciales: Credentials) -> str:
    """Correo de la cuenta que autorizó, leído del id_token que Google entrega con el permiso «openid email»."""
    id_token = getattr(credenciales, "id_token", None)
    if not id_token:
        return ""
    # Viene directo de Google por HTTPS en la misma autorización: basta leerlo, no hace falta otra verificación.
    datos = jwt.decode(id_token, verify=False)
    return str(datos.get("email", "")).strip().lower()


def autorizar(client_file: Path | None, token_file: Path | None, cuenta_esperada: str, flujo=None,
              permiso: Permiso = PERMISO_ENVIAR) -> str:
    """Autorización única: abre el navegador, guarda el token y devuelve la cuenta. Se niega si no es la esperada."""
    if client_file is None or token_file is None:
        raise GmailError(f"Faltan GOOGLE_CLIENT_FILE o {permiso.var_token} en .env.")
    if not cuenta_esperada:
        raise GmailError(f"Falta {permiso.var_cuenta} en .env ({permiso.para_que}).")
    if not client_file.is_file():
        raise GmailError("No se encuentra el archivo de GOOGLE_CLIENT_FILE.")
    if flujo is None:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flujo = InstalledAppFlow.from_client_secrets_file(str(client_file), permiso.scopes)
    aviso = (f"Se abrirá el navegador: entra como {cuenta_esperada} y acepta {permiso.pantalla}.\n"
             "Si no se abre solo, copia esta dirección en el navegador:\n{url}")
    credenciales = flujo.run_local_server(port=0, open_browser=True, login_hint=cuenta_esperada,
                                          authorization_prompt_message=aviso,
                                          success_message="Listo: ya puedes cerrar esta pestaña y volver a la terminal.")
    cuenta = cuenta_autorizada(credenciales)
    if cuenta != cuenta_esperada:
        raise GmailError(f"Autorizaste con {cuenta or 'una cuenta desconocida'}, pero {permiso.var_cuenta} es "
                         f"{cuenta_esperada}. No se guardó nada: repite entrando como {cuenta_esperada}.")
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credenciales.to_json(), encoding="utf-8")
    return cuenta
