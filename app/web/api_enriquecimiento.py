"""Fase 2 · las direcciones con token para el enriquecimiento desde la PC (docs/ENVIO_ENRIQUECIMIENTO.md).

* No usan la sesión del panel: la PC se identifica con `Authorization: Bearer <ENRICH_TOKEN>` (comparación en
  tiempo constante). Sin ENRICH_TOKEN en el servidor, estas direcciones no existen (404). Con un token malo: 401, y
  queda en el registro del servidor (journalctl), sin escribir nada en la base.
* Solo tres cosas, las de app/sources/remoto.py: abrir una corrida (y recibir la cola), mandar la consulta de un
  cartel de esa cola (ficha + archivos) y cerrar la corrida. No leen revisiones, usuarios, perfil ni nada más.
* La consulta llega como multipart: «consulta» (un archivo JSON con la bitácora y la ficha) y un «archivo» por
  cada documento que bajó la PC, con el nombre de SICOP (serverFileNm). Tope del envío: DOCUMENTS_MAX_MB_PER_TENDER.
"""

from __future__ import annotations

import json
import logging
import secrets
from contextlib import closing

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from app.config import Settings, load_settings
from app.database import connect
from app.sources import enriquecimiento as en
from app.sources import remoto
from app.sources.remoto import RemotoError

PREFIJO = "/api/enriquecimiento/"
MAX_CONSULTA = 5 * 1024 * 1024        # el JSON de la consulta: la ficha de SICOP pesa unos cientos de KB
MARGEN = 1024 * 1024                  # cabeceras del multipart y el JSON, además de los archivos
log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enriquecimiento")


def tope_bytes(settings: Settings) -> int:
    """Lo más que puede pesar el envío de un cartel (lo usa también el límite de app/web/carga.py)."""
    return settings.documents_max_mb_per_tender * 1024 * 1024 + MAX_CONSULTA + MARGEN


def _token_valido(request: Request, settings: Settings) -> Response | None:
    """None si la PC trae el token correcto; si no, la respuesta que se le devuelve."""
    if not settings.enrich_token:
        return JSONResponse({"error": "No encontrado."}, status_code=404)
    dado = request.headers.get("authorization", "")
    esperado = f"Bearer {settings.enrich_token}"
    if not secrets.compare_digest(dado.encode(), esperado.encode()):
        log.warning("API de enriquecimiento: token ausente o incorrecto desde %s (%s %s)",
                    request.client.host if request.client else "?", request.method, request.url.path)
        return JSONResponse({"error": "Token ausente o incorrecto."}, status_code=401,
                            headers={"WWW-Authenticate": "Bearer"})
    return None


def _error(exc: RemotoError) -> JSONResponse:
    return JSONResponse({"error": str(exc)}, status_code=exc.estado)


def _con_base(settings: Settings, funcion, *args):
    with closing(connect(settings.database_path)) as conn:
        return funcion(conn, *args)


@router.post("/corridas")
async def abrir(request: Request) -> Response:
    """Borrado al cierre, cola del día y corrida nueva (origen 'remoto')."""
    settings = load_settings()
    if (rechazo := _token_valido(request, settings)) is not None:
        return rechazo
    try:
        datos = await run_in_threadpool(_con_base, settings, remoto.abrir_corrida, settings, en._ahora())
    except (RemotoError, ValueError) as exc:
        return _error(exc if isinstance(exc, RemotoError) else RemotoError(str(exc), 409))
    return JSONResponse(datos, status_code=201)


@router.post("/corridas/{run_id}/consultas")
async def consulta(request: Request, run_id: int) -> Response:
    """La consulta de un cartel de la cola: ficha y archivos. El servidor repite los guardados y reevalúa."""
    settings = load_settings()
    if (rechazo := _token_valido(request, settings)) is not None:
        return rechazo
    form = await request.form(max_files=200, max_fields=10)
    try:
        parte = form.get("consulta")
        if parte is None or isinstance(parte, str):
            raise RemotoError("Falta la parte «consulta» (un archivo JSON).")
        crudo = await parte.read(MAX_CONSULTA + 1)
        if len(crudo) > MAX_CONSULTA:
            raise RemotoError("La parte «consulta» pesa demasiado.", 413)
        try:
            datos = json.loads(crudo)
        except ValueError:
            raise RemotoError("La parte «consulta» no es JSON.") from None
        if not isinstance(datos, dict):
            raise RemotoError("La parte «consulta» tiene que ser un objeto JSON.")
        archivos: dict[str, bytes] = {}
        total, tope = 0, tope_bytes(settings)
        for archivo in form.getlist("archivo"):
            if isinstance(archivo, str) or not archivo.filename:
                raise RemotoError("Cada «archivo» tiene que llevar el nombre de SICOP (serverFileNm).")
            contenido = await archivo.read()
            total += len(contenido)
            if total > tope:
                raise RemotoError(f"El envío pasa del tope de {settings.documents_max_mb_per_tender} MB por "
                                  "cartel.", 413)
            archivos[archivo.filename] = contenido
        resultado = await run_in_threadpool(_con_base, settings, remoto.aplicar_consulta, settings, run_id, datos,
                                            archivos, en._ahora())
    except RemotoError as exc:
        return _error(exc)
    finally:
        await form.close()
    return JSONResponse(resultado, status_code=201)


@router.post("/corridas/{run_id}/cierre")
async def cerrar(request: Request, run_id: int) -> Response:
    """El estado final que dice la PC: ok, con_fallos o detenida (y el motivo, si se detuvo)."""
    settings = load_settings()
    if (rechazo := _token_valido(request, settings)) is not None:
        return rechazo
    try:
        try:
            cuerpo = await request.json()
        except ValueError:
            raise RemotoError("El cuerpo tiene que ser JSON.") from None
        if not isinstance(cuerpo, dict):
            raise RemotoError("El cuerpo tiene que ser un objeto JSON.")
        resultado = await run_in_threadpool(_con_base, settings, remoto.cerrar_corrida, run_id, cuerpo.get("estado"),
                                            cuerpo.get("motivo"), en._ahora())
    except RemotoError as exc:
        return _error(exc)
    return JSONResponse(resultado)
