"""Rutas del panel: inicio y cierre de sesión, lista de oportunidades, detalle, revisión y carga de archivos;
seguimiento de carteles (gestor de documentos); para administradores, usuarios, destinatarios y avisos
fallidos o inciertos.

Todas, salvo /login, exigen sesión (middleware en app/web/seguridad.py) y todo POST lleva token CSRF.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.cli import EJEMPLOS_POR_ADVERTENCIA, IMPORTADORES, MAX_RECHAZOS_VISIBLES, SEPARADORES
from app.config import load_settings
from app.database import check_database, connect
from app.importers import zip_pliegos
from app.importers.comun import HORA_CR, ORIGENES, ImportacionError
from app.matching.reglas import ReglasError, cargar_reglas
from app import (avisos, calidad, competencia, destinatarios, exportar, historial, panel, reintentos, resumen,
                 seguimiento, usuarios)
from app.historial import Quien
from app.web import carga, seguridad
from app.web.intentos import BLOQUEO
from app.web.seguridad import verificar_csrf

log = logging.getLogger(__name__)


def _contexto_sesion(request: Request) -> dict:
    """Variables de todas las plantillas: el token CSRF de los formularios y quién inició sesión."""
    return {"csrf_token": seguridad.csrf_token(request), "usuario": seguridad.usuario_actual(request)}


PLANTILLAS = Jinja2Templates(directory=Path(__file__).parent / "templates",  # autoescape activo; no se desactiva
                             context_processors=[_contexto_sesion])
PLANTILLAS.env.filters["fecha"] = panel.fecha_cr
PLANTILLAS.env.filters["legible"] = panel.legible
PLANTILLAS.env.filters["titulo"] = panel.formato_titulo
PLANTILLAS.env.globals["monto"] = panel.monto
PLANTILLAS.env.globals.update(
    ENCAJES=panel.ENCAJES, PLAZOS=panel.PLAZOS, CALIDADES=panel.CALIDADES, DECISIONES=panel.DECISIONES,
    MOTIVOS=panel.MOTIVOS, NOMBRES_FAMILIA=panel.NOMBRES_FAMILIA, resaltar=panel.resaltar,
    nombre_competidor=competencia.nombre_competidor,
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
                    formulario: dict[str, str] | None = None, status_code: int = 200) -> Response:
    version = panel.version_vigente(conn)
    ahora = _ahora()
    datos = panel.detalle(conn, nro_sicop, version, ahora)
    if datos is None:
        return PLANTILLAS.TemplateResponse(
            request, "error.html", {"mensaje": f"No hay un cartel con Número SICOP {nro_sicop}."}, status_code=404)
    seg = seguimiento.estado(conn, nro_sicop)
    return PLANTILLAS.TemplateResponse(request, "oportunidad.html", {
        "d": datos, "version": version, "aviso": _aviso_reglas(version, panel.importado_sin_evaluar(conn)), "error": error,
        "seg": seg, "puede_entrar": seguimiento.puede_entrar(seguridad.usuario_actual(request), seg),
        "regresiva": panel.cuenta_regresiva(datos.compra.fecha_cierre_recepcion, ahora),
        "formulario": formulario or {},
    }, status_code=status_code)


@router.get("/oportunidades/{nro_sicop}", response_class=HTMLResponse)
def oportunidad(request: Request, nro_sicop: str) -> Response:
    if (error := _base_no_lista(request)) is not None:
        return error
    with closing(connect(load_settings().database_path)) as conn:
        return _render_detalle(request, conn, nro_sicop)


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
        try:
            seguimiento.abrir(conn, nro_sicop, _quien(request), _ahora())
        except seguimiento.SeguimientoInvalido as exc:
            return _render_detalle(request, conn, nro_sicop, str(exc), status_code=400)
    return RedirectResponse(f"/oportunidades/{nro_sicop}", status_code=303)


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
    return PLANTILLAS.TemplateResponse(request, "cargar.html", {
        "seccion": "cargar", "reportes": list(carga.EXTENSIONES), "origenes": ORIGENES, "extensiones": carga.EXTENSIONES,
        "limite_mb": carga.en_megas(load_settings().upload_max_bytes), "separadores": SEPARADORES,
        "max_rechazos": MAX_RECHAZOS_VISIBLES, "ejemplos": EJEMPLOS_POR_ADVERTENCIA, "formulario": {},
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
    # Sin Post/Redirect/Get: el detalle de los rechazos no se guarda en la base. Si se recarga la página y se
    # reenvía el archivo, el hash lo reconoce y no se importa dos veces.
    return _render_carga(request, 400 if error else 200, formulario=formulario, partes=partes, error=error)


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
        "asignables": seguimiento.asignables(conn) if seguridad.es_admin(request) else [],
        "regresiva": panel.cuenta_regresiva(datos.compra.fecha_cierre_recepcion, ahora),
        "hecho": request.session.pop("hecho", None), **contexto,
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
    request.session["hecho"] = "Encargado asignado." if cambio else "No se cambió nada: ya era el encargado."
    return RedirectResponse(f"/seguimiento/{nro_sicop}", status_code=303)


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
        "motivos_aviso": {**avisos.MOTIVOS, resumen.MOTIVO: "Resumen semanal"},
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
