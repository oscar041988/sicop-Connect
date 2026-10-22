"""Resumen ejecutivo semanal (A4): un correo el lunes con lo que pasó la semana anterior.

Contenido (semana anterior = de lunes 00:00 a domingo 23:59, hora de Costa Rica):
* Nuevas oportunidades por familia: carteles vistos por primera vez en la semana con prioridad Alta o Media.
* Revisadas: carteles con alguna revisión en la semana, por su última decisión de la semana.
* Pendientes: oportunidades Alta o Media abiertas que nadie ha revisado.
* Próximos cierres: lo que cierra en los próximos 7 días y sigue en juego (sin revisar, «Interesa» o
  «Revisar requisitos»).
* Adjudicaciones relevantes: solo si hay adjudicaciones importadas; en firme en la semana y en alguna familia
  (las mismas cifras que la página «Competencia»).

Usa la misma outbox que los avisos: una fila por destinatario y semana, motivo «resumen_semanal», sin cartel,
version = la semana ISO del lunes en que se arma («2026-W44»). La clave de deduplicación lleva el motivo, así que
repetirlo la misma semana no prepara otro. Dry-run por defecto: vista previa en EXPORTS_DIR, sin tocar el
proveedor. Envío: «incierto» antes de llamar al proveedor; después «aceptado» o «fallido» (nunca se reenvía solo).
Solo se envía el de la semana actual: uno de una semana anterior que quedó «preparado» ya no sirve.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app import competencia, destinatarios, panel
from app.avisos import _PLANTILLAS, AvisoError, Envio, Proveedor, _marcar
from app.config import Settings
from app.database import transaccion
from app.importers.comun import HORA_CR
from app.matching.evaluar import plazo_estado
from app.notifications import EnvioIncierto, EnvioRechazado

MOTIVO = "resumen_semanal"
DIAS_PROXIMOS_CIERRES = 7
MAX_CIERRES = 15
MAX_PENDIENTES = 10


def semana(ahora: datetime) -> tuple[str, datetime, datetime]:
    """(id de la semana ISO en que se arma, inicio y fin de la semana ANTERIOR) en hora de Costa Rica."""
    local = ahora.astimezone(HORA_CR)
    fin = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    año, numero, _ = local.isocalendar()
    return f"{año}-W{numero:02d}", fin - timedelta(days=7), fin


def dedup_key(destinatario: str, id_semana: str) -> str:
    return f"{destinatario.strip().lower()}|resumen|{id_semana}|{MOTIVO}"


@dataclass
class Cartel:
    nro_sicop: str
    titulo: str | None
    institucion: str
    cierre: str | None
    regresiva: str
    estado: str          # «Sin revisar» o la decisión vigente
    enlace: str


@dataclass
class Adjudicada:
    familia: str
    carteles: int
    lider: str
    veces: int
    empate: int          # cuántos ganadores tienen las mismas veces que el primero
    montos: list         # [(moneda, total)] sin impuestos, cada moneda aparte


@dataclass
class Contenido:
    id_semana: str
    inicio: datetime
    fin: datetime
    nuevas_por_familia: list[tuple[str, int]]   # (nombre de la familia, carteles)
    nuevas_total: int
    revisadas: list[tuple[str, int]]            # (decisión, carteles)
    revisadas_total: int
    pendientes_total: int
    pendientes: list[Cartel]
    proximos_cierres: list[Cartel]
    hay_adjudicaciones: bool
    adjudicaciones: list[Adjudicada] = field(default_factory=list)
    datos_hasta: str | None = None              # última importación de carteles


def _cartel(conn, nro: str, estado: str, ahora: datetime, base_url: str) -> Cartel:
    titulo, institucion, cedula, cierre = conn.execute(
        "SELECT t.descripcion, i.nombre, t.institution_cedula, t.fecha_cierre_recepcion FROM tenders t"
        " LEFT JOIN institutions i ON i.cedula = t.institution_cedula WHERE t.nro_sicop = ?", (nro,)).fetchone()
    return Cartel(nro, titulo, institucion or f"Institución {cedula or 'sin cédula'}", cierre,
                  panel.cuenta_regresiva(cierre, ahora), estado, f"{base_url}/oportunidades/{nro}")


def contenido(conn: sqlite3.Connection, version: str, ahora: datetime, base_url: str) -> Contenido:
    id_semana, inicio, fin = semana(ahora)
    rango = {"inicio": inicio.isoformat(), "fin": fin.isoformat(), "version": version}

    nuevas = conn.execute(
        "SELECT a.familia, count(DISTINCT t.nro_sicop) FROM tenders t"
        " JOIN opportunity_assessments a ON a.nro_sicop = t.nro_sicop AND a.rules_version = :version"
        "  AND a.encaje IN ('alta', 'media')"
        " WHERE julianday(t.first_seen) >= julianday(:inicio) AND julianday(t.first_seen) < julianday(:fin)"
        " GROUP BY a.familia ORDER BY 2 DESC, 1", rango).fetchall()
    nuevas_total = conn.execute(
        "SELECT count(DISTINCT t.nro_sicop) FROM tenders t"
        " JOIN opportunity_assessments a ON a.nro_sicop = t.nro_sicop AND a.rules_version = :version"
        "  AND a.encaje IN ('alta', 'media')"
        " WHERE julianday(t.first_seen) >= julianday(:inicio) AND julianday(t.first_seen) < julianday(:fin)",
        rango).fetchone()[0]

    revisadas = conn.execute(
        "SELECT decision, count(*) FROM reviews WHERE id IN (SELECT max(id) FROM reviews"
        "  WHERE julianday(created_at) >= julianday(:inicio) AND julianday(created_at) < julianday(:fin)"
        "  GROUP BY nro_sicop) GROUP BY decision ORDER BY 2 DESC, 1", rango).fetchall()

    # Lo que sigue en juego: Alta/Media abiertas sin revisar, o con su última decisión «en curso».
    en_juego = conn.execute(
        "SELECT t.nro_sicop, t.fecha_cierre_recepcion,"
        "       (SELECT decision FROM reviews r WHERE r.nro_sicop = t.nro_sicop ORDER BY r.id DESC LIMIT 1)"
        " FROM tenders t WHERE EXISTS (SELECT 1 FROM opportunity_assessments a WHERE a.nro_sicop = t.nro_sicop"
        "   AND a.rules_version = :version AND a.encaje IN ('alta', 'media'))"
        "   OR (SELECT decision FROM reviews r WHERE r.nro_sicop = t.nro_sicop ORDER BY r.id DESC LIMIT 1)"
        f"      IN ({', '.join(repr(d) for d in panel.DECISIONES_EN_CURSO)})"
        " ORDER BY t.fecha_cierre_recepcion, t.nro_sicop", rango).fetchall()
    abiertas = [(nro, cierre, decision) for nro, cierre, decision in en_juego
                if plazo_estado(cierre, ahora) != "vencido"
                and (decision is None or decision in panel.DECISIONES_EN_CURSO)]
    sin_revisar = [nro for nro, _, decision in abiertas if decision is None]
    limite = ahora + timedelta(days=DIAS_PROXIMOS_CIERRES)
    proximos = [(nro, decision) for nro, cierre, decision in abiertas
                if plazo_estado(cierre, ahora) != "por_verificar" and datetime.fromisoformat(cierre) <= limite]

    def estado(decision):
        return panel.DECISIONES[decision] if decision else "Sin revisar"

    c = Contenido(
        id_semana=id_semana, inicio=inicio, fin=fin,
        nuevas_por_familia=[(panel.NOMBRES_FAMILIA.get(f, f), n) for f, n in nuevas], nuevas_total=nuevas_total,
        revisadas=[(panel.DECISIONES.get(d, d), n) for d, n in revisadas], revisadas_total=sum(n for _, n in revisadas),
        pendientes_total=len(sin_revisar),
        pendientes=[_cartel(conn, nro, "Sin revisar", ahora, base_url) for nro in sin_revisar[:MAX_PENDIENTES]],
        proximos_cierres=[_cartel(conn, nro, estado(d), ahora, base_url) for nro, d in proximos[:MAX_CIERRES]],
        hay_adjudicaciones=conn.execute("SELECT 1 FROM adjudicaciones LIMIT 1").fetchone() is not None,
        datos_hasta=conn.execute("SELECT max(imported_at) FROM imports WHERE report = 'carteles'").fetchone()[0],
    )
    if c.hay_adjudicaciones:
        try:
            nombres = competencia.cargar_competidores()
        except competencia.CompetidoresError:
            nombres = {}  # el resumen no se cae por el YAML: se muestran cédulas
        filtro = competencia.Filtro(desde=inicio.date(), hasta=(fin - timedelta(days=1)).date())
        for fam in competencia.resumen(conn, version, filtro, nombres).familias:
            lider = fam.competidores[0]
            c.adjudicaciones.append(Adjudicada(
                panel.NOMBRES_FAMILIA.get(fam.familia, fam.familia), len(fam.carteles),
                lider.nombre or competencia.nombre_competidor(lider.clave), lider.veces,
                sum(1 for x in fam.competidores if x.veces == lider.veces), fam.montos_ordenados()))
    return c


def asunto(c: Contenido) -> str:
    return (f"SICOP · Resumen semanal {c.inicio:%d/%m}–{c.fin - timedelta(days=1):%d/%m}: "
            f"{c.nuevas_total} nueva{'s' if c.nuevas_total != 1 else ''}, {c.pendientes_total} sin revisar, "
            f"{len(c.proximos_cierres)} por cerrar")


def componer(c: Contenido, ahora: datetime, base_url: str) -> tuple[str, str, str]:
    contexto = {"c": c, "asunto": asunto(c), "ahora": ahora.isoformat(timespec="seconds"), "panel": base_url,
                "monto": panel.monto, "hasta": c.fin - timedelta(days=1)}
    return (contexto["asunto"], _PLANTILLAS.get_template("resumen.html").render(contexto),
            _PLANTILLAS.get_template("resumen.txt").render(contexto))


@dataclass
class Resultado:
    id_semana: str
    destinatarios: int
    nuevos: int = 0                                   # filas agregadas a la outbox en esta corrida
    preparados: dict[str, list[int]] = field(default_factory=dict)  # destinatario → ids «preparado» de esta semana
    asunto: str = ""
    vista_previa: list[Path] = field(default_factory=list)
    envios: dict[str, Envio] = field(default_factory=dict)


def notify(conn: sqlite3.Connection, settings: Settings, ahora: datetime, dry_run: bool = True,
           proveedor: Proveedor | None = None) -> Resultado:
    """Prepara el resumen de esta semana para cada destinatario activo; con dry_run escribe la vista previa,
    sin dry_run lo envía. Repetible: la clave de deduplicación impide un segundo resumen la misma semana."""
    if not dry_run and proveedor is None:
        raise AvisoError("Falta el proveedor de correo para el envío real.")
    version = panel.version_vigente(conn)
    if version is None:
        raise AvisoError("Todavía no hay evaluaciones: ejecuta python -m app.cli evaluate.")
    id_semana, _, _ = semana(ahora)
    lista = destinatarios.activos(conn)
    resultado = Resultado(id_semana, len(lista))
    momento = ahora.isoformat(timespec="seconds")
    with transaccion(conn):
        for d in lista:
            para = d.email.strip().lower()
            cursor = conn.execute(
                "INSERT OR IGNORE INTO notification_outbox (dedup_key, recipient, nro_sicop, version, motivo, cierre,"
                " rules_version, status, created_at) VALUES (?, ?, NULL, ?, ?, NULL, ?, 'preparado', ?)",
                (dedup_key(para, id_semana), para, id_semana, MOTIVO, version, momento))
            resultado.nuevos += cursor.rowcount
    activos = {d.email.strip().lower() for d in lista}
    for id_, para in conn.execute(
            "SELECT id, recipient FROM notification_outbox WHERE motivo = ? AND version = ? AND status = 'preparado'"
            " ORDER BY id", (MOTIVO, id_semana)).fetchall():
        if para in activos:
            resultado.preparados.setdefault(para, []).append(id_)
    if not resultado.preparados:
        return resultado

    c = contenido(conn, version, ahora, settings.app_base_url)
    titulo, html, texto = componer(c, ahora, settings.app_base_url)
    resultado.asunto = titulo
    if dry_run:
        carpeta = settings.exports_dir / f"resumen_{ahora:%Y%m%d-%H%M%S}"
        carpeta.mkdir(parents=True, exist_ok=True)
        for n, para in enumerate(sorted(resultado.preparados), start=1):
            base = carpeta / f"{n:02d}_{re.sub(r'[^a-z0-9]+', '_', para)}"
            cabecera = f"Para: {para}\nAsunto: {titulo}\n(VISTA PREVIA · dry-run · no se envió)\n\n"
            base.with_suffix(".txt").write_text(cabecera + texto, encoding="utf-8")
            base.with_suffix(".html").write_text(html, encoding="utf-8")
            resultado.vista_previa += [base.with_suffix(".html"), base.with_suffix(".txt")]
        return resultado

    for para, ids in sorted(resultado.preparados.items()):
        _marcar(conn, ids, "incierto", "envío en curso: sin respuesta del proveedor", ahora)
        try:
            id_mensaje = proveedor.enviar(para, titulo, html, texto)
        except EnvioRechazado as exc:
            envio = Envio("fallido", str(exc), 1)
        except EnvioIncierto as exc:
            envio = Envio("incierto", str(exc), 1)
        except Exception as exc:  # cualquier otra cosa: no sabemos si salió
            envio = Envio("incierto", f"error inesperado: {type(exc).__name__}", 1)
        else:
            envio = Envio("aceptado", f"gmail id {id_mensaje}", 1)
        _marcar(conn, ids, envio.estado, envio.detalle, ahora)
        resultado.envios[para] = envio
    return resultado
