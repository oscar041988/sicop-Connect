"""Reporte de cartel Hermatix en PDF, máximo 3 páginas (Reporte con IA, lección 4; DECISION_IA.md regla 9).

* La IA no escribe el reporte, lo alimenta: el diseño, el orden, los límites y los KPI de SICOP (monto estimado por
  moneda, líneas, unidades, cierre y días para el cierre, estado, tipo de procedimiento, encaje de las reglas) los
  pone la app desde la base, igual que el panel. Del resumen (ia_summaries) salen solo los textos y los KPI del
  pliego, cada uno con su cita; «no encontrado» se muestra así.
* Cada sección tiene un máximo; si hay más, se muestran los primeros (los requerimientos excluyentes primero) y
  «y N más en el panel». Si aun así no cabe en MAX_PAGINAS, se vuelve a armar con límites más chicos; si tampoco,
  error: nunca se guarda un reporte más largo.
* Al final, «Por qué se recomienda»: la explicación detallada del resumen (prompt v6; Oscar, 2026-11-09), unos
  media página. Por eso el máximo pasó de 2 a 3 páginas. Un resumen anterior a v6 no la trae y el reporte lo dice.
* PDF con el Chromium de Playwright (page.pdf), que la app ya usa: sin librerías nuevas. El archivo queda en
  REPORTS_DIR/<nro>/ (fuera de Git, en el respaldo) y su registro en ia_reports (migración 0036): un reporte nuevo
  nunca borra el anterior, y si no cambiaron el resumen ni los estados «¿Cumple?» se reutiliza el último.
* «¿Cumple?» (migración 0038, app/cumplimiento.py): en «Qué piden», lo que marcó una persona; en «Requerimientos»,
  el estado del asistente de elegibilidad.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import cumplimiento, fichas_panel, historial, panel
from app.ai import expediente as ia_expediente
from app.ai import resumen as ia_resumen
from app.config import PROJECT_ROOT, Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

PLANTILLAS = PROJECT_ROOT / "app" / "web" / "templates"
LOGO = PROJECT_ROOT / "app" / "web" / "static" / "logo-hermatix.png"
NO = ia_resumen.NO
PIE = "Generado con IA a partir de datos públicos de SICOP · verificar con el pliego"
ENCAJES = ("alta", "media", "baja", "ninguno")

MAX_PAGINAS = 3
MAX_EXPLICACION = 1800   # caracteres: unas 250 palabras con holgura; es un tope de seguridad, no un recorte normal
# Máximos por sección. LIMITES aprovecha hasta 3 páginas (Ivania, 2026-11-09: medido con los 35 carteles reales con
# resumen y una explicación de 250 palabras, ninguno pasó de 3). Si el PDF pasa de MAX_PAGINAS se rehace con
# LIMITES_MEDIOS (los de cuando el máximo era 2 páginas) y, si tampoco, con LIMITES_CORTOS.
LIMITES = {"que_piden": 14, "especificaciones": 5, "requerimientos": 18, "criterios": 8, "riesgos": 5,
           "otros_plazos": 6, "fuentes": 10, "caracteres": 300}
LIMITES_MEDIOS = {"que_piden": 8, "especificaciones": 3, "requerimientos": 10, "criterios": 5, "riesgos": 3,
                  "otros_plazos": 4, "fuentes": 6, "caracteres": 200}
LIMITES_CORTOS = {"que_piden": 6, "especificaciones": 2, "requerimientos": 7, "criterios": 4, "riesgos": 3,
                  "otros_plazos": 3, "fuentes": 4, "caracteres": 140}
TIPOS = {"legal": "Legal", "tecnico": "Técnico", "técnico": "Técnico", "financiero": "Financiero",
         "experiencia": "Experiencia"}
KPI_PLIEGO = (("plazo_entrega", "Plazo de entrega"), ("vigencia_contrato", "Vigencia del contrato"),
              ("garantia_participacion_pct", "Garantía de participación"),
              ("garantia_cumplimiento_pct", "Garantía de cumplimiento"), ("peso_precio_pct", "Peso del precio"))


class ReporteError(ValueError):
    """El reporte no se puede generar; el mensaje es el que verá la persona."""


@dataclass(frozen=True)
class Reporte:
    id: int
    nro_sicop: str
    ia_summary_id: int
    ruta: Path
    sha256: str
    paginas: int
    creado_en: str
    cumple_huella: str | None = None     # los estados «¿Cumple?» con que se hizo (migración 0038)
    reutilizado: bool = False


# --- Datos del reporte: la app calcula los KPI y aplica los límites ------------------------------------------------

def _corto(texto, maximo: int) -> str:
    texto = " ".join(str(texto if texto is not None else NO).split())
    return texto if len(texto) <= maximo else texto[:maximo - 1].rstrip() + "…"


def _limitar(lista: list, maximo: int) -> tuple[list, int]:
    """(los primeros `maximo`, cuántos quedan fuera)."""
    lista = list(lista or [])
    return lista[:maximo], max(0, len(lista) - maximo)


def _explicacion(texto) -> list[str]:
    """Los párrafos de la explicación detallada de la recomendación, sin pasar de MAX_EXPLICACION caracteres; [] si
    el resumen no la trae (anterior al prompt v6)."""
    if not isinstance(texto, str) or texto.strip() in ("", NO):
        return []
    parrafos, quedan = [], MAX_EXPLICACION
    for linea in texto.splitlines():
        if quedan <= 1 or not linea.strip():
            continue
        parrafos.append(_corto(linea, quedan))
        quedan -= len(parrafos[-1])
    return parrafos


def titulo(descripcion: str | None) -> str:
    """El título de SICOP casi todo en mayúsculas sale todo en mayúsculas («cOMPRA DE CAMARAS», con las mayúsculas
    invertidas en SICOP → «COMPRA DE CAMARAS»; pedido de Ivania, 2026-11-05). Los demás, como vienen."""
    if not descripcion:
        return "(sin título)"
    return descripcion.upper() if panel._casi_todo_mayusculas(descripcion) else descripcion


def _unidades(lineas) -> str:
    total = Decimal(0)
    for linea in lineas:
        try:
            total += Decimal(str(linea.cantidad))
        except (InvalidOperation, TypeError):
            return NO
    return f"{total.normalize():f}"


def _encaje(evaluaciones) -> str:
    mejor = min(evaluaciones, key=lambda e: ENCAJES.index(e.encaje) if e.encaje in ENCAJES else 9, default=None)
    if mejor is None or mejor.encaje not in ("alta", "media", "baja"):
        return "Sin coincidencia con las reglas de Hermatix"
    familia = panel.NOMBRES_FAMILIA.get(mejor.familia, mejor.familia)
    return f"{mejor.encaje.capitalize()} · {familia}"


def kpis_sicop(conn: sqlite3.Connection, nro_sicop: str, ahora: datetime) -> list[tuple[str, str]]:
    """Los KPI de SICOP, calculados desde la base como en el panel (nunca del modelo)."""
    det = panel.detalle(conn, nro_sicop, panel.version_vigente(conn), ahora)
    if det is None:
        raise ReporteError(f"No hay un cartel con Número SICOP {nro_sicop}.")
    c, sicop = det.compra, fichas_panel.informacion(conn, nro_sicop)
    if sicop and sicop.monto is not None:
        monto = panel.monto(sicop.monto, sicop.moneda)
    else:
        monto = " · ".join(panel.monto(m.valor, moneda) for moneda, m in c.estimado_por_moneda.items()) or NO
    cierre = (sicop.cierre if sicop and sicop.cierre else None) or c.fecha_cierre_recepcion
    return [
        ("Monto estimado", monto),
        ("Líneas · unidades", f"{len(c.lineas)} · {_unidades(c.lineas)}"),
        ("Cierre de recepción", f"{panel.fecha_cr(cierre)} · {panel.cuenta_regresiva(cierre, ahora)}"),
        ("Estado en SICOP", (sicop.estado if sicop and sicop.estado else "Sin consultar la ficha")),
        ("Tipo de procedimiento", det.tipo_procedimiento or (sicop.tipo_procedimiento if sicop else None) or NO),
        ("Encaje con Hermatix (reglas)", _encaje(det.evaluaciones)),
    ]


def _resumen(conn: sqlite3.Connection, nro_sicop: str) -> ia_resumen.Resultado:
    res = next((r for r in ia_resumen.del_cartel(conn, nro_sicop) if r.datos), None)
    if res is None:
        raise ReporteError(f"El cartel {nro_sicop} todavía no tiene resumen con IA: el reporte sale de él.")
    return res


def estados(conn: sqlite3.Connection, nro_sicop: str, ahora: datetime) -> tuple[dict, dict]:
    """«¿Cumple?»: (requerimientos según el asistente de hoy, filas de «Qué piden» según lo que marcó una persona)."""
    return (cumplimiento.de_requerimientos(conn, nro_sicop, ahora.astimezone(HORA_CR).date()),
            cumplimiento.de_lineas(conn, nro_sicop))


def datos(conn: sqlite3.Connection, nro_sicop: str, ahora: datetime, limites: dict | None = None) -> dict:
    """Todo lo que va en el reporte, ya recortado a sus máximos."""
    lim = limites or LIMITES
    n = lim["caracteres"]
    kpis = kpis_sicop(conn, nro_sicop, ahora)
    compra = panel.detalle(conn, nro_sicop, panel.version_vigente(conn), ahora).compra
    res = _resumen(conn, nro_sicop)
    r = res.datos
    est_reqs, est_lineas = estados(conn, nro_sicop, ahora)
    que_piden, mas_piden = _limitar(r.get("que_piden"), lim["que_piden"])
    piden = []
    for i in que_piden:
        specs, mas_specs = _limitar(i.get("especificaciones_clave"), lim["especificaciones"])
        piden.append({"linea": _corto(i.get("linea"), 12), "bien": _corto(i.get("bien_o_servicio"), n),
                      "cantidad": _corto(i.get("cantidad"), 12), "specs": [_corto(e, n // 2) for e in specs],
                      "mas_specs": mas_specs, "cita": i.get("cita"), "cumple": cumplimiento.linea(est_reqs, est_lineas, i)})
    todos = sorted(r.get("requerimientos") or [], key=lambda q: not q.get("excluyente"))   # excluyentes primero
    reqs, mas_reqs = _limitar(todos, lim["requerimientos"])
    criterios, mas_criterios = _limitar(r.get("criterios_de_evaluacion"), lim["criterios"])
    riesgos, mas_riesgos = _limitar(r.get("riesgos_y_dudas"), lim["riesgos"])
    plazos = r.get("plazos") or {}
    otros, mas_otros = _limitar(plazos.get("otros"), lim["otros_plazos"])
    docs, mas_docs = _limitar(list(ia_expediente.numeracion(conn, nro_sicop).items()), lim["fuentes"])
    kpi = r.get("kpi_pliego") or {}
    encaje = r.get("encaje_hermatix") or {}
    return {
        "nro": nro_sicop, "procedimiento": compra.nro_procedimiento or NO,
        "titulo": _corto(titulo(compra.descripcion), 160), "institucion": compra.institucion or NO,
        "fecha": panel.fecha_cr(ahora.isoformat()), "kpis": kpis,
        "kpi_pliego": [(nombre, _corto((kpi.get(clave) or {}).get("valor"), n), (kpi.get(clave) or {}).get("cita"))
                       for clave, nombre in KPI_PLIEGO],
        "de_que_trata": _corto(r.get("de_que_trata"), n * 2),
        "recomendacion": ia_resumen.RECOMENDACIONES.get(r.get("recomendacion"), NO),
        "recomendacion_clave": r.get("recomendacion"), "justificacion": _corto(r.get("justificacion"), n),
        "explicacion": _explicacion(r.get("explicacion_recomendacion")),
        "encaje": f"{_corto(encaje.get('producto'), 60)} — {_corto(encaje.get('por_que'), n)}",
        "piden": piden, "mas_piden": mas_piden,
        "reqs": [{"tipo": TIPOS.get(str(q.get("tipo")).lower(), _corto(q.get("tipo"), 20).capitalize()), "requisito": _corto(q.get("requisito"), n),
                  "excluyente": bool(q.get("excluyente")), "cita": q.get("cita"),
                  "cumple": cumplimiento.requerimiento(est_reqs, q)} for q in reqs],
        "mas_reqs": mas_reqs, "total_reqs": len(todos),
        "plazos": [("Cierre de recepción", (plazos.get("cierre_recepcion") or {}).get("valor"),
                    (plazos.get("cierre_recepcion") or {}).get("cita")),
                   ("Apertura de ofertas", (plazos.get("apertura_ofertas") or {}).get("valor"),
                    (plazos.get("apertura_ofertas") or {}).get("cita"))]
                  + [(_corto(o.get("plazo"), 60), _corto(o.get("valor"), n // 2), o.get("cita")) for o in otros],
        "mas_plazos": mas_otros,
        "criterios": [(_corto(x.get("criterio"), n // 2), _corto(x.get("peso"), 20), x.get("cita")) for x in criterios],
        "mas_criterios": mas_criterios,
        "riesgos": [(_corto(x.get("riesgo"), n), x.get("cita")) for x in riesgos], "mas_riesgos": mas_riesgos,
        "fuentes": [f"DOC {k} · {_corto(d.nombre or d.archivo, 70)}" for k, d in docs], "mas_fuentes": mas_docs,
        "resumen": {"id": res.id, "creado_en": panel.fecha_cr(res.creado_en), "prompt": res.prompt_version,
                    "modelo": res.modelo},
        "NO": NO, "PIE": PIE,
    }


# --- HTML y PDF ----------------------------------------------------------------------------------------------------

def _entorno() -> Environment:
    entorno = Environment(loader=FileSystemLoader(PLANTILLAS), autoescape=select_autoescape(["html"]))
    entorno.filters["fecha"] = panel.fecha_cr
    return entorno


def html(d: dict) -> str:
    logo = "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode("ascii") if LOGO.is_file() else ""
    return _entorno().get_template("reporte_cartel.html").render(d=d, logo=logo)


def _pie_pdf(nro: str) -> str:
    return ('<div style="width:100%;font-size:7.5pt;color:#5a6b7b;padding:0 12mm;display:flex;'
            'justify-content:space-between;font-family:Arial,sans-serif">'
            f'<span>{PIE} · N.º SICOP {nro}</span>'
            '<span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>')


def pdf(contenido_html: str, nro: str) -> bytes:
    """Imprime la página a PDF con el Chromium de Playwright (tamaño carta)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page()
            pagina.set_content(contenido_html, wait_until="load")
            return pagina.pdf(format="Letter", print_background=True, display_header_footer=True,
                              header_template="<span></span>", footer_template=_pie_pdf(nro),
                              margin={"top": "12mm", "bottom": "16mm", "left": "12mm", "right": "12mm"})
        finally:
            navegador.close()


def contar_paginas(contenido: bytes) -> int:
    """Páginas del PDF, contando sus objetos /Type /Page (sin librerías)."""
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", contenido))


# --- Guardar y reutilizar -----------------------------------------------------------------------------------------

_COLUMNAS = "id, nro_sicop, ia_summary_id, ruta, sha256, paginas, creado_en, cumple_huella"


def ultimo(conn: sqlite3.Connection, settings: Settings, nro_sicop: str) -> Reporte | None:
    fila = conn.execute(f"SELECT {_COLUMNAS} FROM ia_reports WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1",
                        (nro_sicop,)).fetchone()
    if fila is None:
        return None
    return Reporte(fila[0], fila[1], fila[2], settings.reports_dir / fila[3], *fila[4:])


def generar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, ahora: datetime,
            forzar: bool = False) -> Reporte:
    """El reporte del resumen vigente: reutiliza el último si no cambiaron ni el resumen ni los estados «¿Cumple?»
    (y el archivo sigue ahí)."""
    res = _resumen(conn, nro_sicop)
    # Los estados «¿Cumple?» y el diseño del reporte: si cambia cualquiera de los dos, se genera de nuevo.
    diseno = hashlib.sha256((PLANTILLAS / "reporte_cartel.html").read_bytes()).hexdigest()
    cumple_huella = hashlib.sha256(f"{cumplimiento.huella(*estados(conn, nro_sicop, ahora))}{diseno}".encode()).hexdigest()
    anterior = ultimo(conn, settings, nro_sicop)
    if (not forzar and anterior and anterior.ia_summary_id == res.id and anterior.cumple_huella == cumple_huella
            and anterior.ruta.is_file()):
        return Reporte(**{**anterior.__dict__, "reutilizado": True})
    for limites in (LIMITES, LIMITES_MEDIOS, LIMITES_CORTOS):
        contenido = pdf(html(datos(conn, nro_sicop, ahora, limites)), nro_sicop)
        paginas = contar_paginas(contenido)
        if 1 <= paginas <= MAX_PAGINAS:
            break
    else:
        raise ReporteError(f"El reporte del cartel {nro_sicop} no cabe en {MAX_PAGINAS} páginas ({paginas}):"
                           " no se guardó.")
    momento = ahora.astimezone(HORA_CR)
    base = f"{nro_sicop}/reporte_{nro_sicop}_{momento:%Y%m%d-%H%M%S}"
    relativa, n = f"{base}.pdf", 1
    while (settings.reports_dir / relativa).exists():          # nunca se sobrescribe un reporte anterior
        n += 1
        relativa = f"{base}_{n}.pdf"
    destino = settings.reports_dir / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    temporal.write_bytes(contenido)
    os.replace(temporal, destino)
    huella = hashlib.sha256(contenido).hexdigest()
    with transaccion(conn):
        reporte_id = conn.execute(
            "INSERT INTO ia_reports (nro_sicop, ia_summary_id, ruta, sha256, paginas, creado_por, creado_por_nombre,"
            " creado_en, cumple_huella) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nro_sicop, res.id, relativa, huella, paginas, quien.user_id, quien.nombre,
             momento.isoformat(timespec="seconds"), cumple_huella)).lastrowid
        historial.registrar(conn, quien, "generar_reporte", f"{nro_sicop}: {paginas} páginas")
    return Reporte(reporte_id, nro_sicop, res.id, destino, huella, paginas, momento.isoformat(timespec="seconds"),
                   cumple_huella)
