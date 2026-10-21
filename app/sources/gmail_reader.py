"""Lector de Gmail de SOLO LECTURA (obtención automática, lección 1). Ver docs/DECISION_OBTENCION.md §8.

Busca en el buzón SICOP_REQUEST_EMAIL solo los correos de info@sicop.go.cr con los asuntos «Código verificación
para reporte» y «Envío de reporte», y saca de ellos el código de verificación y el enlace del reporte.

Permiso: gmail.readonly, con un token aparte del de enviar avisos (GOOGLE_READ_TOKEN_FILE). La autorización se hace
una vez con python -m app.cli obtain gmail-auth. Este módulo solo hace GET a la API: no envía, borra, marca ni
mueve correos.

Tres resultados distintos, que no se confunden:
* CorreoNoLlego → todavía no hay correo posterior a la solicitud: se puede esperar.
* FormatoDesconocido → el correo llegó, pero el código o el enlace no tienen la forma conocida: FALLO, revisar.
* GmailError → no se pudo leer el buzón (token, permiso, conexión).

Nunca se escriben el código, el enlace, el id del correo ni su contenido en mensajes o logs: para mostrar algo se
usan enmascarar_codigo() y enmascarar_enlace().
"""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email import message_from_bytes, policy
from email.message import EmailMessage

import google.auth.exceptions
import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

from app.config import Settings
from app.importers.comun import HORA_CR
from app.notifications import gmail
from app.notifications.gmail import GmailError, Permiso

SCOPE_LEER = "https://www.googleapis.com/auth/gmail.readonly"
PERMISO_LEER = Permiso(SCOPE_LEER, "GOOGLE_READ_TOKEN_FILE", "SICOP_REQUEST_EMAIL",
                       "el buzón donde llegan los correos de SICOP", "python -m app.cli obtain gmail-auth",
                       "«Ver tus mensajes de correo» (solo lectura)")
URL_MENSAJES = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
TIMEOUT_S = 30
MAX_CORREOS = 10  # por búsqueda: se pide un reporte por día, así que basta

REMITENTE_SICOP = "info@sicop.go.cr"
ASUNTOS = {"codigo": "Código verificación para reporte", "enlace": "Envío de reporte"}

# Observado el 2026-10-21: «…debe ingresar el siguiente código: <strong>XXXXXX</strong>.» (6 letras y números).
PATRON_CODIGO = re.compile(r"c[óo]digo:\s*<strong>\s*([A-Za-z0-9]{4,12})\s*</strong>", re.IGNORECASE)
# Solo enlaces de descarga de SICOP: un enlace a otro dominio cuenta como formato desconocido.
PATRON_ENLACE = re.compile(
    r'href="(https://www\.sicop\.go\.cr/app/module/bid/public/ext-report-download\?processId=\d+)"')


class CorreoNoLlego(Exception):
    """Todavía no hay correo de SICOP posterior a la solicitud. No es un error del correo: se puede esperar."""


class FormatoDesconocido(Exception):
    """Llegó el correo de SICOP, pero no trae el código o el enlace con la forma conocida. Es un FALLO."""


@dataclass(frozen=True)
class CorreoSicop:
    """Un correo de SICOP ya comprobado. repr no muestra el id ni el valor (podría terminar en un log)."""

    id: str = field(repr=False)
    recibido: datetime  # cuándo lo recibió Gmail (internalDate), en hora de Costa Rica
    tipo: str           # "codigo" o "enlace"
    valor: str | None = field(repr=False)  # el código o el enlace; None si el formato no se reconoce


def enmascarar_codigo(codigo: str) -> str:
    return codigo[:2] + "*" * max(len(codigo) - 2, 2)


def enmascarar_enlace(enlace: str) -> str:
    encontrado = re.search(r"processId=(\d+)", enlace)
    if not encontrado:
        return "enlace ****"
    numero = encontrado.group(1)
    return f"processId={numero[:2]}{'*' * max(len(numero) - 2, 2)}"


def extraer(tipo: str, correo: EmailMessage) -> str | None:
    """El código o el enlace del cuerpo del correo (ya decodificado: quoted-printable, UTF-8), o None."""
    cuerpo = correo.get_body(preferencelist=("html", "plain"))
    if cuerpo is None:
        return None
    try:
        texto = cuerpo.get_content()
    except (LookupError, ValueError, KeyError):
        return None
    encontrado = (PATRON_CODIGO if tipo == "codigo" else PATRON_ENLACE).search(texto)
    if not encontrado:
        return None
    return encontrado.group(1) if tipo == "codigo" else html.unescape(encontrado.group(1))


def _es_de_sicop(correo: EmailMessage, tipo: str) -> bool:
    """Gmail ya filtró con la consulta; aquí se vuelve a comprobar con reglas exactas."""
    try:
        direcciones = correo["From"].addresses if correo["From"] else ()
        asunto = str(correo["Subject"] or "").strip()
    except (AttributeError, ValueError, IndexError):
        return False
    return (len(direcciones) == 1 and direcciones[0].addr_spec.lower() == REMITENTE_SICOP
            and asunto == ASUNTOS[tipo])


class LectorGmail:
    """Lee el buzón con gmail.readonly. Solo GET: no hay ningún método que cambie el buzón."""

    def __init__(self, credenciales: Credentials | None, session: requests.Session | None = None):
        self.session = session or AuthorizedSession(credenciales)

    def _get(self, url: str, params: dict) -> dict:
        try:
            respuesta = self.session.get(url, params=params, timeout=TIMEOUT_S)
        except requests.Timeout:
            raise GmailError(f"Gmail no respondió en {TIMEOUT_S} s.") from None
        except (requests.ConnectionError, google.auth.exceptions.TransportError) as exc:
            raise GmailError(f"No se pudo conectar con Gmail ({type(exc).__name__}).") from None
        if respuesta.status_code == 403:
            raise GmailError("Gmail negó el acceso (HTTP 403): el permiso de lectura o la API de Gmail no están "
                             "activados para el cliente OAuth. Lo revisa el administrador.")
        if respuesta.status_code >= 300:
            raise GmailError(f"Gmail no pudo leer el buzón (HTTP {respuesta.status_code}).")
        try:
            return respuesta.json()
        except ValueError:
            raise GmailError("Gmail respondió algo que no es JSON.") from None

    def _buscar(self, tipo: str, desde: datetime) -> list[CorreoSicop]:
        """Correos de SICOP de ese tipo recibidos desde «desde», del más reciente al más viejo."""
        if desde.tzinfo is None:
            raise ValueError("desde debe llevar zona horaria")
        consulta = f'from:{REMITENTE_SICOP} subject:"{ASUNTOS[tipo]}" after:{int(desde.timestamp())}'
        lista = self._get(URL_MENSAJES, {"q": consulta, "maxResults": MAX_CORREOS})
        correos = []
        for item in lista.get("messages", []):
            datos = self._get(f"{URL_MENSAJES}/{item['id']}", {"format": "raw"})
            try:
                recibido = datetime.fromtimestamp(int(datos["internalDate"]) / 1000, tz=HORA_CR)
                crudo = base64.urlsafe_b64decode(datos["raw"] + "=" * (-len(datos["raw"]) % 4))
            except (KeyError, ValueError, TypeError):
                raise GmailError("Gmail devolvió un correo incompleto (sin fecha o sin contenido).") from None
            if recibido < desde:
                continue
            correo = message_from_bytes(crudo, policy=policy.default)
            if not _es_de_sicop(correo, tipo):
                continue
            correos.append(CorreoSicop(str(item["id"]), recibido, tipo, extraer(tipo, correo)))
        return sorted(correos, key=lambda c: c.recibido, reverse=True)

    def _el_mas_reciente(self, tipo: str, desde: datetime) -> CorreoSicop:
        correos = self._buscar(tipo, desde)
        if not correos:
            raise CorreoNoLlego(f"Todavía no llegó el correo «{ASUNTOS[tipo]}» posterior a {desde:%Y-%m-%d %H:%M}.")
        # Solo vale el más reciente: si no se entiende, no se usa uno anterior (sería un código o enlace viejo).
        if correos[0].valor is None:
            raise FormatoDesconocido(f"Llegó el correo «{ASUNTOS[tipo]}» de las {correos[0].recibido:%H:%M}, pero "
                                     "su formato es desconocido: SICOP pudo cambiar el texto del correo.")
        return correos[0]

    def buscar_codigo(self, desde: datetime) -> CorreoSicop:
        """El código de verificación del correo más reciente posterior a la solicitud («desde»)."""
        return self._el_mas_reciente("codigo", desde)

    def buscar_enlace(self, desde: datetime) -> CorreoSicop:
        """El enlace de descarga del correo «Envío de reporte» más reciente posterior a la solicitud."""
        return self._el_mas_reciente("enlace", desde)

    def listar_recientes(self, dias: int, ahora: datetime | None = None) -> list[CorreoSicop]:
        """Los correos de SICOP de los dos tipos de los últimos «dias» días (diagnóstico: obtain check-mail)."""
        desde = (ahora or datetime.now(HORA_CR)) - timedelta(days=dias)
        correos = self._buscar("codigo", desde) + self._buscar("enlace", desde)
        return sorted(correos, key=lambda c: c.recibido, reverse=True)


def _comprobar_token_aparte(settings: Settings) -> None:
    if settings.google_read_token_file is not None and settings.google_read_token_file == settings.google_token_file:
        raise GmailError("GOOGLE_READ_TOKEN_FILE debe ser otro archivo que GOOGLE_TOKEN_FILE (el token de enviar).")


def crear_lector(settings: Settings) -> LectorGmail:
    _comprobar_token_aparte(settings)
    return LectorGmail(gmail.cargar_credenciales(settings.google_read_token_file, PERMISO_LEER))


def autorizar(settings: Settings, flujo=None) -> str:
    """Autorización única de lectura: se entra como SICOP_REQUEST_EMAIL y se acepta solo «Ver tus mensajes»."""
    _comprobar_token_aparte(settings)
    return gmail.autorizar(settings.google_client_file, settings.google_read_token_file,
                           settings.sicop_request_email, flujo=flujo, permiso=PERMISO_LEER)
