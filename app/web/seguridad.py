"""Sesión obligatoria y protección CSRF del panel.

- La sesión es una cookie firmada por SessionMiddleware de Starlette (itsdangerous) con SESSION_SECRET.
- CSRF: cada sesión tiene un token aleatorio (secrets); todo formulario POST lo envía en un campo oculto
  y el servidor lo compara con el de la sesión. Sin token o con uno distinto → 403.
- En cada petición se revisa en la base que el usuario siga activo y no haya cambiado su contraseña
  desde que entró; si no, la sesión se cierra (una cookie firmada no se puede «recoger» de otra forma).
  En la misma consulta se lee su nivel (admin o encargado): las páginas de administración usan exigir_admin.
"""

from __future__ import annotations

import hmac
import re
import secrets
import sqlite3
from contextlib import closing
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from app import usuarios
from app.config import load_settings

CAMPO_CSRF = "csrf_token"
RUTAS_PUBLICAS = ("/health", "/login")
PREFIJOS_PUBLICOS = ("/static/",)
# Destino seguro tras el login: una ruta de este sitio («/…»), nunca otro dominio («//otro.com», «/\otro.com»).
DESTINO_LOCAL = re.compile(r"^/(?![/\\])")


class CsrfInvalido(Exception):
    """El formulario llegó sin token CSRF o con uno que no es el de la sesión."""


class SinPermiso(Exception):
    """La página es solo para administradores."""


def csrf_token(request: Request) -> str:
    """Token CSRF de la sesión; se crea la primera vez que una página muestra un formulario."""
    if CAMPO_CSRF not in request.session:
        request.session[CAMPO_CSRF] = secrets.token_urlsafe(32)
    return request.session[CAMPO_CSRF]


async def verificar_csrf(request: Request) -> None:
    """Dependencia de cada ruta POST."""
    enviado = (await request.form()).get(CAMPO_CSRF)
    esperado = request.session.get(CAMPO_CSRF)
    # compare_digest tarda lo mismo acierte o no: no da pistas sobre el token.
    if not isinstance(enviado, str) or not esperado or not hmac.compare_digest(enviado, esperado):
        raise CsrfInvalido()


def usuario_actual(request: Request) -> dict | None:
    return request.session.get("usuario")


def es_admin(request: Request) -> bool:
    usuario = usuario_actual(request)
    return usuario is not None and usuario.get("rol") == usuarios.ADMIN


def exigir_admin(request: Request) -> None:
    """Dependencia de las páginas de administración. El nivel se leyó de la base en esta misma petición."""
    if not es_admin(request):
        raise SinPermiso()


def _nivel_vigente(usuario: dict) -> str | None:
    """Nivel actual del usuario, consultando la base en solo lectura (no la crea si falta).
    None si la sesión ya no vale o la base no se puede abrir."""
    path = load_settings().database_path
    if not path.is_file():
        return None
    try:
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as conn:
            return usuarios.sesion_vigente(conn, usuario.get("id"), usuario.get("huella"))
    except sqlite3.Error:
        return None


def destino_seguro(destino: str) -> str:
    return destino if DESTINO_LOCAL.match(destino) else "/oportunidades"


async def exigir_sesion(request: Request, call_next) -> Response:
    """Middleware: sin sesión, todo (menos /health, /login y /static) redirige al login."""
    ruta = request.url.path
    if ruta in RUTAS_PUBLICAS or ruta.startswith(PREFIJOS_PUBLICOS):
        return await call_next(request)
    usuario = usuario_actual(request)
    if usuario is not None:
        nivel = await run_in_threadpool(_nivel_vigente, usuario)
        if nivel is None:
            # Desactivado o con contraseña nueva desde que entró: la cookie firmada sigue siendo auténtica,
            # pero ya no vale. Se cierra la sesión aquí mismo.
            request.session.clear()
            usuario = None
        elif usuario.get("rol") != nivel:
            # El nivel siempre es el de la base, no el que tenía al entrar: un cambio aplica en el siguiente clic.
            request.session["usuario"] = {**usuario, "rol": nivel}
    if usuario is None:
        destino = ruta + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse("/login?" + urlencode({"siguiente": destino}), status_code=303)
    respuesta = await call_next(request)
    # Al cerrar sesión, el botón «atrás» no debe mostrar una copia guardada de los datos.
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta
