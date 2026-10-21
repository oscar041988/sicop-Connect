"""Configuración de SICOP CONNECT.

Orden de prioridad (de mayor a menor):
1. Variables de entorno del proceso (en el servidor vienen de /etc/sicop-connect/app.env).
2. Archivo .env local (solo en desarrollo; nunca se versiona).
3. Valores por defecto seguros definidos aquí.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
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
    "GOOGLE_CLIENT_FILE": "",
    "GOOGLE_TOKEN_FILE": "",
    "GOOGLE_READ_TOKEN_FILE": "",
    "SICOP_REQUEST_EMAIL": "",
    "OBTAIN_CODE_TIMEOUT_MIN": "10",
    "OBTAIN_LINK_MAX_HOURS": "12",
    "OBTAIN_POLL_MINUTES": "5",
}

# Variables cuyo valor nunca se muestra (solo si están configuradas o pendientes).
SENSITIVE_KEYS = frozenset({"SESSION_SECRET", "MAIL_FROM", "SICOP_REQUEST_EMAIL"})


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
