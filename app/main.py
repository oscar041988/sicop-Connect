"""Aplicación web de SICOP CONNECT (FastAPI)."""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.config import Settings, load_settings
from app.database import check_database
from app.web import carga, seguridad
from app.web.intentos import LimiteIntentos
from app.web.rutas import csrf_invalido, router as panel, sin_permiso

MIN_SECRETO = 32
log = logging.getLogger(__name__)


def _secreto_de_sesion(settings: Settings) -> str:
    secreto = settings.get("SESSION_SECRET")
    if settings.app_env == "development" and not secreto:
        log.warning("SESSION_SECRET vacío: se usa uno temporal; las sesiones se pierden al reiniciar la app.")
        return secrets.token_urlsafe(48)
    if len(secreto) < MIN_SECRETO:
        raise RuntimeError(f"SESSION_SECRET debe tener al menos {MIN_SECRETO} caracteres fuera de development.")
    return secreto


def crear_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    # Sin /docs ni /openapi.json: también mostrarían el panel sin sesión.
    app = FastAPI(title="SICOP CONNECT", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.intentos = LimiteIntentos()  # intentos de login fallidos, en memoria
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static")
    app.include_router(panel)
    app.add_exception_handler(seguridad.CsrfInvalido, csrf_invalido)
    app.add_exception_handler(seguridad.SinPermiso, sin_permiso)
    app.get("/health")(health)
    # El último middleware agregado es el que se ejecuta primero: la sesión se lee, luego se exige,
    # y solo con sesión se revisa el tamaño de una subida.
    app.middleware("http")(carga.limitar_tamano)
    app.middleware("http")(seguridad.exigir_sesion)
    app.add_middleware(SessionMiddleware, secret_key=_secreto_de_sesion(settings), session_cookie="sicop_sesion",
                       max_age=settings.session_max_age, same_site="lax", https_only=settings.cookie_secure)
    return app


def health() -> dict:
    """Estado de la app y de la base. Público: no incluye rutas, usuarios ni secretos."""
    settings = load_settings()
    return {
        "app": "ok",
        "version": __version__,
        "environment": settings.app_env,
        "database": check_database(settings.database_path),
    }


app = crear_app()
