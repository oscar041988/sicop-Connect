"""Revisión a mano de los avisos «fallido» o «incierto» (pendiente de la lección 7). Solo administradores.

Un aviso que falló o quedó en duda nunca se reenvía solo (app/avisos.py). Aquí una persona decide:
* Reintentar: vuelve a «preparado» y sale en el siguiente envío normal (notify --send o el ciclo diario).
  Si estaba «incierto», puede que sí haya salido: antes hay que revisar Gmail › Enviados (se pide confirmarlo).
* Confirmar que sí salió (solo «incierto»): pasa a «aceptado» sin reenviar nada.

No se borra nada: cambia el estado de la fila de la outbox y cada decisión queda en el historial (audit_log),
con el estado y el detalle de antes, porque un envío posterior reemplaza el detalle de la outbox.

El resumen semanal (app/resumen.py) también aparece aquí: no tiene cartel (nro_sicop vacío). Reintentarlo solo
sirve en su misma semana; sale con el siguiente envío del resumen (notify --resumen-semanal --send).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app import destinatarios, historial, resumen
from app.database import transaccion
from app.historial import TERMINAL, Quien
from app.matching.evaluar import plazo_estado

POR_REVISAR = ("fallido", "incierto")


class AvisoInvalido(ValueError):
    """No se puede hacer el cambio; el mensaje es el que verá la persona."""


@dataclass
class AvisoPorRevisar:
    id: int
    para: str
    nro_sicop: str | None    # None: es el resumen semanal
    titulo: str | None
    motivo: str
    estado: str              # fallido · incierto
    detalle: str | None      # lo que respondió el proveedor (nunca credenciales)
    creado: str
    actualizado: str | None
    cierre: str | None
    vencido: bool            # el cartel ya cerró (o el resumen es de otra semana): aunque se prepare, no se enviaría
    destinatario_activo: bool
    superado: bool           # a ese destinatario ya le llegó una versión más nueva del cartel
    semana: str | None = None  # solo el resumen semanal: «2026-W43»

    @property
    def es_resumen(self) -> bool:
        return self.nro_sicop is None

    @property
    def que(self) -> str:
        """«cartel 20261000001» o «resumen semanal 2026-W43», para los mensajes y el historial."""
        return f"resumen semanal {self.semana}" if self.es_resumen else f"cartel {self.nro_sicop}"


def _filas(conn: sqlite3.Connection, condicion: str, parametros: tuple) -> list[tuple]:
    return conn.execute(
        "SELECT o.id, o.recipient, o.nro_sicop, t.descripcion, o.motivo, o.status, o.detalle, o.created_at,"
        "       o.updated_at, o.cierre, o.version,"
        "       EXISTS (SELECT 1 FROM notification_outbox n WHERE n.recipient = o.recipient"
        "               AND n.nro_sicop = o.nro_sicop AND n.id > o.id AND n.status = 'aceptado')"
        " FROM notification_outbox o LEFT JOIN tenders t ON t.nro_sicop = o.nro_sicop"  # el resumen no tiene cartel
        f" WHERE {condicion} ORDER BY o.id DESC", parametros).fetchall()


def _aviso(fila: tuple, activos: set[str], ahora: datetime) -> AvisoPorRevisar:
    id_, para, nro, titulo, motivo, estado, detalle, creado, actualizado, cierre, version, superado = fila
    if nro is None:  # resumen semanal: solo vale en su semana (app/resumen.py solo envía el de la semana actual)
        return AvisoPorRevisar(id_, para, None, f"Resumen semanal {version}", motivo, estado, detalle, creado,
                               actualizado, None, version != resumen.semana(ahora)[0], para in activos, False,
                               semana=version)
    return AvisoPorRevisar(id_, para, nro, titulo, motivo, estado, detalle, creado, actualizado, cierre,
                           plazo_estado(cierre, ahora) == "vencido", para in activos, bool(superado))


def _activos(conn: sqlite3.Connection) -> set[str]:
    return {d.email.strip().lower() for d in destinatarios.activos(conn)}


def por_revisar(conn: sqlite3.Connection, ahora: datetime) -> list[AvisoPorRevisar]:
    """Los avisos «fallido» o «incierto», del más reciente al más viejo."""
    activos = _activos(conn)
    return [_aviso(f, activos, ahora) for f in _filas(conn, "o.status IN ('fallido', 'incierto')", ())]


def _buscar(conn: sqlite3.Connection, outbox_id: int, ahora: datetime) -> AvisoPorRevisar:
    filas = _filas(conn, "o.id = ?", (outbox_id,))
    if not filas:
        raise AvisoInvalido("Ese aviso no existe.")
    aviso = _aviso(filas[0], _activos(conn), ahora)
    if aviso.estado not in POR_REVISAR:
        raise AvisoInvalido(f"Ese aviso ya no está fallido ni incierto (ahora: {aviso.estado}).")
    return aviso


def _cambiar(conn: sqlite3.Connection, aviso: AvisoPorRevisar, estado: str, detalle: str, quien: Quien,
             accion: str, ahora: datetime) -> None:
    with transaccion(conn):  # el cambio y su línea del historial, juntos
        # «AND status = ?»: si otra persona lo cambió entre la página y el clic, no se pisa su decisión.
        cursor = conn.execute(
            "UPDATE notification_outbox SET status = ?, detalle = ?, updated_at = ? WHERE id = ? AND status = ?",
            (estado, detalle, ahora.astimezone(timezone.utc).isoformat(timespec="seconds"), aviso.id, aviso.estado))
        if cursor.rowcount != 1:
            raise AvisoInvalido("Otra persona cambió este aviso hace un momento: recarga la página.")
        historial.registrar(conn, quien, accion, f"{aviso.para} · {aviso.que} · antes {aviso.estado}:"
                                                 f" {aviso.detalle or 'sin detalle'}")


def reintentar(conn: sqlite3.Connection, outbox_id: int, ahora: datetime, quien: Quien = TERMINAL,
               revise_enviados: bool = False) -> AvisoPorRevisar:
    """Vuelve a «preparado» un aviso fallido o incierto: sale en el siguiente envío normal."""
    aviso = _buscar(conn, outbox_id, ahora)
    if aviso.estado == "incierto" and not revise_enviados:
        raise AvisoInvalido("Este aviso pudo haber salido. Revisa en Gmail › Enviados que no esté y marca la"
                            " casilla para reintentarlo; si sí salió, usa «Sí salió».")
    if aviso.superado:
        raise AvisoInvalido(f"A {aviso.para} ya le llegó una versión más nueva de este cartel: no hace falta"
                            " reenviarlo.")
    if aviso.vencido and aviso.es_resumen:
        raise AvisoInvalido(f"El resumen semanal {aviso.semana} es de otra semana: ya no se envía.")
    if aviso.vencido:
        raise AvisoInvalido(f"El cartel {aviso.nro_sicop} ya cerró: aunque se prepare, no se enviaría.")
    if not aviso.destinatario_activo:
        raise AvisoInvalido(f"{aviso.para} ya no recibe avisos: vuelve a agregarlo en «Destinatarios» antes de"
                            " reintentar.")
    _cambiar(conn, aviso, "preparado", f"reintento pedido por {quien.nombre}", quien, "reintentar_aviso", ahora)
    return aviso


def confirmar_salida(conn: sqlite3.Connection, outbox_id: int, ahora: datetime,
                     quien: Quien = TERMINAL) -> AvisoPorRevisar:
    """Un aviso incierto que sí está en Gmail › Enviados pasa a «aceptado», sin reenviar nada."""
    aviso = _buscar(conn, outbox_id, ahora)
    if aviso.estado != "incierto":
        raise AvisoInvalido("Solo un aviso incierto se puede confirmar: uno fallido fue rechazado por Gmail.")
    _cambiar(conn, aviso, "aceptado", f"confirmado a mano por {quien.nombre}: sí salió (está en Enviados)",
             quien, "confirmar_aviso", ahora)
    return aviso
