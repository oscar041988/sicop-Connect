"""Gestor de documentos, paso 1B: correo al nuevo encargado de un cartel en seguimiento (docs/GESTOR_DOCUMENTOS.md).

* Al asignar o cambiar el encargado (app/seguimiento.py, asignar) queda un aviso «preparado» en la outbox, en la
  misma transacción que la asignación: motivo «asignacion», para el correo del usuario encargado (no tiene que
  estar en «Destinatarios»), version = id de la asignación. Si el administrador se asigna a sí mismo, no.
* Sale con el ciclo diario (8:00), en dry-run o real según el ciclo (decisión de Oscar, 2026-10-26). No depende de
  los datos del día: sale aunque la fuente haya fallado. Un correo por encargado, con todas sus asignaciones.
* Solo se envía lo que sigue vigente: si el cartel cambió de encargado antes del envío, o el usuario se desactivó,
  ese aviso no sale (queda «preparado», igual que un aviso de un cartel vencido). Un cartel ya cerrado sí sale: el
  expediente sigue sirviendo.
* Envío: «incierto» antes de llamar al proveedor; después «aceptado» o «fallido» (nunca se reenvía solo).
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app import panel
from app.avisos import _PLANTILLAS, AvisoError, Envio, Proveedor, _marcar
from app.config import Settings
from app.notifications import EnvioIncierto, EnvioRechazado

MOTIVO = "asignacion"


def dedup_key(encargado: str, nro_sicop: str, asignacion_id: int) -> str:
    return f"{encargado.strip().lower()}|{nro_sicop}|{asignacion_id}|{MOTIVO}"


def preparar(conn: sqlite3.Connection, nro_sicop: str, asignacion_id: int, encargado_id: int, encargado_email: str,
             quien_id: int | None, ahora: datetime) -> bool:
    """Deja el aviso «preparado». Va dentro de la transacción de la asignación: no abre otra.
    Devuelve False si no hace falta (el administrador se asignó a sí mismo) o si ya estaba."""
    if quien_id == encargado_id:
        return False
    cierre = conn.execute("SELECT fecha_cierre_recepcion FROM tenders WHERE nro_sicop = ?", (nro_sicop,)).fetchone()
    para = encargado_email.strip().lower()
    cursor = conn.execute(
        "INSERT OR IGNORE INTO notification_outbox (dedup_key, recipient, nro_sicop, version, motivo, cierre,"
        " rules_version, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'preparado', ?)",
        (dedup_key(para, nro_sicop, asignacion_id), para, nro_sicop, str(asignacion_id), MOTIVO,
         cierre[0] if cierre else None, panel.version_vigente(conn) or "sin_evaluar",
         ahora.isoformat(timespec="seconds")))
    return bool(cursor.rowcount)


@dataclass
class Asignado:
    """Lo que el correo dice de un cartel asignado."""
    nro_sicop: str
    titulo: str | None
    institucion: str
    cierre: str | None
    regresiva: str
    asignado_por: str
    asignado_en: str
    antes: str | None        # encargado anterior; None = estaba sin encargado
    enlace: str
    outbox_id: int


# Avisos «preparado» de asignación que siguen vigentes: la asignación es la última de su seguimiento y el usuario
# sigue activo con ese mismo correo.
_VIGENTES = """
SELECT o.id, o.recipient, o.nro_sicop, t.descripcion,
       coalesce(i.nombre, 'Institución ' || coalesce(t.institution_cedula, 'sin cédula')), t.fecha_cierre_recepcion, a.asignado_por_nombre, a.created_at,
       (SELECT b.encargado_nombre FROM seguimiento_asignaciones b
         WHERE b.seguimiento_id = a.seguimiento_id AND b.id < a.id ORDER BY b.id DESC LIMIT 1)
FROM notification_outbox o
JOIN seguimiento_asignaciones a ON a.id = CAST(o.version AS INTEGER)
JOIN users u ON u.id = a.encargado_id AND u.active = 1 AND lower(u.email) = o.recipient
JOIN tenders t ON t.nro_sicop = o.nro_sicop
LEFT JOIN institutions i ON i.cedula = t.institution_cedula
WHERE o.motivo = 'asignacion' AND o.status = 'preparado'
  AND a.id = (SELECT max(id) FROM seguimiento_asignaciones WHERE seguimiento_id = a.seguimiento_id)
ORDER BY o.id
"""


def pendientes(conn: sqlite3.Connection, ahora: datetime, base_url: str) -> dict[str, list[Asignado]]:
    """Por encargado, los avisos de asignación que se enviarían ahora."""
    por_encargado: dict[str, list[Asignado]] = {}
    for id_, para, nro, titulo, institucion, cierre, por, en, antes in conn.execute(_VIGENTES).fetchall():
        por_encargado.setdefault(para, []).append(Asignado(
            nro, titulo, institucion, cierre, panel.cuenta_regresiva(cierre, ahora), por, en, antes,
            f"{base_url}/seguimiento/{nro}", id_))
    return por_encargado


def asunto(asignados: list[Asignado]) -> str:
    if len(asignados) == 1:
        return f"SICOP · Te asignaron el cartel {asignados[0].nro_sicop} en seguimiento"
    return f"SICOP · Te asignaron {len(asignados)} carteles en seguimiento"


def componer(asignados: list[Asignado], ahora: datetime, base_url: str) -> tuple[str, str, str]:
    """(asunto, html, texto plano) del correo para un encargado."""
    contexto = {"asignados": asignados, "ahora": ahora.isoformat(timespec="seconds"), "panel": base_url,
                "asunto": asunto(asignados)}
    return (contexto["asunto"], _PLANTILLAS.get_template("encargado.html").render(contexto),
            _PLANTILLAS.get_template("encargado.txt").render(contexto))


@dataclass
class Resultado:
    preparados: dict[str, list[Asignado]] = field(default_factory=dict)  # lo que se envía (o se enviaría)
    vista_previa: list[Path] = field(default_factory=list)
    envios: dict[str, Envio] = field(default_factory=dict)              # solo con envío real


def notify(conn: sqlite3.Connection, settings: Settings, ahora: datetime, dry_run: bool = True,
           proveedor: Proveedor | None = None) -> Resultado:
    """Con dry_run escribe la vista previa en EXPORTS_DIR; sin dry_run envía un correo por encargado."""
    if not dry_run and proveedor is None:
        raise AvisoError("Falta el proveedor de correo para el envío real.")
    resultado = Resultado(pendientes(conn, ahora, settings.app_base_url))
    if not resultado.preparados:
        return resultado
    if dry_run:
        carpeta = settings.exports_dir / f"encargados_{ahora:%Y%m%d-%H%M%S}"
        carpeta.mkdir(parents=True, exist_ok=True)
        for n, (para, asignados) in enumerate(sorted(resultado.preparados.items()), start=1):
            titulo, html, texto = componer(asignados, ahora, settings.app_base_url)
            base = carpeta / f"{n:02d}_{re.sub(r'[^a-z0-9]+', '_', para)}"
            cabecera = f"Para: {para}\nAsunto: {titulo}\n(VISTA PREVIA · dry-run · no se envió)\n\n"
            base.with_suffix(".txt").write_text(cabecera + texto, encoding="utf-8")
            base.with_suffix(".html").write_text(html, encoding="utf-8")
            resultado.vista_previa += [base.with_suffix(".html"), base.with_suffix(".txt")]
        return resultado

    for para, asignados in sorted(resultado.preparados.items()):
        ids = [a.outbox_id for a in asignados]
        titulo, html, texto = componer(asignados, ahora, settings.app_base_url)
        _marcar(conn, ids, "incierto", "envío en curso: sin respuesta del proveedor", ahora)
        try:
            id_mensaje = proveedor.enviar(para, titulo, html, texto)
        except EnvioRechazado as exc:
            envio = Envio("fallido", str(exc), len(asignados))
        except EnvioIncierto as exc:
            envio = Envio("incierto", str(exc), len(asignados))
        except Exception as exc:  # cualquier otra cosa: no sabemos si salió
            envio = Envio("incierto", f"error inesperado: {type(exc).__name__}", len(asignados))
        else:
            envio = Envio("aceptado", f"gmail id {id_mensaje}", len(asignados))
        _marcar(conn, ids, envio.estado, envio.detalle, ahora)
        resultado.envios[para] = envio
    return resultado
