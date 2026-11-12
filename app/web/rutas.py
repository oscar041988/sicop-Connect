"""Rutas del panel: inicio y cierre de sesión, lista de oportunidades, detalle, revisión y carga de archivos;
seguimiento de carteles (gestor de documentos); información y documentos de SICOP (enriquecimiento); para
administradores, usuarios, destinatarios, avisos fallidos o inciertos y la bitácora de consultas con sus videos.

Todas, salvo /login, exigen sesión (middleware en app/web/seguridad.py) y todo POST lleva token CSRF.
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from app.ai import asistente as ia_asistente
from app.ai import chat as ia_chat
from app.ai import cola as ia_cola
from app.ai import expediente as ia_expediente
from app.ai import explicacion as ia_explicacion
from app.ai import reporte as ia_reporte
from app.ai import resumen as ia_resumen
from app.ai import verificacion
from app.ayuda import pagina as ayuda
from app.ayuda import votos as ayuda_votos
from app.cli import EJEMPLOS_POR_ADVERTENCIA, IMPORTADORES, MAX_RECHAZOS_VISIBLES, SEPARADORES
from app.config import load_settings
from app.database import check_database, connect, transaccion
from app.importers import zip_pliegos
from app.importers.comun import HORA_CR, ORIGENES, ImportacionError
from app.matching.evaluar import evaluar_base
from app.matching.reglas import ReglasError, cargar_reglas
from app import (asistente, aviso_encargado, avisos, calidad, competencia, cumplimiento, destinatarios, elegibilidad,
                 expediente_archivos,
                 expediente_descarga, exportar, fichas_panel, historial, oferta_cambios, oferta_economica, panel,
                 perfil, propuesta, reintentos, resumen,
                 seguimiento, usuarios, visor)
from app.historial import Quien
from app.web import carga, citas, seguridad
from app.web.intentos import BLOQUEO
from app.web.seguridad import verificar_csrf

log = logging.getLogger(__name__)


def _contexto_sesion(request: Request) -> dict:
    """Variables de todas las plantillas: el token CSRF de los formularios y quién inició sesión."""
    return {"csrf_token": seguridad.csrf_token(request), "usuario": seguridad.usuario_actual(request)}


ESTATICOS = Path(__file__).parent / "static"


def version_estatico(nombre: str) -> str:
    """Huella corta del archivo: va en la URL (estilo.css?v=…) para que el navegador no use una copia vieja.

    Se calcula en cada página (el CSS pesa pocos KB): así sirve también con --reload, que no vigila el .css.
    """
    return hashlib.sha256((ESTATICOS / nombre).read_bytes()).hexdigest()[:10]


PLANTILLAS = Jinja2Templates(directory=Path(__file__).parent / "templates",  # autoescape activo; no se desactiva
                             context_processors=[_contexto_sesion])
PLANTILLAS.env.filters["fecha"] = panel.fecha_cr
PLANTILLAS.env.filters["legible"] = panel.legible
PLANTILLAS.env.filters["titulo"] = panel.formato_titulo
PLANTILLAS.env.filters["dia"] = perfil.dia
PLANTILLAS.env.globals["monto"] = panel.monto
PLANTILLAS.env.globals.update(
    ENCAJES=panel.ENCAJES, PLAZOS=panel.PLAZOS, CALIDADES=panel.CALIDADES, DECISIONES=panel.DECISIONES,
    MOTIVOS=panel.MOTIVOS, NOMBRES_FAMILIA=panel.NOMBRES_FAMILIA, resaltar=panel.resaltar,
    falta_para_seguimiento=panel.falta_para_seguimiento, nombre_competidor=competencia.nombre_competidor,
    es_persona_fisica=competencia.es_persona_fisica, version_estatico=version_estatico,
    termino=ayuda.termino, ayuda_para=ayuda.ayuda_para,
)
SOLO_DIGITOS = re.compile(r"^[0-9]+$")

router = APIRouter()


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _base_no_lista(request: Request) -> HTMLResponse | None:
    estado = check_database(load_settings().database_path)
    if estado["status"] == "ok":
        return None
    return PLANTILLAS.TemplateResponse(request, "error.html", {"mensaje": estado["detail"]}, status_code=503)


def _aviso_reglas(version: str | None, sin_evaluar: bool = False) -> str | None:
    if version is None:
        return "Todavía no hay evaluaciones: ejecuta python -m app.cli evaluate."
    try:
        actual = cargar_reglas().version
    except (ReglasError, OSError, ValueError) as exc:
        return f"No se pudo leer config/hermatix_rules.yaml: {exc}"
    if actual != version:
        return (f"Las reglas cambiaron (YAML {actual}; se muestra la evaluación {version}). "
                "Ejecuta python -m app.cli evaluate para actualizar.")
    if sin_evaluar:
        return ("Hay datos importados después de la última evaluación: los carteles nuevos o cambiados todavía "
                "no aparecen aquí. Ejecuta python -m app.cli evaluate para actualizar.")
    return None


def csrf_invalido(request: Request, exc: seguridad.CsrfInvalido) -> Response:
    return PLANTILLAS.TemplateResponse(request, "error.html", {
        "mensaje": "El formulario no es válido o venció. Recarga la página e inténtalo de nuevo."}, status_code=403)


@router.get("/login", response_class=HTMLResponse)
def login(request: Request, siguiente: str = "/oportunidades") -> Response:
    if seguridad.usuario_actual(request) is not None:
        return RedirectResponse(seguridad.destino_seguro(siguiente), status_code=303)
    return PLANTILLAS.TemplateResponse(request, "login.html", {"siguiente": siguiente})


@router.post("/login", response_class=HTMLResponse, dependencies=[Depends(verificar_csrf)])
def iniciar_sesion(request: Request, email: str = Form(""), contrasena: str = Form(""),
                   siguiente: str = Form("/oportunidades")) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    intentos = request.app.state.intentos
    ip = request.client.host if request.client else "desconocida"
    clave = intentos.clave(email[:254], ip)
    # Bloqueado: no se revisa la contraseña, ni siquiera la correcta; si no, el bloqueo no frenaría nada.
    if segundos := intentos.segundos_de_bloqueo(clave):
        return _login_bloqueado(request, siguiente, email, segundos)
    with closing(connect(load_settings().database_path)) as conn:
        usuario = usuarios.autenticar(conn, email, contrasena)
    if usuario is None:
        # El correo va entre comillas (%r) para que un salto de línea no fabrique líneas falsas en el log.
        log.warning("Login fallido para %r desde %s", email[:254], ip)
        if intentos.registrar_fallo(clave):
            log.warning("Login bloqueado %d min para %r desde %s", BLOQUEO // 60, email[:254], ip)
            return _login_bloqueado(request, siguiente, email, BLOQUEO)
        # Mismo mensaje si falla el correo o la contraseña: no se revela qué correos tienen cuenta.
        return PLANTILLAS.TemplateResponse(request, "login.html", {
            "siguiente": siguiente, "email": email, "error": "Correo o contraseña incorrectos."}, status_code=401)
    intentos.registrar_exito(clave)
    request.session.clear()  # sesión nueva (y token CSRF nuevo) al entrar
    request.session["usuario"] = {"id": usuario[0], "nombre": usuario[1], "huella": usuario[2]}
    return RedirectResponse(seguridad.destino_seguro(siguiente), status_code=303)


def _login_bloqueado(request: Request, siguiente: str, email: str, segundos: int) -> Response:
    minutos = -(-segundos // 60)  # redondeo hacia arriba: «1 minuto» aunque falten 20 segundos
    error = f"Demasiados intentos. Espera {minutos} minuto{'s' if minutos != 1 else ''} e inténtalo de nuevo."
    return PLANTILLAS.TemplateResponse(request, "login.html", {
        "siguiente": siguiente, "email": email, "error": error}, status_code=429)


@router.post("/logout", dependencies=[Depends(verificar_csrf)])
def cerrar_sesion(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/", include_in_schema=False)
def inicio() -> RedirectResponse:
    return RedirectResponse("/oportunidades", status_code=307)


@router.get("/oportunidades", response_class=HTMLResponse)
def oportunidades(request: Request, prioridad: str = "candidatos", familia: str = "", institucion: str = "",
                  plazo: str = "", revisado: str = "", tipo: str = "", q: str = "", pagina: int = 1) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    filtros = panel.Filtros(prioridad, familia, institucion, plazo, revisado, tipo, q, pagina).limpios()
    ahora = _ahora()
    with closing(connect(load_settings().database_path)) as conn:
        version = panel.version_vigente(conn)
        resultado = panel.listar(conn, version, filtros, ahora) if version else panel.Pagina([], 0, 1, 1)
        opciones = panel.opciones_filtros(conn, version) if version else {"familias": [], "instituciones": [], "tipos": []}
        sin_evaluar = panel.importado_sin_evaluar(conn)
        seguimientos = seguimiento.de_carteles(conn, [f.nro_sicop for f in resultado.filas])
    consulta = {k: v for k, v in vars(filtros).items() if k != "pagina" and v and v != "candidatos"}
    return PLANTILLAS.TemplateResponse(request, "oportunidades.html", {
        "filtros": filtros, "pagina": resultado, "opciones": opciones, "version": version,
        "seguimientos": seguimientos,
        "aviso": _aviso_reglas(version, sin_evaluar), "prioridades": panel.PRIORIDADES,
        "regresiva": lambda cierre: panel.cuenta_regresiva(cierre, ahora),
        "url_chip": lambda valor: "/oportunidades?" + urlencode(
            {k: v for k, v in {**consulta, "revisado": valor}.items() if v}),
        "url_pagina": lambda n: "/oportunidades?" + urlencode({**consulta, "pagina": n}),
        "url_exportar": "/oportunidades.xlsx" + ("?" + urlencode(consulta) if consulta else ""),
    })


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/oportunidades.xlsx")
def exportar_oportunidades(request: Request, prioridad: str = "candidatos", familia: str = "", institucion: str = "",
                           plazo: str = "", revisado: str = "", tipo: str = "", q: str = "") -> Response:
    """A5: el listado con los mismos filtros que la pantalla, en Excel (todas las páginas)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    filtros = panel.Filtros(prioridad, familia, institucion, plazo, revisado, tipo, q, 1).limpios()
    ahora = _ahora()
    with closing(connect(load_settings().database_path)) as conn:
        version = panel.version_vigente(conn)
        if version is None:
            return PLANTILLAS.TemplateResponse(request, "error.html", {
                "mensaje": "Todavía no hay evaluaciones: no hay nada que exportar."}, status_code=409)
        contenido, filas = exportar.libro(conn, version, filtros, ahora, load_settings().app_base_url)
    log.info("Exportación a Excel: %s filas · usuario %s", filas, (seguridad.usuario_actual(request) or {}).get("id"))
    nombre = f"oportunidades_{ahora.astimezone(HORA_CR):%Y%m%d-%H%M}.xlsx"
    return Response(contenido, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def _render_detalle(request: Request, conn: sqlite3.Connection, nro_sicop: str, error: str | None = None,
                    formulario: dict[str, str] | None = None, status_code: int = 200, ver_item: int | None = None,
                    **asistente_extra) -> Response:
    version = panel.version_vigente(conn)
    ahora = _ahora()
    datos = panel.detalle(conn, nro_sicop, version, ahora)
    if datos is None:
        return PLANTILLAS.TemplateResponse(
            request, "error.html", {"mensaje": f"No hay un cartel con Número SICOP {nro_sicop}."}, status_code=404)
    seg = seguimiento.estado(conn, nro_sicop)
    puede = seguimiento.puede_entrar(seguridad.usuario_actual(request), seg)
    ia_visible = _ia_encendida()
    resumenes = ia_resumen.del_cartel(conn, nro_sicop) if ia_visible else []
    asistente_activo = _asistente_encendido()
    return PLANTILLAS.TemplateResponse(request, "oportunidad.html", {
        "d": datos, "version": version, "aviso": _aviso_reglas(version, panel.importado_sin_evaluar(conn)), "error": error,
        "seg": seg, "puede_entrar": puede, "error_oferta": request.session.pop("error_oferta", None),
        "regresiva": panel.cuenta_regresiva(datos.compra.fecha_cierre_recepcion, ahora),
        "formulario": formulario or {},
        # Enriquecimiento (lección 4, entrega 4B): la ficha más reciente de SICOP y sus documentos.
        "sicop": fichas_panel.informacion(conn, nro_sicop), "documentos": fichas_panel.documentos(conn, nro_sicop),
        "retiro": fichas_panel.retiro(conn, nro_sicop), "TEXTO_DOC": fichas_panel.TEXTO,
        "ESTADO_DOC": fichas_panel.ESTADOS,
        # Reporte con IA (lección 5): la fila del resumen («Ver» y «Descargar»). Con AI_MODE=none no se muestra.
        "ia_visible": ia_visible, "resumenes": resumenes, "IA": _TEXTOS_IA,
        # Asistente de elegibilidad (lección 3): solo para quien entra al expediente (seguimiento.puede_entrar).
        # Con ASSISTANT_ENABLED=false (lección 5) no se muestra ni se calcula nada del asistente.
        "asistente_activo": asistente_activo,
        **(_contexto_asistente(request, conn, nro_sicop, ahora, ver_item, **asistente_extra)
           if asistente_activo and seg and puede else {}),
    }, status_code=status_code)


_TEXTOS_IA = {"recomendaciones": ia_resumen.RECOMENDACIONES, "estados": ia_resumen.ESTADOS, "NO": ia_resumen.NO}


def _ia_encendida() -> bool:
    try:
        return load_settings().ia_activa
    except ValueError:   # AI_MODE mal escrito: el panel sigue funcionando, sin el bloque de la IA
        return False


def _asistente_encendido() -> bool:
    """ASSISTANT_ENABLED (asistente, lección 5): apagado, el asistente y su lista no se ven ni responden."""
    try:
        return load_settings().assistant_enabled
    except ValueError:
        return False


_RUTA_ASISTENTE = re.compile(r"^/oportunidades/\d+/(asistente|verificacion)(/|$)")


async def cerrar_asistente_apagado(request: Request, call_next) -> Response:
    """Middleware: con ASSISTANT_ENABLED=false, todas las direcciones del asistente y de su lista dan «no
    encontrado» (un solo lugar en vez de una condición en cada ruta). No borra nada."""
    if _RUTA_ASISTENTE.match(request.url.path) and not await run_in_threadpool(_asistente_encendido):
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": "El asistente de elegibilidad está apagado (ASSISTANT_ENABLED=false)."}, status_code=404)
    return await call_next(request)


@router.get("/oportunidades/{nro_sicop}/resumen", response_class=HTMLResponse)
def ver_resumen(request: Request, nro_sicop: str, imprimir: bool = False) -> Response:
    """El resumen con IA del cartel como documento («Ver»). Con ?imprimir=1 («Descargar») abre la ventana de imprimir
    del navegador, que lo guarda como PDF (decisión de Ivania, 2026-10-30: sin librerías nuevas)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        datos = panel.detalle(conn, nro_sicop, panel.version_vigente(conn), _ahora()) \
            if SOLO_DIGITOS.match(nro_sicop) else None
        vigente = next((r for r in ia_resumen.del_cartel(conn, nro_sicop) if r.datos), None) \
            if datos is not None and _ia_encendida() else None
        if vigente is None:
            return _no_encontrado(request, f"El cartel {nro_sicop} todavía no tiene resumen.")
        # DOC n → documento, solo si el expediente sigue siendo el que leyó el modelo (si no, citas sin enlace).
        actual = ia_expediente.armar_expediente(conn, nro_sicop, load_settings().ia_max_input_tokens)
        numerados = ia_expediente.numeracion(conn, nro_sicop) \
            if actual is not None and actual.huella == vigente.huella else None
        sicop = fichas_panel.informacion(conn, nro_sicop)
        # «¿Cumple?» (2026-11-05): requerimientos según el asistente; «Qué piden», lo que marca el encargado.
        seg = seguimiento.estado(conn, nro_sicop)
        est_reqs = cumplimiento.de_requerimientos(conn, nro_sicop, _ahora().astimezone(HORA_CR).date())
        est_lineas = cumplimiento.de_lineas(conn, nro_sicop)
    return PLANTILLAS.TemplateResponse(request, "resumen.html", {
        "d": datos, "res": vigente, "sicop": sicop, "IA": _TEXTOS_IA, "imprimir": imprimir,
        "citas_enlazadas": numerados is not None, "citar": lambda texto: citas.enlazar(texto, nro_sicop, numerados),
        "cumple_req": lambda q: cumplimiento.requerimiento(est_reqs, q),
        "cumple_linea": lambda i: cumplimiento.linea(est_reqs, est_lineas, i), "clave_linea": cumplimiento.clave_linea,
        "ESTADOS_LINEA": cumplimiento.ESTADOS_LINEA, "con_asistente": bool(est_reqs), "seg": seg,
        "asistente_activo": _asistente_encendido(),
        "puede_marcar": seg is not None and seguimiento.puede_entrar(seguridad.usuario_actual(request), seg),
        "hecho": request.session.pop("hecho_cumple", None), "error": request.session.pop("error_cumple", None),
    })


@router.post("/oportunidades/{nro_sicop}/resumen/cumple", dependencies=[Depends(verificar_csrf)])
def marcar_cumple(request: Request, nro_sicop: str, clave: str = Form(""), estado: str = Form(""),
                  nota: str = Form("")) -> Response:
    """«¿Cumple?» de una fila de «Qué piden»: la marca el encargado del cartel o un administrador (la regla del
    expediente). Nunca borra la marca anterior: vale la última."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        if (prohibido := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return prohibido
        vigente = next((r for r in ia_resumen.del_cartel(conn, nro_sicop) if r.datos), None)
        if vigente is None:
            return _no_encontrado(request, f"El cartel {nro_sicop} todavía no tiene resumen.")
        try:
            cumplimiento.marcar(conn, nro_sicop, vigente.datos, clave, estado, nota, _quien(request), _ahora())
            request.session["hecho_cumple"] = f"Guardado: {cumplimiento.ESTADOS_LINEA[estado]}."
        except cumplimiento.MarcaInvalida as exc:
            request.session["error_cumple"] = str(exc)
    return RedirectResponse(f"/oportunidades/{nro_sicop}/resumen#que-piden", status_code=303)


@router.get("/oportunidades/{nro_sicop}/reporte")
def descargar_reporte(request: Request, nro_sicop: str) -> Response:
    """Reporte de cartel Hermatix en PDF, máximo 3 páginas (Reporte con IA, lección 4). Lo genera si el resumen
    cambió desde el último; si no, entrega el último. Nunca borra los anteriores."""
    if (error := _base_no_lista(request)) is not None:
        return error
    if not SOLO_DIGITOS.match(nro_sicop):
        return _no_encontrado(request, "El Número SICOP solo lleva dígitos.")
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        try:
            r = ia_reporte.generar(conn, settings, nro_sicop, _quien(request), _ahora())
        except ia_reporte.ReporteError as exc:
            return _no_encontrado(request, str(exc))
    return FileResponse(r.ruta, media_type="application/pdf", filename=r.ruta.name)


# --- Oferta completa con un botón (Oscar, por Ivania, 2026-11-10; DECISION_PROPUESTA.md §12) -------------------------
# Como la oferta de NAVSAT: portada, pliego respondido sección por sección, listado de anexos, oferta económica y los
# documentos del asistente adjuntos (app/propuesta.py). Sin formulario: los precios salen de config/tarifario.yaml y lo
# que falta sale en rojo. La ven quienes entran al expediente (su encargado y los administradores): trae precios.
# La app formula el PDF; una persona lo revisa, lo firma con firma digital y lo sube a SICOP.

# La misma oferta sale también en Word (.docx) con «formato=docx» (Oscar, por Ivania, 2026-11-11; DECISION_IA.md
# §10.6 bis): mismo contenido, otro formato (app/propuesta_word.py).
TIPOS_OFERTA = {"pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@router.post("/oportunidades/{nro_sicop}/oferta", dependencies=[Depends(verificar_csrf)])
async def generar_oferta(request: Request, nro_sicop: str) -> Response:
    """Arma la oferta completa y la entrega en PDF (o en Word con formato=docx); guarda una copia en
    EXPORTS_DIR/ofertas/ (nunca sobrescribe)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    formulario = await request.form()
    formato = str(formulario.get("formato") or "pdf")
    if formato not in TIPOS_OFERTA:
        formato = "pdf"
    version = str(formulario.get("version") or "")          # una versión anterior (paso 4); vacío = la última
    desde_asistente = formulario.get("desde") == "asistente"   # si falla, el error se ve donde se pidió
    return await run_in_threadpool(_generar_oferta, request, nro_sicop, formato,
                                   int(version) if version.isdigit() else None, desde_asistente)


def _generar_oferta(request: Request, nro_sicop: str, formato: str = "pdf", version: int | None = None,
                    desde_asistente: bool = False) -> Response:
    settings = load_settings()
    ahora = datetime.now(HORA_CR)
    with closing(connect(settings.database_path)) as conn:
        if (negado := _expediente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        armar = propuesta.armar_word if formato == "docx" else propuesta.armar
        try:
            armada = armar(conn, settings, nro_sicop, _quien(request), ahora, version=version)
        except propuesta.PropuestaError as exc:
            request.session["error_oferta"] = str(exc)
            destino = f"/oportunidades/{nro_sicop}/asistente#oferta" if desde_asistente else f"/oportunidades/{nro_sicop}"
            return RedirectResponse(destino, status_code=303)
    oferta_economica.guardar(armada.contenido, settings.exports_dir, armada.procedimiento, ahora, prefijo="oferta",
                             extension=f".{formato}")
    nombre = f"oferta_{nro_sicop}_{ahora:%Y%m%d-%H%M%S}.{formato}"
    return Response(armada.contenido, media_type=TIPOS_OFERTA[formato],
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@router.get("/oportunidades/{nro_sicop}", response_class=HTMLResponse)
def oportunidad(request: Request, nro_sicop: str, pregunta: int | None = None) -> Response:
    """El detalle del cartel. ?pregunta=<requisito> muestra esa pregunta del asistente («Cambiar» una respuesta)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_detalle(request, conn, nro_sicop, ver_item=pregunta)


@router.post("/oportunidades/{nro_sicop}/revision", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def revisar(request: Request, nro_sicop: str, decision: str = Form(""), motivo: str = Form(""),
            comentario: str = Form("")) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    # El responsable sale de la sesión, nunca del formulario: nadie puede firmar a nombre de otro.
    user_id = seguridad.usuario_actual(request)["id"]
    with closing(connect(load_settings().database_path)) as conn:
        try:
            if not SOLO_DIGITOS.match(nro_sicop):
                raise panel.RevisionInvalida("El Número SICOP solo lleva dígitos.")
            panel.guardar_revision(conn, nro_sicop, decision, motivo, comentario, user_id, _ahora())
        except panel.RevisionInvalida as exc:
            formulario = {"decision": decision, "motivo": motivo, "comentario": comentario}
            return _render_detalle(request, conn, nro_sicop, str(exc), formulario, status_code=400)
    # Post/Redirect/Get: recargar la página no vuelve a enviar el formulario.
    return RedirectResponse(f"/oportunidades/{nro_sicop}#revisiones", status_code=303)


@router.post("/oportunidades/{nro_sicop}/seguimiento", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def dar_seguimiento(request: Request, nro_sicop: str) -> Response:
    """Gestor de documentos (paso 1A): cualquier usuario pone el cartel en seguimiento, sin encargado."""
    if (error := _base_no_lista(request)) is not None:
        return error
    if not SOLO_DIGITOS.match(nro_sicop):
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": "El Número SICOP solo lleva dígitos."}, status_code=404)
    with closing(connect(load_settings().database_path)) as conn:
        if (falta := panel.falta_para_seguimiento(panel.decision_vigente(conn, nro_sicop))) is not None:
            return _render_detalle(request, conn, nro_sicop, falta, status_code=400)
        try:
            seguimiento.abrir(conn, nro_sicop, _quien(request), _ahora())
        except seguimiento.SeguimientoInvalido as exc:
            return _render_detalle(request, conn, nro_sicop, str(exc), status_code=400)
    return RedirectResponse(f"/oportunidades/{nro_sicop}#asistente", status_code=303)


# --- Asistente de elegibilidad (lección 3): para quien entra al expediente ------------------------------------------
# Desde el 2026-11-12 (pedido de Ivania) tiene su propia página, con el diseño de la maqueta del chat: la ficha del
# cartel arriba, el asistente a la izquierda y el avance, los archivos y la oferta a la derecha. El detalle del cartel
# solo muestra el botón «Abrir el asistente».

@router.get("/oportunidades/{nro_sicop}/asistente", response_class=HTMLResponse)
def pagina_asistente(request: Request, nro_sicop: str, pregunta: int | None = None) -> Response:
    """La página del asistente. ?pregunta=<requisito> muestra esa pregunta («Cambiar» una respuesta)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_asistente(request, conn, nro_sicop, ver_item=pregunta)


def _render_asistente(request: Request, conn: sqlite3.Connection, nro_sicop: str, status_code: int = 200,
                      ver_item: int | None = None, **asistente_extra) -> Response:
    if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
        return negado
    ahora = _ahora()
    datos = panel.detalle(conn, nro_sicop, panel.version_vigente(conn), ahora)
    if datos is None:
        return _no_encontrado(request, f"No hay un cartel con Número SICOP {nro_sicop}.")
    return PLANTILLAS.TemplateResponse(request, "asistente.html", {
        "d": datos, "seg": seguimiento.estado(conn, nro_sicop), "puede_entrar": True, "asistente_activo": True,
        "regresiva": panel.cuenta_regresiva(datos.compra.fecha_cierre_recepcion, ahora),
        "error_oferta": request.session.pop("error_oferta", None),
        **_contexto_asistente(request, conn, nro_sicop, ahora, ver_item, **asistente_extra),
    }, status_code=status_code)


def _citador(conn, nro_sicop: str, settings):
    """[DOC n] → documento, solo si el expediente sigue siendo el que leyó la IA de la lista (si no, sin enlace)."""
    generacion = verificacion.ultima_generacion(conn, nro_sicop)
    actual = ia_expediente.armar_expediente(conn, nro_sicop, settings.ia_max_input_tokens) if generacion else None
    numerados = ia_expediente.numeracion(conn, nro_sicop) \
        if generacion and actual is not None and actual.huella == generacion.huella else None
    return lambda texto: citas.enlazar(texto, nro_sicop, numerados)


def _contexto_asistente(request: Request, conn, nro_sicop: str, ahora: datetime, ver_item: int | None,
                        error_asistente: str | None = None, formulario_asistente: dict | None = None) -> dict:
    settings = load_settings()
    if asistente.sesion(conn, nro_sicop):
        verificacion.sincronizar_filas(conn, nro_sicop)       # «Qué piden» de un resumen nuevo (no escribe si no cambió)
    pasos = asistente.recorrido(conn, nro_sicop, ahora.astimezone(HORA_CR).date())
    sesion = asistente.sesion(conn, nro_sicop)
    # Revisión rápida (decisión de Oscar, 2026-11-04): mientras no se amplíe, solo se preguntan los excluyentes.
    # «Cambiar» abre cualquier requisito ya respondido; la pregunta siguiente sale solo de los visibles.
    visibles = asistente.visibles(pasos, sesion)
    actual = next((p for p in pasos if p.item.id == ver_item), None) or asistente.siguiente(visibles)
    # Resultado (lección 4): cómo va cada requisito con las respuestas de hoy y las constancias ya calculadas.
    evaluaciones = elegibilidad.evaluar(pasos, elegibilidad.cierre_de(conn, nro_sicop),
                                        elegibilidad.revisiones(conn, sesion.id)) if sesion else []
    return {
        "res_eleg": {"evaluaciones": evaluaciones, "global": elegibilidad.resultado_global(evaluaciones),
                     "constancias": elegibilidad.constancias(conn, nro_sicop) if sesion else [],
                     "conteo": {k: sum(e.estado == k for e in evaluaciones) for k in elegibilidad.ESTADOS},
                     "rapido": elegibilidad.resultado_rapido(evaluaciones), "RAPIDOS": elegibilidad.RAPIDOS},
        "ELEG": {"resultados": elegibilidad.RESULTADOS, "estados": elegibilidad.ESTADOS, "aviso": elegibilidad.AVISO},
        "asis": {"sesion": sesion, "pasos": pasos, "actual": actual,
                 "ampliada": asistente.ampliada(pasos, sesion), "visibles": visibles,
                 "avance": asistente.avance(visibles), "info": asistente.informativos(conn, nro_sicop),
                 "es_admin": seguridad.es_admin(request), "limite_mb": settings.assistant_doc_max_mb,
                 "ia": _ia_encendida(), "faltan_ia": sum(p.origen == "app" for p in pasos),
                 "error": error_asistente, "formulario": formulario_asistente or {},
                 "hecho": request.session.pop("hecho_asistente", None)},
        "EVIDENCIAS": verificacion.EVIDENCIAS, "citar": _citador(conn, nro_sicop, settings),
        "chat": _contexto_chat(conn, settings, pasos, sesion, actual, ahora),
    }


def _chat_encendido(settings) -> bool:
    """ASSISTANT_CHAT=true y la IA encendida (DECISION_IA.md §10): si no, el asistente pregunta uno por uno."""
    try:
        return settings.assistant_chat and settings.ia_activa
    except ValueError:   # AI_MODE mal escrito: sin chat
        return False


def _contexto_chat(conn, settings, pasos, sesion, actual, ahora: datetime) -> dict:
    if not _chat_encendido(settings) or sesion is None:
        return {"activo": False}
    lista = ia_chat.mensajes(conn, sesion.id)
    return {"activo": True, "mensajes": lista,
            "presentacion": None if lista else ia_chat.presentacion(pasos, sesion),
            "listo": ia_chat.listo(pasos, sesion),
            # El dato del perfil de la pregunta de ahora se confirma con un clic, como siempre (no va a la IA).
            "perfil": actual if actual is not None and actual.perfil is not None and actual.respuesta is None else None,
            "gasto": ia_cola.costo_de_hoy(conn, ahora.astimezone(HORA_CR).date()), "tope": settings.ia_max_daily_cost,
            "lee_archivos": settings.assistant_send_documents, "limite_mb": settings.assistant_doc_max_mb,
            # Paso 4: los cambios que propuso la IA (con «Aplicar» y «No») y las versiones de la oferta.
            "propuestas": {p.mensaje_id: p for p in oferta_cambios.propuestas(conn, sesion.nro_sicop)},
            "versiones": oferta_cambios.versiones(conn, sesion.nro_sicop)}


# Paso 4 (DECISION_IA.md §10): un cambio a la oferta se aplica solo con el clic de una persona (Ivania, 2026-11-11).

@router.post("/oportunidades/{nro_sicop}/asistente/propuestas/{propuesta_id}/aplicar", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def aplicar_propuesta(request: Request, nro_sicop: str, propuesta_id: int) -> Response:
    return _decidir_propuesta(request, nro_sicop, propuesta_id, True)


@router.post("/oportunidades/{nro_sicop}/asistente/propuestas/{propuesta_id}/rechazar", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def rechazar_propuesta(request: Request, nro_sicop: str, propuesta_id: int) -> Response:
    return _decidir_propuesta(request, nro_sicop, propuesta_id, False)


def _decidir_propuesta(request: Request, nro_sicop: str, propuesta_id: int, aplicar: bool) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            base = propuesta.preparar(conn, settings, nro_sicop, _quien(request), _ahora(), con_cambios=False)
            nueva = oferta_cambios.decidir(conn, nro_sicop, propuesta_id, aplicar, base.bloques, base.anexos,
                                           _quien(request), _ahora())
        except (oferta_cambios.CambioInvalido, propuesta.PropuestaError) as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
        p = next(x for x in oferta_cambios.propuestas(conn, nro_sicop) if x.id == propuesta_id)
        ia_chat.anotar(conn, nro_sicop, f"Aplicado · versión {nueva.numero}: {p.descripcion}" if nueva
                       else f"No aplicado: {p.descripcion}", _ahora())
    return RedirectResponse(f"/oportunidades/{nro_sicop}/asistente#chat", status_code=303)


def _asistente_permitido(request: Request, conn, nro_sicop: str) -> Response | None:
    """None si la persona puede usar el asistente del cartel (la regla del expediente); si no, la página del error."""
    actual = seguimiento.estado(conn, nro_sicop) if SOLO_DIGITOS.match(nro_sicop) else None
    if actual is None:
        return _no_encontrado(request, f"El cartel {nro_sicop} no está en seguimiento: primero «Dar seguimiento».")
    if not seguimiento.puede_entrar(seguridad.usuario_actual(request), actual):
        de = actual.encargado or "su encargado (todavía sin asignar)"
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": f"El asistente de este cartel lo usan {de} y los administradores."}, status_code=403)
    return None


def _volver_asistente(request: Request, nro_sicop: str, mensaje: str) -> Response:
    request.session["hecho_asistente"] = mensaje
    return RedirectResponse(f"/oportunidades/{nro_sicop}/asistente#asistente", status_code=303)


def _redactar_mensaje(r) -> str:
    if r.motivo is None:
        return f"{r.redactadas} preguntas redactadas con IA." if r.redactadas else "Todas las preguntas ya estaban."
    return f"{r.redactadas} preguntas redactadas con IA; {r.motivo}." if r.redactadas else f"Sin IA: {r.motivo}."


@router.post("/oportunidades/{nro_sicop}/asistente/empezar", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def empezar_asistente(request: Request, nro_sicop: str) -> Response:
    """Abre la conversación (o la retoma) y pide a la IA las preguntas, una vez por cartel. Si el cartel todavía no
    tiene lista de verificación, primero la genera con IA (pedido de Ivania, 2026-11-09: sin la página aparte)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            if not verificacion.listar(conn, nro_sicop):
                verificacion.generar(conn, settings, nro_sicop, _quien(request))
        except verificacion.VerificacionError as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
        try:
            asistente.empezar(conn, nro_sicop, _quien(request), _ahora())
        except asistente.AsistenteInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
        r = ia_asistente.redactar(conn, settings, nro_sicop, _quien(request), _ahora())
    return _volver_asistente(request, nro_sicop, f"Asistente listo. {_redactar_mensaje(r)}")


# --- El asistente como chat (DECISION_IA.md §10; ASSISTANT_CHAT) -----------------------------------------------------
# La IA lee el mensaje y propone las respuestas; la app las guarda con las reglas de siempre (app/ai/chat.py).

@router.post("/oportunidades/{nro_sicop}/asistente/chat", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def chat_asistente(request: Request, nro_sicop: str, mensaje: str = Form(""),
                   archivo: UploadFile | None = File(None)) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        if not _chat_encendido(settings):
            return _render_asistente(request, conn, nro_sicop, status_code=400,
                                   error_asistente="El chat está apagado (ASSISTANT_CHAT=false o la IA apagada).")
        subido = None
        if archivo is not None and archivo.filename:
            limite = settings.assistant_doc_max_mb * 1024 * 1024
            datos = archivo.file.read(limite + 1)
            if len(datos) > limite:
                return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=(
                    f"El archivo pasa de {settings.assistant_doc_max_mb} MB (ASSISTANT_DOC_MAX_MB): no se guardó."))
            subido = (datos, archivo.filename)
        try:
            ia_chat.enviar(conn, settings, nro_sicop, mensaje, subido, _quien(request), _ahora())
        except ia_chat.ChatInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
    return RedirectResponse(f"/oportunidades/{nro_sicop}/asistente#chat", status_code=303)


@router.post("/oportunidades/{nro_sicop}/asistente/redactar", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def redactar_asistente(request: Request, nro_sicop: str) -> Response:
    """Pide a la IA las preguntas que faltan (requisitos agregados o corregidos después de empezar)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            r = ia_asistente.redactar(conn, settings, nro_sicop, _quien(request), _ahora())
        except asistente.AsistenteInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
    return _volver_asistente(request, nro_sicop, _redactar_mensaje(r))


@router.post("/oportunidades/{nro_sicop}/asistente/{item_id}/responder", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def responder_asistente(request: Request, nro_sicop: str, item_id: int, estado: str = Form("respondido"),
                        valor_texto: str = Form(""), valor_numero: str = Form(""), valor_fecha: str = Form(""),
                        valor_si_no: str = Form(""), vence_el: str = Form(""), nota: str = Form(""),
                        guardar_en_perfil: str = Form(""), archivo: UploadFile | None = File(None)) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    entrada = asistente.Entrada(estado, valor_texto, valor_numero, valor_fecha, valor_si_no, vence_el, nota)
    guardar = guardar_en_perfil == "1"
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            if guardar and not seguridad.es_admin(request):
                raise asistente.AsistenteInvalido("Guardar en el perfil es solo para administradores.")
            asistente.responder(conn, settings, nro_sicop, item_id, entrada, _subido(archivo), _quien(request),
                                _ahora(), guardar_en_perfil=guardar)
        except (asistente.AsistenteInvalido, expediente_archivos.ArchivoInvalido) as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=_estado_error(exc), ver_item=item_id,
                                   error_asistente=str(exc), formulario_asistente=entrada.__dict__)
    return _volver_asistente(request, nro_sicop,
                             "Respuesta guardada." + (" También quedó en el perfil." if guardar else ""))


@router.post("/oportunidades/{nro_sicop}/asistente/{item_id}/perfil", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def confirmar_perfil_asistente(request: Request, nro_sicop: str, item_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            asistente.confirmar_perfil(conn, nro_sicop, item_id, _quien(request), _ahora())
        except asistente.AsistenteInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, ver_item=item_id,
                                   error_asistente=str(exc))
    return _volver_asistente(request, nro_sicop, "Dato del perfil confirmado.")


@router.post("/oportunidades/{nro_sicop}/asistente/ampliar", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def ampliar_asistente(request: Request, nro_sicop: str) -> Response:
    """«Seguir con los demás requisitos»: después de la revisión rápida (solo excluyentes), abre el resto."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            asistente.ampliar(conn, nro_sicop, _quien(request), _ahora())
        except asistente.AsistenteInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
    return _volver_asistente(request, nro_sicop, "Listo: ahora el asistente pregunta también los demás requisitos.")


# --- Resultado de elegibilidad (lección 4): la app compara, una persona decide los «revisar» --------------------

def _volver_resultado(request: Request, nro_sicop: str, mensaje: str) -> Response:
    request.session["hecho_asistente"] = mensaje
    return RedirectResponse(f"/oportunidades/{nro_sicop}/asistente#resultado", status_code=303)


@router.post("/oportunidades/{nro_sicop}/asistente/{item_id}/revisar", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def revisar_requisito(request: Request, nro_sicop: str, item_id: int, cumple: str = Form(""),
                      nota: str = Form("")) -> Response:
    """Una persona decide un requisito que la app no puede comparar sola (queda atado a su respuesta)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            if cumple not in ("1", "0"):
                raise elegibilidad.ResultadoInvalido("Elige «Cumple» o «No cumple».")
            elegibilidad.revisar(conn, nro_sicop, item_id, cumple == "1", nota, _quien(request), _ahora())
        except elegibilidad.ResultadoInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
    return _volver_resultado(request, nro_sicop, "Revisión guardada. Calcula el resultado para dejar la constancia.")


@router.post("/oportunidades/{nro_sicop}/asistente/resultado", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf)])
def calcular_resultado(request: Request, nro_sicop: str) -> Response:
    """Calcula el resultado con las respuestas de hoy (la app), lo explica (la IA, si se puede) y guarda la
    constancia."""
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        try:
            constancia_id = ia_explicacion.calcular(conn, settings, nro_sicop, _quien(request), _ahora())
        except elegibilidad.ResultadoInvalido as exc:
            return _render_asistente(request, conn, nro_sicop, status_code=400, error_asistente=str(exc))
        c = elegibilidad.constancia(conn, nro_sicop, constancia_id)
    sin_ia = f" Explicación de la app: {c.explicacion_motivo}." if c.explicacion_motivo else ""
    return _volver_resultado(request, nro_sicop, f"Resultado calculado: {c.resultado_texto}.{sin_ia}")


@router.get("/oportunidades/{nro_sicop}/asistente/resultados/{constancia_id}", response_class=HTMLResponse)
def ver_constancia(request: Request, nro_sicop: str, constancia_id: int, imprimir: bool = False) -> Response:
    """La constancia como documento («Ver»); con ?imprimir=1 («Descargar») el navegador la guarda como PDF."""
    return _pagina_constancia(request, nro_sicop, constancia_id, imprimir)


@router.get("/oportunidades/{nro_sicop}/asistente/resultados/{constancia_id}/explicacion", response_class=HTMLResponse)
def ver_explicacion(request: Request, nro_sicop: str, constancia_id: int) -> Response:
    """«Ver explicación» (Ivania, 05/11): la misma constancia, solo con el resultado, la explicación y lo que falta."""
    return _pagina_constancia(request, nro_sicop, constancia_id, False, solo_explicacion=True)


def _pagina_constancia(request: Request, nro_sicop: str, constancia_id: int, imprimir: bool,
                       solo_explicacion: bool = False) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        c = elegibilidad.constancia(conn, nro_sicop, constancia_id)
        if c is None:
            return _no_encontrado(request, "Esa constancia no es de este cartel.")
        datos = panel.detalle(conn, nro_sicop, panel.version_vigente(conn), _ahora())
        citar = _citador(conn, nro_sicop, load_settings())
    return PLANTILLAS.TemplateResponse(request, "resultado.html", {
        "d": datos, "k": c, "imprimir": imprimir, "citar": citar, "solo_explicacion": solo_explicacion,
        "ELEG": {"resultados": elegibilidad.RESULTADOS, "estados": elegibilidad.ESTADOS, "aviso": elegibilidad.AVISO},
    })


def _documento_asistente(request: Request, nro_sicop: str, respuesta_id: int, accion: str):
    """(ruta, Respuesta) del archivo, con el acceso ya registrado; o la página del error."""
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _asistente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        hallado = asistente.documento(conn, settings.assistant_docs_dir, nro_sicop, respuesta_id)
        if hallado is None:
            return _no_encontrado(request, "Ese archivo no está en las respuestas del asistente.")
        asistente.registrar_acceso(conn, _quien(request), accion, nro_sicop, hallado[1])
    return hallado


@router.get("/oportunidades/{nro_sicop}/asistente/respuestas/{respuesta_id}/archivo")
def descargar_documento_asistente(request: Request, nro_sicop: str, respuesta_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _documento_asistente(request, nro_sicop, respuesta_id, "descargar_documento_asistente")
    if isinstance(hallado, Response):
        return hallado
    ruta, r = hallado
    return _archivo(ruta, r.archivo_nombre, perfil.MIME[r.archivo_extension])


@router.get("/oportunidades/{nro_sicop}/asistente/respuestas/{respuesta_id}/ver")
def ver_documento_asistente(request: Request, nro_sicop: str, respuesta_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _documento_asistente(request, nro_sicop, respuesta_id, "ver_documento_asistente")
    if isinstance(hallado, Response):
        return hallado
    ruta, r = hallado
    return _archivo(ruta, r.archivo_nombre, perfil.MIME[r.archivo_extension], en_linea=True)


@dataclass
class ParteCarga:
    """Lo que se muestra de cada CSV importado: uno si se subió un CSV, dos si fue el ZIP de pliegos."""
    nombre: str
    reporte: str
    resultado: object
    anterior: tuple | None


def _importar_parte(conn, reporte: str, ruta: Path, nombre: str, origen: str, raw_dir: Path) -> ParteCarga:
    resultado = IMPORTADORES[reporte](conn, ruta, origen, raw_dir)
    # Qué fue la importación anterior del mismo archivo, para que el aviso no se preste a confusión.
    anterior = conn.execute("SELECT report, file_name, imported_at FROM imports WHERE id = ?",
                            (resultado.ya_importado,)).fetchone() if resultado.ya_importado else None
    return ParteCarga(nombre, reporte, resultado, anterior)


def _importar_zip_pliegos(conn, ruta: Path, nombre: str, origen: str, raw_dir: Path
                          ) -> tuple[list[ParteCarga], str | None]:
    """Carteles y después líneas. Si las líneas fallan, los carteles ya importados se muestran igual."""
    partes: list[ParteCarga] = []
    with tempfile.TemporaryDirectory() as temporal:
        for reporte, csv in zip_pliegos.extraer(ruta, Path(temporal)):
            try:
                partes.append(_importar_parte(conn, reporte, csv, f"{nombre} › {csv.name}", origen, raw_dir))
            except ImportacionError as exc:
                return partes, f"No se importó {csv.name}: {exc}"
    return partes, None


def _render_carga(request: Request, status_code: int = 200, **contexto) -> Response:
    settings = load_settings()
    return PLANTILLAS.TemplateResponse(request, "cargar.html", {
        "seccion": "cargar", "reportes": list(carga.EXTENSIONES), "origenes": ORIGENES, "extensiones": carga.EXTENSIONES,
        "limite_mb": carga.en_megas(settings.upload_max_bytes), "separadores": SEPARADORES,
        "max_rechazos": MAX_RECHAZOS_VISIBLES, "ejemplos": EJEMPLOS_POR_ADVERTENCIA,
        # «real» ya elegido: es el origen del trabajo diario (decisión de Ivania, 2026-10-26).
        "formulario": {"origen": "real"}, "url_sicop": carga.URL_SICOP,
        "url_gmail": carga.enlace_gmail(settings.sicop_request_email), "automatico": settings.source_mode == "auto",
        "correo_8": settings.scheduler_enabled,  # el ciclo de las 8:00 manda los avisos (servidor)
        **contexto,
    }, status_code=status_code)


@router.get("/cargar", response_class=HTMLResponse)
def formulario_carga(request: Request) -> Response:
    return _render_carga(request)


@router.post("/cargar", response_class=HTMLResponse, dependencies=[Depends(verificar_csrf)])
def cargar(request: Request, reporte: str = Form(""), origen: str = Form(""),
           archivo: UploadFile | None = File(None)) -> Response:
    formulario = {"reporte": reporte, "origen": origen}
    if reporte not in carga.EXTENSIONES or origen not in ORIGENES:
        return _render_carga(request, 400, formulario=formulario,
                             error="Elige el tipo de reporte y el origen de los datos.")
    if archivo is None or not archivo.filename:
        return _render_carga(request, 400, formulario=formulario, error="Elige un archivo.")
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    try:
        ruta = carga.guardar_subida(archivo.file, archivo.filename, reporte, settings.incoming_dir,
                                    settings.upload_max_bytes)
    except carga.CargaInvalida as exc:
        status = 413 if isinstance(exc, carga.ArchivoMuyGrande) else 400
        return _render_carga(request, status, formulario=formulario, error=str(exc))
    error = None
    try:
        with closing(connect(settings.database_path)) as conn:
            if reporte == carga.PLIEGOS:
                partes, error = _importar_zip_pliegos(conn, ruta, archivo.filename, origen, settings.raw_data_dir)
            else:
                partes = [_importar_parte(conn, reporte, ruta, archivo.filename, origen, settings.raw_data_dir)]
    except (ImportacionError, zip_pliegos.ZipInvalido) as exc:
        partes, error = [], f"No se importó: {exc}"
    if error or all(p.resultado.ya_importado is not None for p in partes):
        # Con error, o repetido (el original ya está guardado desde la primera vez): no queda en la carpeta de entrada.
        ruta.unlink(missing_ok=True)
    evaluacion = error_evaluacion = None
    if any(p.resultado.ya_importado is None for p in partes):  # entró algo nuevo (aunque otra parte fallara)
        evaluacion, error_evaluacion = _evaluar_tras_cargar(settings)
    # Sin Post/Redirect/Get: el detalle de los rechazos no se guarda en la base. Si se recarga la página y se
    # reenvía el archivo, el hash lo reconoce y no se importa dos veces.
    return _render_carga(request, 400 if error else 200, formulario=formulario, partes=partes, error=error,
                         evaluacion=evaluacion, error_evaluacion=error_evaluacion)


def _evaluar_tras_cargar(settings) -> tuple[dict | None, str | None]:
    """Evalúa toda la base apenas se sube un archivo (Ivania, 2026-10-26): los carteles nuevos se ven en el panel
    sin correr evaluate. No manda correos: los avisos salen con el ciclo de las 8:00. Con la base real tarda
    unos 15 s. Devuelve (resumen, None) o (None, motivo) si no se pudo."""
    try:
        reglas = cargar_reglas()
        with closing(connect(settings.database_path)) as conn:
            r = evaluar_base(conn, reglas, _ahora())
    except ReglasError as exc:
        return None, f"Se importó, pero no se pudo evaluar: {exc}. Avisa a una administradora."
    contar = lambda encaje: sum(c.get(encaje, 0) for c in r.por_encaje.values())  # noqa: E731
    return {"carteles": r.carteles, "alta": contar("alta"), "media": contar("media")}, None


# --- Competencia (todos los usuarios con sesión) ---------------------------------------------------------------

def _competidores() -> tuple[dict[str, str], str | None]:
    """Los nombres de config/competidores.yaml; si el archivo está mal, la página igual se ve (con cédulas)."""
    try:
        return competencia.cargar_competidores(), None
    except (competencia.CompetidoresError, OSError) as exc:
        return {}, f"{exc}. Mientras tanto, los ganadores se muestran por cédula."


@router.get("/competencia", response_class=HTMLResponse)
def pagina_competencia(request: Request, desde: str = "", hasta: str = "", prioridad: str = "") -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    filtro = competencia.Filtro.desde_texto(desde, hasta, prioridad)
    nombres, error_yaml = _competidores()
    with closing(connect(load_settings().database_path)) as conn:
        version = panel.version_vigente(conn)
        hay_adjudicaciones = conn.execute("SELECT 1 FROM adjudicaciones LIMIT 1").fetchone() is not None
        datos = competencia.resumen(conn, version, filtro, nombres) if version and hay_adjudicaciones else None
    return PLANTILLAS.TemplateResponse(request, "competencia.html", {
        "seccion": "competencia", "filtro": filtro, "r": datos, "version": version, "error": error_yaml,
        "aviso": _aviso_reglas(version), "hay_adjudicaciones": hay_adjudicaciones,
        "prioridades": competencia.PRIORIDADES,
        "url_registros": lambda familia, clave: "/competencia/registros?" + urlencode(
            {**filtro.consulta(), "familia": familia, "competidor": clave}),
    })


@router.get("/competencia/registros", response_class=HTMLResponse)
def registros_competencia(request: Request, familia: str = "", competidor: str = "", desde: str = "",
                          hasta: str = "", prioridad: str = "") -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    filtro = competencia.Filtro.desde_texto(desde, hasta, prioridad)
    nombres, error_yaml = _competidores()
    with closing(connect(load_settings().database_path)) as conn:
        version = panel.version_vigente(conn)
        carteles = competencia.registros(conn, version, filtro, nombres, familia, competidor) if version else []
    return PLANTILLAS.TemplateResponse(request, "competencia_registros.html", {
        "seccion": "competencia", "filtro": filtro, "familia": familia, "competidor": competidor,
        "carteles": carteles, "version": version, "error": error_yaml,
        "volver": "/competencia" + ("?" + urlencode(filtro.consulta()) if filtro.consulta() else ""),
    })


# --- Seguimiento: gestor de documentos, paso 1A ----------------------------------------------------------------
# La lista la ve cualquier usuario; cada expediente, solo su encargado y los administradores (seguimiento.puede_entrar).
# El nivel del usuario de la sesión es el que el middleware leyó de la base en esta misma petición.

@router.get("/seguimiento", response_class=HTMLResponse)
def pagina_seguimiento(request: Request) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    ahora = _ahora()
    usuario = seguridad.usuario_actual(request)
    with closing(connect(load_settings().database_path)) as conn:
        filas = seguimiento.listar(conn)
    return PLANTILLAS.TemplateResponse(request, "seguimiento.html", {
        "seccion": "seguimiento", "filas": filas,
        "puede_entrar": lambda estado: seguimiento.puede_entrar(usuario, estado),
        "regresiva": lambda cierre: panel.cuenta_regresiva(cierre, ahora),
    })


def _render_expediente(request: Request, conn, nro_sicop: str, status_code: int = 200, **contexto) -> Response:
    ahora = _ahora()
    actual = seguimiento.estado(conn, nro_sicop) if SOLO_DIGITOS.match(nro_sicop) else None
    if actual is None:
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": f"El cartel {nro_sicop} no está en seguimiento."}, status_code=404)
    if not seguimiento.puede_entrar(seguridad.usuario_actual(request), actual):
        de = actual.encargado or "su encargado (todavía sin asignar)"
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": f"Este expediente es de {de} y de los administradores."}, status_code=403)
    datos = panel.detalle(conn, nro_sicop, panel.version_vigente(conn), ahora)
    return PLANTILLAS.TemplateResponse(request, "expediente.html", {
        "seccion": "seguimiento", "seg": actual, "d": datos, "asignaciones": seguimiento.historial_de(conn, nro_sicop),
        "etapas": seguimiento.etapas_de(conn, nro_sicop), "ETAPAS": seguimiento.ETAPAS,
        "notas": seguimiento.notas_de(conn, nro_sicop), "NOTA_MAX": seguimiento.NOTA_MAX,
        "archivos": expediente_archivos.listar(conn, nro_sicop), "TIPOS_ARCHIVO": expediente_archivos.TIPOS,
        "limite_archivo_mb": load_settings().expediente_max_mb,
        "asignables": seguimiento.asignables(conn) if seguridad.es_admin(request) else [],
        "regresiva": panel.cuenta_regresiva(datos.compra.fecha_cierre_recepcion, ahora),
        "hecho": request.session.pop("hecho", None), "hecho_etapa": request.session.pop("hecho_etapa", None),
        "hecho_archivo": request.session.pop("hecho_archivo", None),
        "hecho_nota": request.session.pop("hecho_nota", None),
        **contexto,
    }, status_code=status_code)


@router.get("/seguimiento/{nro_sicop}", response_class=HTMLResponse)
def expediente(request: Request, nro_sicop: str) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_expediente(request, conn, nro_sicop)


@router.post("/seguimiento/{nro_sicop}/encargado", response_class=HTMLResponse,
             dependencies=[Depends(verificar_csrf), Depends(seguridad.exigir_admin)])
def asignar_encargado(request: Request, nro_sicop: str, encargado: str = Form("")) -> Response:
    """Solo un administrador asigna o cambia el encargado (decisión de Oscar, 2026-10-26)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            if not SOLO_DIGITOS.match(encargado):
                raise seguimiento.SeguimientoInvalido("Elige un encargado de la lista.")
            cambio = seguimiento.asignar(conn, nro_sicop, int(encargado), _quien(request), _ahora())
        except seguimiento.SeguimientoInvalido as exc:
            return _render_expediente(request, conn, nro_sicop, 400, error=str(exc))
    if not cambio:
        request.session["hecho"] = "No se cambió nada: ya era el encargado."
    elif int(encargado) == _quien(request).user_id:
        request.session["hecho"] = "Encargado asignado."
    else:
        request.session["hecho"] = "Encargado asignado. Le llegará un correo con el ciclo diario de las 8:00."
    return RedirectResponse(f"/seguimiento/{nro_sicop}", status_code=303)


@router.post("/seguimiento/{nro_sicop}/etapa", response_class=HTMLResponse, dependencies=[Depends(verificar_csrf)])
def cambiar_etapa(request: Request, nro_sicop: str, etapa: str = Form("")) -> Response:
    """Paso 5: la etapa la cambian quienes entran al expediente (su encargado y los administradores)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        actual = seguimiento.estado(conn, nro_sicop) if SOLO_DIGITOS.match(nro_sicop) else None
        if actual is None or not seguimiento.puede_entrar(seguridad.usuario_actual(request), actual):
            return _render_expediente(request, conn, nro_sicop)  # el mismo 404 o 403 que al abrirlo
        try:
            cambio = seguimiento.cambiar_etapa(conn, nro_sicop, etapa, _quien(request), _ahora())
        except seguimiento.SeguimientoInvalido as exc:
            return _render_expediente(request, conn, nro_sicop, 400, error_etapa=str(exc))
    request.session["hecho_etapa"] = (f"Etapa: {seguimiento.ETAPAS[etapa]}." if cambio
                                      else "No se cambió nada: ya estaba en esa etapa.")
    return RedirectResponse(f"/seguimiento/{nro_sicop}#etapa", status_code=303)


@router.post("/seguimiento/{nro_sicop}/notas", response_class=HTMLResponse, dependencies=[Depends(verificar_csrf)])
def escribir_nota(request: Request, nro_sicop: str, texto: str = Form("")) -> Response:
    """Paso 3: las notas las escriben quienes entran al expediente (su encargado y los administradores)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        actual = seguimiento.estado(conn, nro_sicop) if SOLO_DIGITOS.match(nro_sicop) else None
        if actual is None or not seguimiento.puede_entrar(seguridad.usuario_actual(request), actual):
            return _render_expediente(request, conn, nro_sicop)  # el mismo 404 o 403 que al abrirlo
        try:
            seguimiento.escribir_nota(conn, nro_sicop, texto, _quien(request), _ahora())
        except seguimiento.SeguimientoInvalido as exc:
            # El texto vuelve al formulario para no perderlo.
            return _render_expediente(request, conn, nro_sicop, 400, error_nota=str(exc), texto_nota=texto)
    request.session["hecho_nota"] = "Nota guardada."
    return RedirectResponse(f"/seguimiento/{nro_sicop}#notas", status_code=303)


# --- Archivos del expediente: gestor de documentos, paso 2 ---------------------------------------------------
# Suben, bajan y ven los archivos quienes entran al expediente (seguimiento.puede_entrar), en cada petición.

def _expediente_permitido(request: Request, conn, nro_sicop: str) -> Response | None:
    """None si la persona puede entrar al expediente; si no, el mismo 404 o 403 que al abrirlo."""
    actual = seguimiento.estado(conn, nro_sicop) if SOLO_DIGITOS.match(nro_sicop) else None
    if actual is None or not seguimiento.puede_entrar(seguridad.usuario_actual(request), actual):
        return _render_expediente(request, conn, nro_sicop)
    return None


@router.post("/seguimiento/{nro_sicop}/archivos", response_class=HTMLResponse, dependencies=[Depends(verificar_csrf)])
def subir_archivo(request: Request, nro_sicop: str, archivo: UploadFile | None = File(None)) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _expediente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        if archivo is None or not archivo.filename:
            return _render_expediente(request, conn, nro_sicop, 400, error_archivo="Elige un archivo.")
        try:
            guardado = expediente_archivos.guardar(conn, settings.expedientes_dir, nro_sicop, archivo.file,
                                                   archivo.filename, settings.expediente_max_mb * 1024 * 1024,
                                                   _quien(request), _ahora())
        except expediente_archivos.ArchivoInvalido as exc:
            status = 413 if isinstance(exc, expediente_archivos.ArchivoMuyGrande) else                 409 if isinstance(exc, expediente_archivos.YaEsta) else 400
            return _render_expediente(request, conn, nro_sicop, status, error_archivo=str(exc))
    request.session["hecho_archivo"] = f"Archivo subido: {guardado.nombre}."
    return RedirectResponse(f"/seguimiento/{nro_sicop}#archivos", status_code=303)


def _archivo_del_expediente(request: Request, nro_sicop: str, archivo_id: int):
    """(ruta, Archivo, settings) si la persona puede entrar y el archivo es de ese expediente; si no, la página."""
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _expediente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        hallado = expediente_archivos.obtener(conn, settings.expedientes_dir, nro_sicop, archivo_id)
    if hallado is None:
        return _no_encontrado(request, "Ese archivo no está en el expediente.")
    log.info("Archivo %s del expediente %s · usuario %s", archivo_id, nro_sicop,
             (seguridad.usuario_actual(request) or {}).get("id"))
    return (*hallado, settings)


def _volver_expediente(nro_sicop: str) -> tuple[str, str]:
    return f"/seguimiento/{nro_sicop}#archivos", f"Expediente {nro_sicop}"


@router.get("/seguimiento/{nro_sicop}/archivos/{archivo_id}")
def descargar_archivo(request: Request, nro_sicop: str, archivo_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _archivo_del_expediente(request, nro_sicop, archivo_id)
    if isinstance(hallado, Response):
        return hallado
    ruta, archivo, _ = hallado
    return _archivo(ruta, archivo.nombre, expediente_archivos.MIME[archivo.extension])


@router.get("/seguimiento/{nro_sicop}/archivos/{archivo_id}/ver")
def ver_archivo(request: Request, nro_sicop: str, archivo_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _archivo_del_expediente(request, nro_sicop, archivo_id)
    if isinstance(hallado, Response):
        return hallado
    ruta, archivo, _ = hallado
    return _ver(request, ruta, archivo.nombre, archivo.vista, f"/seguimiento/{nro_sicop}/archivos/{archivo_id}",
                _volver_expediente(nro_sicop))


@router.get("/seguimiento/{nro_sicop}/archivos/{archivo_id}/ver/{indice}")
def ver_dentro_del_archivo(request: Request, nro_sicop: str, archivo_id: int, indice: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _archivo_del_expediente(request, nro_sicop, archivo_id)
    if isinstance(hallado, Response):
        return hallado
    ruta, archivo, settings = hallado
    if archivo.vista != "zip":
        return _no_encontrado(request, "Ese archivo no es un ZIP.")
    return _ver_dentro(request, ruta, archivo.nombre, indice, settings.document_max_mb * 1024 * 1024,
                       f"/seguimiento/{nro_sicop}/archivos/{archivo_id}", _volver_expediente(nro_sicop))


@router.get("/seguimiento/{nro_sicop}/descargar")
def descargar_expediente(request: Request, nro_sicop: str) -> Response:
    """Paso 4: todo el expediente en un ZIP (archivos, notas e historial), para el traspaso."""
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    ahora = _ahora()
    with closing(connect(settings.database_path)) as conn:
        if (negado := _expediente_permitido(request, conn, nro_sicop)) is not None:
            return negado
        # Se arma en un archivo temporal (no en memoria: puede pesar varias veces EXPEDIENTE_MAX_MB) que se borra
        # al terminar de enviarlo.
        temporal = tempfile.NamedTemporaryFile(prefix="expediente-", suffix=".zip", delete=False)
        try:
            with temporal:
                expediente_descarga.armar(conn, settings.expedientes_dir, nro_sicop, temporal, _quien(request), ahora)
        except BaseException:
            Path(temporal.name).unlink(missing_ok=True)
            raise
    respuesta = _archivo(Path(temporal.name), expediente_descarga.nombre_zip(nro_sicop, ahora), "application/zip")
    respuesta.background = BackgroundTask(Path(temporal.name).unlink, missing_ok=True)
    return respuesta


# --- Calidad de las reglas (solo administradores) -------------------------------------------------------------

@router.get("/calidad", response_class=HTMLResponse, dependencies=[Depends(seguridad.exigir_admin)])
def pagina_calidad(request: Request) -> Response:
    """A3: la medición con las reglas actuales del YAML (no se guarda; la guarda score-rules) y el historial."""
    if (error := _base_no_lista(request)) is not None:
        return error
    try:
        reglas = cargar_reglas()
    except (ReglasError, OSError, ValueError) as exc:
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": f"No se pudo leer config/hermatix_rules.yaml: {exc}"}, status_code=500)
    with closing(connect(load_settings().database_path)) as conn:
        medicion = calidad.medir(reglas, conn)
        anteriores = calidad.historial(conn)
    return PLANTILLAS.TemplateResponse(request, "calidad.html", {
        "seccion": "calidad", "m": medicion, "historial": anteriores, "TOTAL": calidad.TOTAL,
    })


# --- Usuarios (solo administradores) -------------------------------------------------------------------------

SOLO_ADMIN = [Depends(verificar_csrf), Depends(seguridad.exigir_admin)]


def sin_permiso(request: Request, exc: seguridad.SinPermiso) -> Response:
    return PLANTILLAS.TemplateResponse(request, "error.html", {
        "mensaje": "Esta página es solo para administradores."}, status_code=403)


def _quien(request: Request) -> Quien:
    usuario = seguridad.usuario_actual(request)
    return Quien(usuario["id"], usuario["nombre"])


def _render_usuarios(request: Request, conn, status_code: int = 200, **contexto) -> Response:
    return PLANTILLAS.TemplateResponse(request, "usuarios.html", {
        "seccion": "usuarios", "usuarios": usuarios.listar(conn),
        "historial": historial.ultimos(conn, historial.DE_USUARIOS),
        "niveles": usuarios.NIVELES, "acciones": historial.ACCIONES, "min_contrasena": usuarios.MIN_CONTRASENA,
        "consejo": usuarios.CONSEJO_CONTRASENA,
        "hecho": request.session.pop("hecho", None), "formulario": {}, **contexto,
    }, status_code=status_code)


def _cambio_de_usuario(request: Request, cambio, hecho: str, formulario: dict | None = None) -> Response:
    """Aplica un cambio; si sale bien, Post/Redirect/Get con un mensaje; si no, la página con el error (400)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            mensaje = cambio(conn) or hecho
        except usuarios.UsuarioInvalido as exc:
            return _render_usuarios(request, conn, 400, error=str(exc), formulario=formulario or {})
    request.session["hecho"] = mensaje
    return RedirectResponse("/usuarios", status_code=303)


@router.get("/usuarios", response_class=HTMLResponse, dependencies=[Depends(seguridad.exigir_admin)])
def pagina_usuarios(request: Request) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_usuarios(request, conn)


@router.post("/usuarios", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def crear_usuario(request: Request, email: str = Form(""), nombre: str = Form(""), rol: str = Form(""),
                  contrasena: str = Form(""), repetir: str = Form("")) -> Response:
    def cambio(conn):
        if contrasena != repetir:
            raise usuarios.UsuarioInvalido("Las contraseñas no coinciden.")
        usuarios.crear_usuario(conn, email, nombre, contrasena, rol, _quien(request))
    # Las contraseñas nunca vuelven al formulario, ni siquiera si hay un error.
    return _cambio_de_usuario(request, cambio, f"Usuario creado: {email.strip()}.",
                              {"email": email, "nombre": nombre, "rol": rol})


@router.post("/usuarios/{user_id}/nivel", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def cambiar_nivel(request: Request, user_id: int, rol: str = Form("")) -> Response:
    def cambio(conn):
        if not usuarios.cambiar_nivel(conn, user_id, rol, _quien(request)):
            return "No se cambió nada: ya tenía ese nivel."
    return _cambio_de_usuario(request, cambio, "Nivel cambiado.")


@router.post("/usuarios/{user_id}/estado", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def cambiar_estado(request: Request, user_id: int, activo: str = Form("")) -> Response:
    def cambio(conn):
        if activo not in ("0", "1"):
            raise usuarios.UsuarioInvalido("Estado no válido.")
        if not usuarios.cambiar_estado(conn, user_id, activo == "1", _quien(request)):
            return "No se cambió nada: ya estaba así."
    return _cambio_de_usuario(request, cambio,
                              "Usuario activado." if activo == "1" else
                              "Usuario desactivado: su sesión abierta se cerró y sus revisiones se conservan.")


@router.post("/usuarios/{user_id}/eliminar", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def eliminar_usuario(request: Request, user_id: int, confirmar: str = Form("")) -> Response:
    def cambio(conn):
        if confirmar != "si":
            raise usuarios.UsuarioInvalido("Para eliminar, marca la casilla «Entiendo que no se puede deshacer».")
        nombre = usuarios.eliminar(conn, user_id, _quien(request))
        return (f"{nombre} fue eliminado: ya no puede entrar y su sesión abierta se cerró. Sus revisiones y su "
                "historial se conservan.")
    return _cambio_de_usuario(request, cambio, "Usuario eliminado.")


@router.post("/usuarios/{user_id}/contrasena", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def cambiar_contrasena(request: Request, user_id: int, contrasena: str = Form(""), repetir: str = Form("")) -> Response:
    def cambio(conn):
        if contrasena != repetir:
            raise usuarios.UsuarioInvalido("Las contraseñas no coinciden.")
        nueva_huella = usuarios.cambiar_contrasena(conn, user_id, contrasena, _quien(request))
        if user_id == seguridad.usuario_actual(request)["id"]:
            # Su propia contraseña: la sesión se actualiza para que no la cierre el siguiente clic.
            request.session["usuario"] = {**seguridad.usuario_actual(request), "huella": nueva_huella}
            return "Tu contraseña cambió. Tus otras sesiones abiertas se cerraron."
    return _cambio_de_usuario(request, cambio, "Contraseña nueva puesta: sus sesiones abiertas se cerraron.")


# --- Destinatarios de los avisos (solo administradores) ------------------------------------------------------

def _render_destinatarios(request: Request, conn, status_code: int = 200, **contexto) -> Response:
    return PLANTILLAS.TemplateResponse(request, "destinatarios.html", {
        "seccion": "destinatarios", "destinatarios": destinatarios.listar(conn),
        "historial": historial.ultimos(conn, historial.DE_DESTINATARIOS), "acciones": historial.ACCIONES,
        "hecho": request.session.pop("hecho", None), "formulario": {}, **contexto,
    }, status_code=status_code)


def _cambio_de_destinatario(request: Request, cambio, hecho: str, formulario: dict | None = None) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            mensaje = cambio(conn) or hecho
        except destinatarios.DestinatarioInvalido as exc:
            return _render_destinatarios(request, conn, 400, error=str(exc), formulario=formulario or {})
    request.session["hecho"] = mensaje
    return RedirectResponse("/destinatarios", status_code=303)


@router.get("/destinatarios", response_class=HTMLResponse, dependencies=[Depends(seguridad.exigir_admin)])
def pagina_destinatarios(request: Request) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_destinatarios(request, conn)


@router.post("/destinatarios", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def agregar_destinatario(request: Request, email: str = Form(""), nombre: str = Form("")) -> Response:
    def cambio(conn):
        destinatarios.agregar(conn, email, nombre, _quien(request))
    return _cambio_de_destinatario(request, cambio, f"Destinatario agregado: {nombre.strip()} <{email.strip()}>.",
                                   {"email": email, "nombre": nombre})


@router.post("/destinatarios/{destinatario_id}/estado", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def cambiar_estado_destinatario(request: Request, destinatario_id: int, activo: str = Form("")) -> Response:
    def cambio(conn):
        if activo not in ("0", "1"):
            raise destinatarios.DestinatarioInvalido("Estado no válido.")
        if not destinatarios.cambiar_estado(conn, destinatario_id, activo == "1", _quien(request)):
            return "No se cambió nada: ya estaba así."
    return _cambio_de_destinatario(request, cambio,
                                   "Destinatario activado." if activo == "1" else
                                   "Destinatario quitado: ya no recibirá avisos (lo enviado antes se conserva).")


# --- Avisos fallidos o inciertos (solo administradores) ------------------------------------------------------

def _render_avisos(request: Request, conn, status_code: int = 200, **contexto) -> Response:
    return PLANTILLAS.TemplateResponse(request, "avisos.html", {
        "seccion": "avisos", "avisos": reintentos.por_revisar(conn, _ahora()),
        "motivos_aviso": {**avisos.MOTIVOS, resumen.MOTIVO: "Resumen semanal",
                          aviso_encargado.MOTIVO: "Correo al nuevo encargado"},
        "historial": historial.ultimos(conn, historial.DE_AVISOS), "acciones": historial.ACCIONES,
        "hecho": request.session.pop("hecho", None), **contexto,
    }, status_code=status_code)


def _cambio_de_aviso(request: Request, cambio) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            mensaje = cambio(conn)
        except reintentos.AvisoInvalido as exc:
            return _render_avisos(request, conn, 400, error=str(exc))
    request.session["hecho"] = mensaje
    return RedirectResponse("/avisos", status_code=303)


@router.get("/avisos", response_class=HTMLResponse, dependencies=[Depends(seguridad.exigir_admin)])
def pagina_avisos(request: Request) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_avisos(request, conn)


@router.post("/avisos/{outbox_id}/reintentar", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def reintentar_aviso(request: Request, outbox_id: int, revise_enviados: str = Form("")) -> Response:
    def cambio(conn):
        a = reintentos.reintentar(conn, outbox_id, _ahora(), _quien(request), revise_enviados == "1")
        if a.es_resumen:
            return (f"Resumen semanal {a.semana} para {a.para} preparado otra vez: sale con el siguiente envío del"
                    " resumen (python -m app.cli notify --resumen-semanal --send).")
        return (f"Aviso del cartel {a.nro_sicop} para {a.para} preparado otra vez: sale en el siguiente envío"
                " de avisos.")
    return _cambio_de_aviso(request, cambio)


@router.post("/avisos/{outbox_id}/confirmar", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def confirmar_aviso(request: Request, outbox_id: int) -> Response:
    def cambio(conn):
        a = reintentos.confirmar_salida(conn, outbox_id, _ahora(), _quien(request))
        return f"Aviso del {a.que} para {a.para} marcado como enviado: no se reenviará."
    return _cambio_de_aviso(request, cambio)


# --- Documentos de la ficha y bitácora de consultas (enriquecimiento, lección 4, entrega 4B) ----------------

def _no_encontrado(request: Request, mensaje: str) -> Response:
    return PLANTILLAS.TemplateResponse(request, "error.html", {"mensaje": mensaje}, status_code=404)


def _archivo(ruta: Path, nombre: str | None = None, tipo: str = "application/octet-stream",
             en_linea: bool = False) -> FileResponse:
    """Un archivo del disco. Con nombre: como adjunto (se descarga; el navegador no lo abre dentro del panel), salvo
    en_linea=True («Ver»: el navegador lo muestra y, si se guarda, conserva el nombre)."""
    respuesta = FileResponse(ruta, media_type=tipo, filename=nombre,
                             content_disposition_type="attachment" if nombre and not en_linea else "inline")
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    return respuesta


def _en_linea(datos: bytes, nombre: str, tipo: str) -> Response:
    """Un archivo de dentro de un ZIP, para verlo en el navegador (nunca se escribe a disco)."""
    return Response(datos, media_type=tipo, headers={
        "Content-Disposition": f"inline; filename*=utf-8''{quote(PurePosixPath(nombre).name)}",
        "X-Content-Type-Options": "nosniff"})


@router.get("/oportunidades/{nro_sicop}/documentos/{doc_id}")
def descargar_documento(request: Request, nro_sicop: str, doc_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        hallado = fichas_panel.documento_guardado(conn, settings.documents_dir, nro_sicop, doc_id)
    if hallado is None:
        return _no_encontrado(request, "Ese documento no está guardado (o se borró al cierre del cartel).")
    log.info("Descarga de documento %s del cartel %s · usuario %s", doc_id, nro_sicop,
             (seguridad.usuario_actual(request) or {}).get("id"))
    return _archivo(*hallado)


def _volver_cartel(nro_sicop: str) -> tuple[str, str]:
    return f"/oportunidades/{nro_sicop}#documentos", f"Cartel {nro_sicop}"


def _documento_para_ver(request: Request, nro_sicop: str, doc_id: int):
    """(ruta, nombre, settings) del documento guardado, o la página de error."""
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        hallado = fichas_panel.documento_guardado(conn, settings.documents_dir, nro_sicop, doc_id)
    if hallado is None:
        return _no_encontrado(request, "Ese documento no está guardado (o se borró al cierre del cartel).")
    log.info("Ver documento %s del cartel %s · usuario %s", doc_id, nro_sicop,
             (seguridad.usuario_actual(request) or {}).get("id"))
    return (*hallado, settings)


def _no_se_puede_ver(request: Request, descargar: str, motivo: str) -> Response:
    return PLANTILLAS.TemplateResponse(request, "error.html", {
        "mensaje": f"No se puede ver: {motivo}.", "volver": (descargar, "Descargar el documento")}, status_code=422)


def _ver_excel(request: Request, descargar: str, volver: tuple[str, str], nombre: str, datos: bytes) -> Response:
    try:
        hojas = visor.hojas_excel(datos)
    except visor.NoSePuedeLeer as exc:
        return _no_se_puede_ver(request, descargar, str(exc))
    return PLANTILLAS.TemplateResponse(request, "visor_excel.html", {
        "nombre": nombre, "hojas": hojas, "descargar": descargar, "volver": volver, "MAX_FILAS": visor.MAX_FILAS,
        "MAX_COLUMNAS": visor.MAX_COLUMNAS})


def _ver(request: Request, ruta: Path, nombre: str, clase: str | None, descargar: str,
         volver: tuple[str, str]) -> Response:
    """«Ver» un archivo del disco: PDF e imágenes en línea, Excel como tabla y ZIP como lista (app/visor.py)."""
    if clase in ("pdf", "imagen"):
        return _archivo(ruta, nombre, visor.tipo(nombre) or visor.tipo(ruta.name), en_linea=True)
    if clase == "excel":
        return _ver_excel(request, descargar, volver, nombre, ruta.read_bytes())
    if clase == "zip":
        try:
            entradas = visor.entradas_zip(ruta)
        except visor.NoSePuedeLeer as exc:
            return _no_se_puede_ver(request, descargar, str(exc))
        return PLANTILLAS.TemplateResponse(request, "visor_zip.html", {
            "nombre": nombre, "entradas": entradas, "descargar": descargar, "ver_base": f"{descargar}/ver",
            "volver": volver})
    return _no_se_puede_ver(request, descargar, "este tipo de archivo solo se puede descargar")


def _ver_dentro(request: Request, ruta: Path, nombre: str, indice: int, max_bytes: int, descargar: str,
                volver: tuple[str, str]) -> Response:
    """Un PDF, imagen o Excel de dentro de un ZIP del disco (leído en memoria, nunca a disco)."""
    try:
        leido = visor.leer_entrada(ruta, indice, max_bytes)
    except visor.NoSePuedeLeer as exc:
        return _no_se_puede_ver(request, descargar, str(exc))
    if leido is None:
        return _no_encontrado(request, "Ese archivo no está dentro del ZIP.")
    interno, datos = leido
    clase = visor.vista(interno)
    if clase in ("pdf", "imagen"):
        return _en_linea(datos, interno, visor.tipo(interno))
    if clase == "excel":
        return _ver_excel(request, descargar, volver, f"{nombre} › {interno}", datos)
    return _no_se_puede_ver(request, descargar, "este tipo de archivo solo se puede descargar (con el ZIP)")


@router.get("/oportunidades/{nro_sicop}/documentos/{doc_id}/ver")
def ver_documento(request: Request, nro_sicop: str, doc_id: int) -> Response:
    """«Ver» (pedido de Oscar, 29/10): PDF e imágenes en línea, ZIP como lista y Excel como tabla."""
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _documento_para_ver(request, nro_sicop, doc_id)
    if isinstance(hallado, Response):
        return hallado
    ruta, nombre, settings = hallado
    return _ver(request, ruta, nombre, visor.vista(nombre) or visor.vista(ruta.name),
                f"/oportunidades/{nro_sicop}/documentos/{doc_id}", _volver_cartel(nro_sicop))


@router.get("/oportunidades/{nro_sicop}/documentos/{doc_id}/ver/{indice}")
def ver_dentro_del_zip(request: Request, nro_sicop: str, doc_id: int, indice: int) -> Response:
    """Un PDF, imagen o Excel de dentro de un ZIP guardado."""
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _documento_para_ver(request, nro_sicop, doc_id)
    if isinstance(hallado, Response):
        return hallado
    ruta, nombre, settings = hallado
    if (visor.vista(nombre) or visor.vista(ruta.name)) != "zip":
        return _no_encontrado(request, "Ese documento no es un ZIP.")
    return _ver_dentro(request, ruta, nombre, indice, settings.document_max_mb * 1024 * 1024,
                       f"/oportunidades/{nro_sicop}/documentos/{doc_id}", _volver_cartel(nro_sicop))


@router.get("/bitacora", response_class=HTMLResponse, dependencies=[Depends(seguridad.exigir_admin)])
def pagina_bitacora(request: Request, por_revisar: str = "") -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        datos = fichas_panel.bitacora(conn, solo_por_revisar=por_revisar == "1")
    return PLANTILLAS.TemplateResponse(request, "bitacora.html", {
        "seccion": "bitacora", **datos, "solo_por_revisar": por_revisar == "1", "hecho": request.session.pop("hecho", None),
        "activado": settings.enrich_enabled, "maximo": settings.enrich_max_per_day,
        "dias": settings.recordings_keep_days, "RESULTADOS": fichas_panel.RESULTADOS, "CORRIDAS": fichas_panel.CORRIDAS,
    })


@router.get("/asistente/registro", response_class=HTMLResponse, dependencies=[Depends(seguridad.exigir_admin)])
def registro_asistente(request: Request) -> Response:
    """Registro del asistente (lección 5): quién hizo qué y cuándo con la lista, las respuestas, los documentos, el
    resultado y el perfil. Solo administradores. Sale de audit_log (no se borra ni se modifica)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        eventos = historial.ultimos(conn, historial.REGISTRO_ASISTENTE, limite=300)
    return PLANTILLAS.TemplateResponse(request, "registro_asistente.html", {
        "seccion": "registro_asistente", "eventos": eventos, "acciones": historial.ACCIONES,
        "activo": _asistente_encendido(), "limite": 300,
    })


def _render_grabacion(request: Request, conn, consulta_id: int, status_code: int = 200, error: str | None = None
                      ) -> Response:
    settings = load_settings()
    c = fichas_panel.consulta(conn, consulta_id)
    if c is None:
        return _no_encontrado(request, "Esa consulta no está en la bitácora.")
    video, capturas = fichas_panel.archivos_grabacion(settings.recordings_dir, c)
    return PLANTILLAS.TemplateResponse(request, "grabacion.html", {
        "seccion": "bitacora", "c": c, "video": video, "capturas": capturas, "error": error,
        "dias": settings.recordings_keep_days, "RESULTADOS": fichas_panel.RESULTADOS,
        "hecho": request.session.pop("hecho", None),
    }, status_code=status_code)


@router.get("/bitacora/consultas/{consulta_id}", response_class=HTMLResponse,
            dependencies=[Depends(seguridad.exigir_admin)])
def pagina_grabacion(request: Request, consulta_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_grabacion(request, conn, consulta_id)


@router.get("/bitacora/consultas/{consulta_id}/archivos/{nombre}", dependencies=[Depends(seguridad.exigir_admin)])
def archivo_grabacion(request: Request, consulta_id: int, nombre: str) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        c = fichas_panel.consulta(conn, consulta_id)
    ruta = fichas_panel.archivo_grabacion(settings.recordings_dir, c, nombre) if c else None
    if ruta is None:
        return _no_encontrado(request, f"La grabación ya no está (se guardan {settings.recordings_keep_days} días).")
    return _archivo(ruta, tipo="video/webm" if nombre.endswith(".webm") else "image/png")


@router.post("/bitacora/consultas/{consulta_id}/revisada", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def marcar_grabacion_revisada(request: Request, consulta_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            fichas_panel.marcar_revisada(conn, consulta_id, _quien(request), _ahora())
        except fichas_panel.RevisionInvalida as exc:
            return _render_grabacion(request, conn, consulta_id, 400, error=str(exc))
    request.session["hecho"] = "Grabación marcada como revisada: desde ahora sigue la retención normal."
    return RedirectResponse(f"/bitacora/consultas/{consulta_id}", status_code=303)


# --- Ayuda «¿Cómo se usa?» (ayuda, lección 3): los textos se leen de docs/ayuda/ ---------------------------------

@router.get("/ayuda", response_class=HTMLResponse)
def pagina_ayuda(request: Request, q: str = "") -> Response:
    es_admin = seguridad.es_admin(request)
    consulta = q.strip()[:100]
    votos = None
    if es_admin and _base_no_lista(request) is None:   # «Cómo les fue con la ayuda»: solo administradores
        with closing(connect(load_settings().database_path)) as conn:
            votos = ayuda_votos.resumen(conn)
    return PLANTILLAS.TemplateResponse(request, "ayuda.html", {
        "seccion": "ayuda", "bloques": ayuda.indice(es_admin), "q": consulta,
        "resultados": ayuda.buscar(consulta, es_admin) if consulta else None, "glosario": ayuda.glosario(),
        "votos": votos, "titulos": {m.nombre: m.titulo for m in ayuda.todas()},
    })


@router.get("/ayuda/{nombre}", response_class=HTMLResponse)
def pagina_mision(request: Request, nombre: str) -> Response:
    mision = ayuda.buscar_mision(nombre)
    if mision is None:
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": "No hay una misión con ese nombre.", "seccion": "ayuda"}, status_code=404)
    if mision.solo_admin and not seguridad.es_admin(request):
        raise seguridad.SinPermiso()
    return PLANTILLAS.TemplateResponse(request, "ayuda_mision.html", {
        "seccion": "ayuda", "mision": mision, "cuerpo": ayuda.pagina(mision),
        "hecho": request.session.pop("hecho_voto", None), "error": request.session.pop("error_voto", None)})


@router.post("/ayuda/{nombre}/voto", dependencies=[Depends(verificar_csrf)])
def votar_mision(request: Request, nombre: str, util: str = Form(""), comentario: str = Form("")) -> Response:
    mision = ayuda.buscar_mision(nombre)
    if mision is None:
        return PLANTILLAS.TemplateResponse(request, "error.html", {
            "mensaje": "No hay una misión con ese nombre.", "seccion": "ayuda"}, status_code=404)
    if mision.solo_admin and not seguridad.es_admin(request):
        raise seguridad.SinPermiso()
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            ayuda_votos.votar(conn, mision.nombre, util, comentario, _quien(request), _ahora())
            request.session["hecho_voto"] = "Gracias: tu respuesta ayuda a mejorar la ayuda."
        except ayuda_votos.VotoInvalido as exc:
            request.session["error_voto"] = str(exc)
    return RedirectResponse(f"/ayuda/{mision.nombre}#te-sirvio", status_code=303)


# --- Perfil de Hermatix (asistente de elegibilidad, lección 1): lo ven los dos niveles; cargan los administradores --

def _datos_perfil(valor: str, numero: str, unidad: str, vigente_desde: str, vence_el: str, nota: str) -> perfil.Datos:
    return perfil.Datos(valor, numero, unidad, vigente_desde, vence_el, nota)


def _subido(archivo: UploadFile | None):
    return (archivo.file, archivo.filename) if archivo is not None and archivo.filename else None


def _render_perfil(request: Request, conn, status_code: int = 200, **contexto) -> Response:
    es_admin = seguridad.es_admin(request)
    elementos = perfil.listar(conn)
    return PLANTILLAS.TemplateResponse(request, "perfil.html", {
        "seccion": "perfil", "elementos": elementos, "TIPOS": perfil.TIPOS,
        "sugerencias": perfil.sugerencias(conn) if es_admin else {}, "es_admin": es_admin,
        "hecho": request.session.pop("hecho_perfil", None), "formulario": {},
        **contexto}, status_code=status_code)


def _render_elemento(request: Request, conn, item_id: int, status_code: int = 200, **contexto) -> Response:
    elemento = perfil.obtener(conn, item_id)
    if elemento is None:
        return _no_encontrado(request, "Ese elemento del perfil no existe.")
    return PLANTILLAS.TemplateResponse(request, "perfil_elemento.html", {
        "seccion": "perfil", "e": elemento, "versiones": perfil.versiones(conn, item_id),
        "cambios": perfil.cambios(conn, item_id), "accesos": perfil.accesos(conn, item_id),
        "ACCIONES": historial.ACCIONES,
        "es_admin": seguridad.es_admin(request), "hecho": request.session.pop("hecho_perfil", None),
        "formulario": {}, **contexto}, status_code=status_code)


def _estado_error(exc: Exception) -> int:
    return 413 if isinstance(exc, expediente_archivos.ArchivoMuyGrande) else 400


@router.get("/perfil", response_class=HTMLResponse)
def pagina_perfil(request: Request) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_perfil(request, conn)


@router.post("/perfil", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def crear_elemento_perfil(request: Request, tipo: str = Form(""), titulo: str = Form(""), valor: str = Form(""),
                          numero: str = Form(""), unidad: str = Form(""), vigente_desde: str = Form(""),
                          vence_el: str = Form(""), nota: str = Form(""),
                          archivo: UploadFile | None = File(None)) -> Response:
    """Agrega un elemento; si trae datos o documento, también su primera versión (si no, queda «pendiente»)."""
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    datos = _datos_perfil(valor, numero, unidad, vigente_desde, vence_el, nota)
    subido = _subido(archivo)
    formulario = {"tipo": tipo, "titulo": titulo, **datos.__dict__}
    with closing(connect(settings.database_path)) as conn:
        try:
            perfil.validar(datos)
            item_id = perfil.crear(conn, tipo, titulo, _quien(request), _ahora())
        except perfil.PerfilInvalido as exc:
            return _render_perfil(request, conn, 400, error=str(exc), formulario=formulario)
        if subido is not None or datos.valor.strip() or datos.numero.strip():
            try:
                perfil.nueva_version(conn, settings.profile_docs_dir, item_id, datos, subido,
                                     settings.profile_doc_max_mb * 1024 * 1024, _quien(request), _ahora())
            except (perfil.PerfilInvalido, expediente_archivos.ArchivoInvalido) as exc:
                return _render_elemento(request, conn, item_id, _estado_error(exc), formulario=formulario,
                                        error=f"El elemento se agregó como pendiente, pero sus datos no: {exc}")
    request.session["hecho_perfil"] = "Elemento agregado."
    return RedirectResponse(f"/perfil/{item_id}", status_code=303)


@router.get("/perfil/{item_id}", response_class=HTMLResponse)
def pagina_elemento_perfil(request: Request, item_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_elemento(request, conn, item_id)


@router.post("/perfil/{item_id}/version", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def nueva_version_perfil(request: Request, item_id: int, valor: str = Form(""), numero: str = Form(""),
                         unidad: str = Form(""), vigente_desde: str = Form(""), vence_el: str = Form(""),
                         nota: str = Form(""), archivo: UploadFile | None = File(None)) -> Response:
    """Carga o reemplaza los datos del elemento; la versión anterior queda en el historial."""
    if (error := _base_no_lista(request)) is not None:
        return error
    settings = load_settings()
    datos = _datos_perfil(valor, numero, unidad, vigente_desde, vence_el, nota)
    with closing(connect(settings.database_path)) as conn:
        try:
            perfil.nueva_version(conn, settings.profile_docs_dir, item_id, datos, _subido(archivo),
                                 settings.profile_doc_max_mb * 1024 * 1024, _quien(request), _ahora())
        except (perfil.PerfilInvalido, expediente_archivos.ArchivoInvalido) as exc:
            return _render_elemento(request, conn, item_id, _estado_error(exc), error=str(exc),
                                    formulario=datos.__dict__)
    request.session["hecho_perfil"] = "Datos guardados: la versión anterior quedó en el historial."
    return RedirectResponse(f"/perfil/{item_id}", status_code=303)


@router.post("/perfil/{item_id}/pendiente", response_class=HTMLResponse, dependencies=SOLO_ADMIN)
def pendiente_perfil(request: Request, item_id: int, nota: str = Form("")) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        try:
            perfil.marcar_pendiente(conn, item_id, nota, _quien(request), _ahora())
        except perfil.PerfilInvalido as exc:
            return _no_encontrado(request, str(exc))
    request.session["hecho_perfil"] = "Marcado como pendiente."
    return RedirectResponse(f"/perfil/{item_id}", status_code=303)


def _documento_perfil(request: Request, item_id: int, version_id: int, accion: str):
    """(ruta, Version) del documento, con el acceso ya registrado; o la página de «no encontrado»."""
    settings = load_settings()
    with closing(connect(settings.database_path)) as conn:
        elemento = perfil.obtener(conn, item_id)
        hallado = perfil.documento(conn, settings.profile_docs_dir, item_id, version_id) if elemento else None
        if hallado is None:
            return _no_encontrado(request, "Ese documento no está en el perfil.")
        perfil.registrar_acceso(conn, _quien(request), accion, item_id, elemento.titulo, hallado[1])
    return hallado


@router.get("/perfil/{item_id}/versiones/{version_id}/archivo")
def descargar_documento_perfil(request: Request, item_id: int, version_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _documento_perfil(request, item_id, version_id, "descargar_documento_perfil")
    if isinstance(hallado, Response):
        return hallado
    ruta, v = hallado
    return _archivo(ruta, v.archivo_nombre, perfil.MIME[v.archivo_extension])


@router.get("/perfil/{item_id}/versiones/{version_id}/ver")
def ver_documento_perfil(request: Request, item_id: int, version_id: int) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    hallado = _documento_perfil(request, item_id, version_id, "ver_documento_perfil")
    if isinstance(hallado, Response):
        return hallado
    ruta, v = hallado
    return _archivo(ruta, v.archivo_nombre, perfil.MIME[v.archivo_extension], en_linea=True)
