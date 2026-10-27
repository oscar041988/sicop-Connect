"""Configuración de SICOP CONNECT.

Orden de prioridad (de mayor a menor):
1. Variables de entorno del proceso (en el servidor vienen de /etc/sicop-connect/app.env).
2. Archivo .env local (solo en desarrollo; nunca se versiona).
3. Valores por defecto seguros definidos aquí.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

# Valores por defecto: los mismos de .env.example (seguros: sin envíos ni tareas programadas).
# Solo se leen estas claves: una que ya no está (como MAIL_TO, reemplazada por los destinatarios del panel en la
# lección 7) se ignora aunque siga en un .env o app.env viejo.
DEFAULTS: dict[str, str] = {
    "APP_ENV": "development",
    "APP_TIMEZONE": "America/Costa_Rica",
    "DATABASE_PATH": "data/sicop.db",
    "RAW_DATA_DIR": "data/raw",
    "INCOMING_DIR": "data/incoming",
    "SOURCE_MODE": "manual",
    "AI_MODE": "none",
    "NOTIFICATIONS_ENABLED": "false",
    "NOTIFICATIONS_DRY_RUN": "true",
    "SCHEDULER_ENABLED": "false",
    "MAIL_PROVIDER": "unconfigured",
    "MAIL_FROM": "",
    "SESSION_SECRET": "",
    "SESSION_MAX_AGE_HOURS": "8",
    "UPLOAD_MAX_MB": "25",
    "EXPORTS_DIR": "data/exports",
    "APP_BASE_URL": "http://127.0.0.1:8000",
    "NOTIFY_LOOKBACK_DAYS": "7",
    "NOTIFY_CLOSING_DAYS": "3",
    "GOOGLE_CLIENT_FILE": "",
    "GOOGLE_TOKEN_FILE": "",
    "GOOGLE_READ_TOKEN_FILE": "",
    "SICOP_REQUEST_EMAIL": "",
    "OBTAIN_CODE_TIMEOUT_MIN": "10",
    "OBTAIN_LINK_MAX_HOURS": "12",
    "OBTAIN_POLL_MINUTES": "5",
    "OBTAIN_REQUEST_HOUR": "07:00",
    "OBTAIN_DOWNLOAD": "manual",
    "OBTAIN_ALERT_TO": "",
    "BROWSER_HEADLESS": "false",
    "RECORDINGS_DIR": "data/grabaciones",
    "ENRICH_DELAY_SECONDS": "8",
    "DOCUMENTS_DIR": "data/documentos",
    "DOCUMENT_MAX_MB": "50",
    "DOCUMENTS_MAX_MB_PER_TENDER": "100",
    "ENRICH_ENABLED": "false",
    "ENRICH_MAX_PER_DAY": "20",
    "RECORDINGS_KEEP_DAYS": "30",
}

# Variables cuyo valor nunca se muestra (solo si están configuradas o pendientes).
SENSITIVE_KEYS = frozenset({"SESSION_SECRET", "MAIL_FROM", "SICOP_REQUEST_EMAIL", "OBTAIN_ALERT_TO"})


def parse_env_file(path: Path) -> dict[str, str]:
    """Lee un archivo KEY=VALUE sencillo. Ignora líneas vacías y comentarios (#)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


@dataclass(frozen=True)
class Settings:
    raw: Mapping[str, str]
    env_file_loaded: bool

    def get(self, key: str) -> str:
        return self.raw.get(key, "")

    @property
    def app_env(self) -> str:
        return self.get("APP_ENV")

    @property
    def database_path(self) -> Path:
        path = Path(self.get("DATABASE_PATH"))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def raw_data_dir(self) -> Path:
        path = Path(self.get("RAW_DATA_DIR"))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def incoming_dir(self) -> Path:
        path = Path(self.get("INCOMING_DIR"))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def exports_dir(self) -> Path:
        path = Path(self.get("EXPORTS_DIR"))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def app_base_url(self) -> str:
        """Dirección del panel para los enlaces de los avisos, sin «/» final."""
        return self.get("APP_BASE_URL").strip().rstrip("/")

    @property
    def notify_lookback_days(self) -> int:
        """Solo se avisan versiones de carteles vistas en los últimos N días (NOTIFY_LOOKBACK_DAYS; por defecto 7):
        así el primer lote no envía todo el histórico."""
        try:
            dias = int(self.get("NOTIFY_LOOKBACK_DAYS"))
        except ValueError:
            raise ValueError("NOTIFY_LOOKBACK_DAYS debe ser un número entero de días") from None
        if dias <= 0:
            raise ValueError("NOTIFY_LOOKBACK_DAYS debe ser mayor que 0")
        return dias

    @property
    def notify_closing_days(self) -> int:
        """Aviso de cierre próximo: oportunidades marcadas «Interesa» o «Revisar requisitos» que cierran en N días
        o menos (NOTIFY_CLOSING_DAYS; por defecto 3, decisión de Ivania 2026-10-22)."""
        try:
            dias = int(self.get("NOTIFY_CLOSING_DAYS"))
        except ValueError:
            raise ValueError("NOTIFY_CLOSING_DAYS debe ser un número entero de días") from None
        if dias <= 0:
            raise ValueError("NOTIFY_CLOSING_DAYS debe ser mayor que 0")
        return dias

    @property
    def mail_provider(self) -> str:
        return self.get("MAIL_PROVIDER").strip().lower()

    @property
    def mail_from(self) -> str:
        return self.get("MAIL_FROM").strip().lower()

    def _ruta_opcional(self, key: str) -> Path | None:
        valor = self.get(key).strip()
        if not valor:
            return None
        path = Path(valor)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def google_client_file(self) -> Path | None:
        """JSON del cliente OAuth (lo entrega el administrador). Fuera del proyecto; nunca en git."""
        return self._ruta_opcional("GOOGLE_CLIENT_FILE")

    @property
    def google_token_file(self) -> Path | None:
        """Token que guarda python -m app.cli google-auth. Fuera del proyecto; nunca en git."""
        return self._ruta_opcional("GOOGLE_TOKEN_FILE")

    @property
    def google_read_token_file(self) -> Path | None:
        """Token de SOLO LECTURA (gmail.readonly) que guarda python -m app.cli obtain gmail-auth. Aparte del de
        enviar; fuera del proyecto; nunca en git."""
        return self._ruta_opcional("GOOGLE_READ_TOKEN_FILE")

    @property
    def sicop_request_email(self) -> str:
        """Buzón donde llegan los correos de SICOP (código y enlace del reporte)."""
        return self.get("SICOP_REQUEST_EMAIL").strip().lower()

    @property
    def obtain_code_timeout_min(self) -> int:
        """Minutos que obtain request espera el correo con el código de SICOP (OBTAIN_CODE_TIMEOUT_MIN; 10)."""
        try:
            minutos = int(self.get("OBTAIN_CODE_TIMEOUT_MIN"))
        except ValueError:
            raise ValueError("OBTAIN_CODE_TIMEOUT_MIN debe ser un número entero de minutos") from None
        if not 1 <= minutos <= 60:
            raise ValueError("OBTAIN_CODE_TIMEOUT_MIN debe estar entre 1 y 60")
        return minutos

    def _entero(self, key: str, minimo: int, maximo: int, unidad: str) -> int:
        try:
            valor = int(self.get(key))
        except ValueError:
            raise ValueError(f"{key} debe ser un número entero de {unidad}") from None
        if not minimo <= valor <= maximo:
            raise ValueError(f"{key} debe estar entre {minimo} y {maximo}")
        return valor

    @property
    def obtain_link_max_hours(self) -> int:
        """Horas máximas de espera del correo con el enlace (OBTAIN_LINK_MAX_HOURS; 12). Después: fallido."""
        return self._entero("OBTAIN_LINK_MAX_HOURS", 1, 23, "horas")

    @property
    def obtain_poll_minutes(self) -> int:
        """Cada cuántos minutos obtain poll --seguir revisa el buzón (OBTAIN_POLL_MINUTES; 5)."""
        return self._entero("OBTAIN_POLL_MINUTES", 1, 60, "minutos")

    @property
    def source_mode(self) -> str:
        """manual (por defecto): obtain auto no toca SICOP ni Gmail · auto: obtain auto pide, espera e importa."""
        modo = self.get("SOURCE_MODE").strip().lower()
        if modo not in ("manual", "auto"):
            raise ValueError("SOURCE_MODE debe ser manual o auto")
        return modo

    @property
    def obtain_request_hours(self) -> list[time]:
        """Horas a las que obtain auto pide el reporte (OBTAIN_REQUEST_HOUR, HH:MM; una o dos separadas por coma,
        p. ej. 06:30,14:00). Cada hora es un «turno»: una solicitud por turno (dos por día, Oscar, 2026-10-26)."""
        texto = self.get("OBTAIN_REQUEST_HOUR")
        try:
            horas = sorted(datetime.strptime(h.strip(), "%H:%M").time() for h in texto.split(","))
        except ValueError:
            raise ValueError("OBTAIN_REQUEST_HOUR debe ser una o dos horas HH:MM separadas por coma, "
                             "por ejemplo 06:30,14:00") from None
        if len(horas) > 2:
            raise ValueError("OBTAIN_REQUEST_HOUR admite como máximo dos horas (dos solicitudes por día).")
        if len(set(horas)) != len(horas):
            raise ValueError("OBTAIN_REQUEST_HOUR tiene una hora repetida.")
        return horas

    @property
    def obtain_download(self) -> str:
        """manual (por defecto; SICOP bloqueó la descarga hecha por el programa): al llegar el enlace se avisa para
        descargarlo a mano · auto: la app lo descarga (OBTAIN_DOWNLOAD)."""
        modo = self.get("OBTAIN_DOWNLOAD").strip().lower()
        if modo not in ("manual", "auto"):
            raise ValueError("OBTAIN_DOWNLOAD debe ser manual o auto")
        return modo

    @property
    def obtain_alert_to(self) -> str:
        """Buzón que recibe la alerta de FALLO de la obtención automática (OBTAIN_ALERT_TO)."""
        return self.get("OBTAIN_ALERT_TO").strip().lower()

    @property
    def browser_headless(self) -> bool:
        """false (por defecto): la consulta de fichas abre el navegador CON ventana, para que se vea qué consulta
        (BROWSER_HEADLESS; guía de enriquecimiento). En pytest va sin ventana."""
        return _as_bool(self.get("BROWSER_HEADLESS"))

    @property
    def recordings_dir(self) -> Path:
        """Videos y capturas de cada consulta de ficha (RECORDINGS_DIR; data/grabaciones). Fuera de Git."""
        path = Path(self.get("RECORDINGS_DIR"))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def enrich_delay_seconds(self) -> int:
        """Pausa entre una consulta de ficha y la siguiente (ENRICH_DELAY_SECONDS; 8): el portal es de todos."""
        return self._entero("ENRICH_DELAY_SECONDS", 1, 600, "segundos")

    @property
    def documents_dir(self) -> Path:
        """Documentos de las fichas (DOCUMENTS_DIR; data/documentos). Fuera de Git; entran en el respaldo."""
        path = Path(self.get("DOCUMENTS_DIR"))
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def document_max_mb(self) -> int:
        """Tamaño máximo de UN documento de la ficha (DOCUMENT_MAX_MB; 50)."""
        return self._entero("DOCUMENT_MAX_MB", 1, 500, "MB")

    @property
    def documents_max_mb_per_tender(self) -> int:
        """Tope de documentos guardados por cartel (DOCUMENTS_MAX_MB_PER_TENDER; 100; decisión del 2026-10-27)."""
        return self._entero("DOCUMENTS_MAX_MB_PER_TENDER", 1, 5000, "MB")

    @property
    def enrich_enabled(self) -> bool:
        """false (por defecto): enrich run no consulta SICOP. Se activa a mano en .env (lección 4)."""
        return _as_bool(self.get("ENRICH_ENABLED"))

    @property
    def enrich_max_per_day(self) -> int:
        """Máximo de carteles consultados por día con enrich run (ENRICH_MAX_PER_DAY; 20)."""
        return self._entero("ENRICH_MAX_PER_DAY", 1, 200, "carteles")

    @property
    def recordings_keep_days(self) -> int:
        """Días que se guardan los videos y capturas (RECORDINGS_KEEP_DAYS; 30). Los de un FALLO se conservan."""
        return self._entero("RECORDINGS_KEEP_DAYS", 1, 3650, "días")

    @property
    def notifications_enabled(self) -> bool:
        return _as_bool(self.get("NOTIFICATIONS_ENABLED"))

    @property
    def notifications_dry_run(self) -> bool:
        return _as_bool(self.get("NOTIFICATIONS_DRY_RUN"))

    @property
    def scheduler_enabled(self) -> bool:
        return _as_bool(self.get("SCHEDULER_ENABLED"))

    @property
    def session_max_age(self) -> int:
        """Duración de la sesión en segundos (SESSION_MAX_AGE_HOURS; por defecto 8 h)."""
        try:
            horas = float(self.get("SESSION_MAX_AGE_HOURS"))
        except ValueError:
            raise ValueError("SESSION_MAX_AGE_HOURS debe ser un número de horas") from None
        if horas <= 0:
            raise ValueError("SESSION_MAX_AGE_HOURS debe ser mayor que 0")
        return int(horas * 3600)

    @property
    def upload_max_bytes(self) -> int:
        """Tamaño máximo de un archivo subido desde el panel (UPLOAD_MAX_MB; por defecto 25 MB)."""
        try:
            megas = float(self.get("UPLOAD_MAX_MB"))
        except ValueError:
            raise ValueError("UPLOAD_MAX_MB debe ser un número de megabytes") from None
        if megas <= 0:
            raise ValueError("UPLOAD_MAX_MB debe ser mayor que 0")
        return int(megas * 1024 * 1024)

    @property
    def cookie_secure(self) -> bool:
        """Cookie solo por HTTPS en todo entorno que no sea development (el servidor nunca la desactiva)."""
        return self.app_env != "development"


def load_settings(
    env_file: Path | None = DEFAULT_ENV_FILE,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Combina valores por defecto, .env y variables del proceso (estas ganan)."""
    environ = os.environ if environ is None else environ
    file_values = parse_env_file(env_file) if env_file else {}
    merged = dict(DEFAULTS)
    merged.update(file_values)
    merged.update({k: v for k, v in environ.items() if k in DEFAULTS})
    return Settings(raw=merged, env_file_loaded=bool(file_values))
