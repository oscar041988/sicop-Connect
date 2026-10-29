"""Avisos por correo (lección 7): qué oportunidades avisar, a quién, sin repetir.

Qué se avisa: carteles con prioridad Alta o Media (última evaluación), con el plazo no vencido, cuya versión
actual se vio por primera vez en los últimos NOTIFY_LOOKBACK_DAYS días. El motivo, por destinatario:
* nueva: nunca se le avisó ese cartel.
* cambio_plazo: el cartel cambió y trae otra fecha de cierre que la avisada.
* nueva_version: el cartel cambió (enmienda), con el mismo cierre.
Si la versión es la misma que ya se le avisó, no se vuelve a avisar.

Cierre próximo (A4): además, un cartel cuya última revisión es «Interesa» o «Revisar requisitos» (sin decisión
final: «Ofertada» o «No se oferta») y que cierra en NOTIFY_CLOSING_DAYS días o menos recibe el motivo
cierre_proximo, aunque su prioridad no sea Alta o Media (lo marcó una persona). Una vez por versión del cartel.
El resumen semanal del lunes está en app/resumen.py; usa la misma outbox con su propio motivo.

La «versión» es el content_hash del cartel; cuándo se vio por primera vez sale de raw_snapshots (cada versión
queda ahí con su fecha, y la de una versión repetida no cambia).

Cada aviso es una fila de notification_outbox con dedup_key = destinatario|Número SICOP|versión|motivo (UNIQUE).
Dry-run: prepara los avisos (estado «preparado») y escribe la vista previa en EXPORTS_DIR; NUNCA llama al
proveedor ni marca nada como enviado. Repetirlo no agrega avisos.

Envío (encargo B): un resumen por destinatario con todo lo «preparado» que no haya vencido. Antes de llamar al
proveedor, sus avisos pasan a «incierto»; con la respuesta quedan «aceptado» o «fallido». Si el programa se cae a
mitad del envío, quedan «incierto» y no se reenvían solos. Solo se envía lo «preparado»: lo fallido o incierto
se revisa a mano.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import destinatarios, panel
from app.config import Settings
from app.database import transaccion
from app.matching.evaluar import plazo_estado
from app.notifications import EnvioIncierto, EnvioRechazado

MOTIVOS = {"nueva": "Nueva", "cambio_plazo": "Cambió el plazo", "nueva_version": "Cambió el cartel",
           "cierre_proximo": "Cierra pronto y sigue sin decisión final"}
MOTIVOS_DE_VERSION = ("nueva", "nueva_version", "cambio_plazo")  # los que siguen las versiones del cartel
ESTADOS = ("preparado", "aceptado", "fallido", "incierto")
MAX_FRASES = 6  # evidencia: frases que coincidieron, las primeras

_PLANTILLAS = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "web" / "templates" / "correo"),
    autoescape=select_autoescape(["html"]),  # el .txt va sin escapar: es texto plano
    trim_blocks=True, lstrip_blocks=True,
)
_PLANTILLAS.filters.update(fecha=panel.fecha_cr, titulo=panel.formato_titulo, legible=panel.legible,
                          fecha_dia=lambda d: d.strftime("%d/%m/%Y"))


class AvisoError(Exception):
    """No se puede preparar el aviso; el mensaje es el que verá la persona."""


class Proveedor(Protocol):
    """Quien entrega el correo (app/notifications/gmail.py). El dry-run nunca lo usa.

    enviar() devuelve el id del mensaje si el proveedor lo aceptó; lanza EnvioRechazado si dijo que no y
    EnvioIncierto si no hubo respuesta clara. Cualquier otro error también cuenta como incierto."""

    def enviar(self, para: str, asunto: str, html: str, texto: str) -> str: ...


@dataclass
class Oportunidad:
    """Lo que el correo dice de un cartel."""
    nro_sicop: str
    motivo: str
    titulo: str | None
    institucion: str
    encaje: str              # alta · media (la mejor de sus familias)
    familias: list[str]
    cierre: str | None
    plazo: str
    regresiva: str
    frases: list[str]
    enlace: str
    # Filas de la outbox que cubre (más de una si el cartel cambió otra vez antes de enviarse).
    outbox_ids: list[int] = field(default_factory=list)


@dataclass
class Envio:
    """Cómo terminó el correo de un destinatario."""
    estado: str              # aceptado · fallido · incierto
    detalle: str             # id de Gmail o lo que pasó (nunca credenciales)
    avisos: int              # oportunidades que llevaba


@dataclass
class Resultado:
    version_reglas: str
    destinatarios: int
    nuevos: int = 0          # avisos agregados a la outbox en esta corrida (todos los motivos)
    por_cerrar: int = 0      # de ellos, de cierre próximo
    ya_avisados: int = 0     # candidatos que ya tenían su aviso para esa versión: no se repiten
    # Por destinatario, todo lo que está «preparado»: exactamente lo que enviaría --send.
    preparados: dict[str, list[Oportunidad]] = field(default_factory=dict)
    vista_previa: list[Path] = field(default_factory=list)
    envios: dict[str, Envio] = field(default_factory=dict)  # solo con envío real


def dedup_key(destinatario: str, nro_sicop: str, version: str, motivo: str) -> str:
    return f"{destinatario.strip().lower()}|{nro_sicop}|{version}|{motivo}"


def candidatos(conn: sqlite3.Connection, version_reglas: str, ahora: datetime, dias: int) -> list[tuple[str, str, str | None]]:
    """(Número SICOP, versión, cierre) de los carteles que se pueden avisar hoy."""
    filas = conn.execute(
        "SELECT t.nro_sicop, t.content_hash, t.fecha_cierre_recepcion FROM tenders t"
        " JOIN raw_snapshots s ON s.entity = 'cartel' AND s.natural_key = t.nro_sicop"
        "                     AND s.content_hash = t.content_hash"
        " WHERE julianday(s.captured_at) >= julianday(:desde)"
        "   AND EXISTS (SELECT 1 FROM opportunity_assessments a WHERE a.nro_sicop = t.nro_sicop"
        "               AND a.rules_version = :version AND a.encaje IN ('alta', 'media'))"
        " ORDER BY t.fecha_cierre_recepcion, t.nro_sicop",
        {"desde": (ahora - timedelta(days=dias)).isoformat(timespec="seconds"), "version": version_reglas},
    ).fetchall()
    return [f for f in filas if plazo_estado(f[2], ahora) != "vencido"]


def motivo_para(conn: sqlite3.Connection, destinatario: str, nro_sicop: str, version: str,
                cierre: str | None) -> str | None:
    """Por qué avisarle ahora a ese destinatario, o None si ya se le avisó esta versión."""
    # Solo cuentan los avisos de versión: un aviso de cierre próximo no dice nada de qué versión se avisó.
    ultimo = conn.execute(
        "SELECT version, cierre FROM notification_outbox WHERE recipient = ? AND nro_sicop = ?"
        f" AND motivo IN ({', '.join('?' * len(MOTIVOS_DE_VERSION))}) ORDER BY id DESC LIMIT 1",
        (destinatario.strip().lower(), nro_sicop, *MOTIVOS_DE_VERSION)).fetchone()
    if ultimo is None:
        return "nueva"
    if ultimo[0] == version:
        return None
    return "cambio_plazo" if ultimo[1] != cierre else "nueva_version"


def por_cerrar(conn: sqlite3.Connection, ahora: datetime, dias: int) -> list[tuple[str, str, str]]:
    """(Número SICOP, versión, cierre) de los carteles en curso (última revisión «Interesa» o «Revisar
    requisitos») que cierran en `dias` días o menos y todavía no cerraron."""
    filas = conn.execute(
        "SELECT t.nro_sicop, t.content_hash, t.fecha_cierre_recepcion FROM tenders t"
        " JOIN reviews r ON r.id = (SELECT max(id) FROM reviews WHERE nro_sicop = t.nro_sicop)"
        f" WHERE r.decision IN ({', '.join('?' * len(panel.DECISIONES_EN_CURSO))})"
        " ORDER BY t.fecha_cierre_recepcion, t.nro_sicop", panel.DECISIONES_EN_CURSO).fetchall()
    resultado = []
    for nro, version, cierre in filas:
        if plazo_estado(cierre, ahora) in ("vencido", "por_verificar"):
            continue  # sin fecha legible no se puede decir que cierra pronto
        if datetime.fromisoformat(cierre) - ahora <= timedelta(days=dias):
            resultado.append((nro, version, cierre))
    return resultado


def preparar(conn: sqlite3.Connection, version_reglas: str, ahora: datetime, dias: int,
             dias_cierre: int | None = None) -> Resultado:
    """Agrega a la outbox («preparado») los avisos que faltan. Repetible: lo ya preparado no se duplica.

    dias: NOTIFY_LOOKBACK_DAYS (0 = no preparar los avisos de versión).
    dias_cierre: con un número, también prepara los de cierre próximo (NOTIFY_CLOSING_DAYS)."""
    lista = destinatarios.activos(conn)
    resultado = Resultado(version_reglas, len(lista))
    momento = ahora.isoformat(timespec="seconds")
    with transaccion(conn):
        for nro, version, cierre in (candidatos(conn, version_reglas, ahora, dias) if dias else []):
            for d in lista:
                para = d.email.strip().lower()
                motivo = motivo_para(conn, para, nro, version, cierre)
                if motivo is None:
                    resultado.ya_avisados += 1
                    continue
                # INSERT OR IGNORE: aunque algo fallara arriba, la clave UNIQUE impide un aviso repetido.
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO notification_outbox (dedup_key, recipient, nro_sicop, version, motivo,"
                    " cierre, rules_version, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'preparado', ?)",
                    (dedup_key(para, nro, version, motivo), para, nro, version, motivo, cierre, version_reglas, momento))
                resultado.nuevos += cursor.rowcount
        for nro, version, cierre in (por_cerrar(conn, ahora, dias_cierre) if dias_cierre else []):
            for d in lista:
                para = d.email.strip().lower()
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO notification_outbox (dedup_key, recipient, nro_sicop, version, motivo,"
                    " cierre, rules_version, status, created_at) VALUES (?, ?, ?, ?, 'cierre_proximo', ?, ?, 'preparado', ?)",
                    (dedup_key(para, nro, version, "cierre_proximo"), para, nro, version, cierre, version_reglas, momento))
                resultado.nuevos += cursor.rowcount
                resultado.por_cerrar += cursor.rowcount
    return resultado


def _oportunidad(conn: sqlite3.Connection, nro_sicop: str, motivo: str, version_reglas: str, ahora: datetime,
                 base_url: str) -> Oportunidad:
    d = panel.detalle(conn, nro_sicop, version_reglas, ahora)
    candidatas = [e for e in d.evaluaciones if e.encaje in ("alta", "media")]  # ya vienen Alta primero
    # Un cierre próximo puede ser de un cartel Baja que una persona marcó: se muestra su prioridad real.
    con_senal = candidatas or [e for e in d.evaluaciones if e.encaje != "sin_coincidencia"]
    frases: list[str] = []
    for e in candidatas:
        for lista in panel.frases_de_evidencia(e.evidencia).values():
            frases.extend(f for f in lista if f.lower() not in {x.lower() for x in frases})
    c = d.compra
    return Oportunidad(
        nro_sicop=nro_sicop, motivo=motivo, titulo=c.descripcion,
        institucion=c.institucion or f"Institución {c.institution_cedula or 'sin cédula'}",
        encaje=con_senal[0].encaje if con_senal else "sin_coincidencia",
        familias=[panel.NOMBRES_FAMILIA.get(e.familia, e.familia) for e in con_senal],
        cierre=c.fecha_cierre_recepcion, plazo=d.plazo, regresiva=panel.cuenta_regresiva(c.fecha_cierre_recepcion, ahora),
        frases=frases[:MAX_FRASES], enlace=f"{base_url}/oportunidades/{nro_sicop}",
    )


def pendientes(conn: sqlite3.Connection, ahora: datetime, base_url: str,
               motivos: tuple[str, ...] | None = None) -> dict[str, list[Oportunidad]]:
    """Avisos en estado «preparado», por destinatario (solo los que siguen activos): lo que enviaría --send.

    Se saltan los carteles cuyo cierre ya venció (quedan «preparado», sin enviarse). Si un cartel tiene varios
    avisos preparados (cambió otra vez antes de enviarse), va una sola vez, con el motivo del más reciente."""
    activos = {d.email.strip().lower() for d in destinatarios.activos(conn)}
    filas: dict[tuple[str, str], tuple[str, str, list[int]]] = {}
    # El resumen semanal (sin cartel) y el correo al encargado (app/aviso_encargado.py) van aparte.
    for id_, para, nro, motivo, version_reglas in conn.execute(
            "SELECT id, recipient, nro_sicop, motivo, rules_version FROM notification_outbox"
            " WHERE status = 'preparado' AND nro_sicop IS NOT NULL AND motivo != 'asignacion' ORDER BY id").fetchall():
        if para in activos and (motivos is None or motivo in motivos):
            ids = filas.get((para, nro), ("", "", []))[2]
            filas[(para, nro)] = (motivo, version_reglas, [*ids, id_])  # el más reciente manda
    por_destinatario: dict[str, list[Oportunidad]] = {}
    for (para, nro), (motivo, version_reglas, ids) in filas.items():
        o = _oportunidad(conn, nro, motivo, version_reglas, ahora, base_url)
        if plazo_estado(o.cierre, ahora) == "vencido":
            continue
        o.outbox_ids = ids
        por_destinatario.setdefault(para, []).append(o)
    for lista in por_destinatario.values():
        lista.sort(key=lambda o: (o.cierre or "9999", o.nro_sicop))  # cierre más próximo primero
    return por_destinatario


def asunto(oportunidades: list[Oportunidad]) -> str:
    nuevas = sum(o.motivo == "nueva" for o in oportunidades)
    cierran = sum(o.motivo == "cierre_proximo" for o in oportunidades)
    cambios = len(oportunidades) - nuevas - cierran
    partes = [f"{nuevas} nueva{'s' if nuevas != 1 else ''}"] if nuevas else []
    partes += [f"{cambios} con cambios"] if cambios else []
    partes += [f"{cierran} por cerrar sin decisión"] if cierran else []
    total = len(oportunidades)
    return f"SICOP · {total} oportunidad{'es' if total != 1 else ''} para revisar ({', '.join(partes)})"


def componer(oportunidades: list[Oportunidad], ahora: datetime, base_url: str) -> tuple[str, str, str]:
    """(asunto, html, texto plano) del resumen para un destinatario. Saluda «Hola, equipo» (pedido de Oscar)."""
    contexto = {"oportunidades": oportunidades, "ahora": ahora.isoformat(timespec="seconds"),
                "panel": base_url, "ENCAJES": panel.ENCAJES, "PLAZOS": panel.PLAZOS, "MOTIVOS": MOTIVOS,
                "asunto": asunto(oportunidades)}
    return (contexto["asunto"], _PLANTILLAS.get_template("aviso.html").render(contexto),
            _PLANTILLAS.get_template("aviso.txt").render(contexto))


def _escribir_vista_previa(carpeta: Path, por_destinatario: dict[str, list[Oportunidad]], ahora: datetime,
                           base_url: str) -> list[Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    archivos = []
    for n, (para, oportunidades) in enumerate(sorted(por_destinatario.items()), start=1):
        titulo, html, texto = componer(oportunidades, ahora, base_url)
        base = carpeta / f"{n:02d}_{re.sub(r'[^a-z0-9]+', '_', para)}"
        cabecera = f"Para: {para}\nAsunto: {titulo}\n(VISTA PREVIA · dry-run · no se envió)\n\n"
        base.with_suffix(".txt").write_text(cabecera + texto, encoding="utf-8")
        base.with_suffix(".html").write_text(html, encoding="utf-8")
        archivos += [base.with_suffix(".html"), base.with_suffix(".txt")]
    return archivos


def _marcar(conn: sqlite3.Connection, ids: list[int], estado: str, detalle: str, ahora: datetime) -> None:
    with transaccion(conn):
        conn.executemany(
            "UPDATE notification_outbox SET status = ?, detalle = ?, updated_at = ? WHERE id = ?",
            [(estado, detalle, ahora.isoformat(timespec="seconds"), i) for i in ids])


def enviar(conn: sqlite3.Connection, por_destinatario: dict[str, list[Oportunidad]], proveedor: Proveedor,
           ahora: datetime, base_url: str) -> dict[str, Envio]:
    """Un correo por destinatario. Cada uno se marca «incierto» ANTES de llamar al proveedor."""
    envios: dict[str, Envio] = {}
    for para, oportunidades in sorted(por_destinatario.items()):
        ids = [i for o in oportunidades for i in o.outbox_ids]
        titulo, html, texto = componer(oportunidades, ahora, base_url)
        _marcar(conn, ids, "incierto", "envío en curso: sin respuesta del proveedor", ahora)
        try:
            id_mensaje = proveedor.enviar(para, titulo, html, texto)
        except EnvioRechazado as exc:
            envio = Envio("fallido", str(exc), len(oportunidades))
        except EnvioIncierto as exc:
            envio = Envio("incierto", str(exc), len(oportunidades))
        except Exception as exc:  # cualquier otra cosa: no sabemos si salió
            envio = Envio("incierto", f"error inesperado: {type(exc).__name__}", len(oportunidades))
        else:
            envio = Envio("aceptado", f"gmail id {id_mensaje}", len(oportunidades))
        _marcar(conn, ids, envio.estado, envio.detalle, ahora)
        envios[para] = envio
    return envios


def notify(conn: sqlite3.Connection, settings: Settings, ahora: datetime, dry_run: bool = True,
           proveedor: Proveedor | None = None, solo: str | None = None, solo_cierre: bool = False) -> Resultado:
    """Prepara los avisos; con dry_run escribe la vista previa, sin dry_run los envía con el proveedor.

    solo: enviar únicamente a ese destinatario (prueba controlada); los demás siguen «preparado».
    solo_cierre: solo los de cierre próximo. Lo usa el ciclo cuando la fuente falló: el plazo corre igual y este
    aviso no depende de los datos del día; los demás quedan «preparado» para el siguiente ciclo con datos."""
    if not dry_run and proveedor is None:
        raise AvisoError("Falta el proveedor de correo para el envío real.")
    version = panel.version_vigente(conn)
    if version is None:
        raise AvisoError("Todavía no hay evaluaciones: ejecuta python -m app.cli evaluate.")
    if solo is not None:
        solo = solo.strip().lower()
        if solo not in {d.email.strip().lower() for d in destinatarios.activos(conn)}:
            raise AvisoError(f"{solo} no es un destinatario activo: agrégalo en el panel («Destinatarios»).")
    if solo_cierre:
        resultado = preparar(conn, version, ahora, 0, settings.notify_closing_days)
        resultado.preparados = pendientes(conn, ahora, settings.app_base_url, ("cierre_proximo",))
    else:
        resultado = preparar(conn, version, ahora, settings.notify_lookback_days, settings.notify_closing_days)
        resultado.preparados = pendientes(conn, ahora, settings.app_base_url)
    if solo is not None:
        resultado.preparados = {k: v for k, v in resultado.preparados.items() if k == solo}
    if dry_run:
        # Dry-run: el proveedor ni se toca. Nada pasa de «preparado».
        if resultado.preparados:
            carpeta = settings.exports_dir / f"avisos_{ahora:%Y%m%d-%H%M%S}"
            resultado.vista_previa = _escribir_vista_previa(carpeta, resultado.preparados, ahora,
                                                            settings.app_base_url)
        return resultado
    resultado.envios = enviar(conn, resultado.preparados, proveedor, ahora, settings.app_base_url)
    return resultado
