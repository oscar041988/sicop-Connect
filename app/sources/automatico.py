"""Obtención automática (lección 4): una «vuelta» de obtain auto.

La tarea programada llama a obtain auto cada 15 minutos (06:00–19:45, lunes a viernes). Cada vuelta:
1. Con SOURCE_MODE=manual no hace nada: no abre SICOP ni lee Gmail.
2. Cada hora de OBTAIN_REQUEST_HOUR es un turno (06:30 y 14:00: dos por día, 2026-10-26). Si el turno vigente
   no tiene solicitud, pide el reporte (obtain request). Una por turno: si la del turno falló, no se pide otra
   hasta el turno siguiente (regla 4 de DECISION_OBTENCION.md §8). Si al pedir sigue abierta la del turno anterior,
   esa se cierra «fallido» (su enlace no llegó a tiempo) y manda su alerta.
3. Si hay una solicitud abierta, revisa el buzón una vez (obtain poll). Con OBTAIN_DOWNLOAD=manual (por defecto),
   al llegar el enlace la solicitud queda «enlace_recibido» y no se descarga nada; con auto: descarga → validación
   → la copia a INCOMING_DIR.
4. Correos a OBTAIN_ALERT_TO, uno por solicitud y nunca con el enlace, el código ni el processId (regla 7):
   - «enlace_recibido»: el RECORDATORIO de descargar el ZIP y subirlo en «Cargar archivo».
   - «fallido»: la ALERTA con el motivo y el plan B (descargar a mano con el correo «Envío de reporte»).
   Mientras los avisos estén en dry-run, solo se escribe la vista previa.
La vuelta NO corre el ciclo ni manda avisos de oportunidades (Ivania, 2026-10-26): el ZIP se importa y evalúa al
subirlo en el panel, y el correo de avisos sale una vez al día, a las 8:00, con el ciclo (sicop-cycle.timer).
Un bloqueo propio impide dos vueltas a la vez. Ningún fallo es silencioso: cada paso deja su línea en el resultado.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.bloqueo import CicloOcupado, bloqueo
from app.config import Settings
from app.database import connect
from app.importers.comun import HORA_CR
from app.notifications import EnvioRechazado
from app.sources import obtencion, sicop_browser
from app.sources.gmail_reader import GmailError
from app.sources.sicop_browser import FalloObtencion, YaSolicitadoHoy

__all__ = ["Vuelta", "vuelta", "ruta_bloqueo"]


@dataclass
class Vuelta:
    """Qué hizo una vuelta, para la salida del comando y el registro de la tarea."""
    lineas: list[str] = field(default_factory=list)
    fallo: bool = False      # algo falló en esta vuelta (la salida del comando es 1)

    def nota(self, texto: str, fallo: bool = False) -> None:
        self.lineas.append(("FALLO · " if fallo else "") + texto)
        self.fallo = self.fallo or fallo


def ruta_bloqueo(settings: Settings) -> Path:
    return settings.database_path.parent / "obtain-auto.lock"


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def vuelta(settings: Settings, *, crear_lector: Callable, proveedor_alerta: Callable | None = None,
           reloj: Callable[[], datetime] = _ahora, solicitar: Callable = sicop_browser.solicitar_reporte,
           sondear: Callable = obtencion.sondear) -> Vuelta:
    """Una vuelta de obtain auto. Lanza CicloOcupado si otra vuelta está en curso.

    crear_lector y proveedor_alerta se llaman solo si hacen falta: en modo manual no se toca Gmail. Las pruebas
    pasan versiones SIMULADAS de todo lo que sale de la computadora."""
    v = Vuelta()
    if settings.source_mode != "auto":
        v.nota("SOURCE_MODE=manual: obtain auto no hace nada (no se abrió SICOP ni se leyó Gmail).")
        return v
    ahora = reloj()
    with bloqueo(ruta_bloqueo(settings), f"obtain auto · {ahora:%Y-%m-%d %H:%M:%S} · proceso {os.getpid()}"):
        _obtener(settings, v, ahora, crear_lector, solicitar, sondear, reloj)
        _alertar(settings, v, reloj, proveedor_alerta)
    return v


# --- 2 y 3: pedir y sondear --------------------------------------------------------------------------------

def _solicitud_del_turno(settings: Settings, hoy: str, turno: str) -> sqlite3.Row | None:
    with closing(connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT id, estado FROM solicitudes_sicop WHERE substr(solicitada_en, 1, 10) = ?"
                            " AND turno = ? ORDER BY id DESC LIMIT 1", (hoy, turno)).fetchone()


def _cerrar_anteriores(settings: Settings, turno: str, reloj) -> list[int]:
    """Antes de pedir el reporte de un turno, la solicitud que siga abierta de antes se cierra «fallido»: su enlace
    no llegó a tiempo y el sondeo solo sigue la más reciente. Manda su alerta normal (con el plan B)."""
    marcas = ", ".join("?" for _ in obtencion.ABIERTOS)
    with closing(connect(settings.database_path)) as conn:
        ids = [i for (i,) in conn.execute(f"SELECT id FROM solicitudes_sicop WHERE estado IN ({marcas})",
                                          obtencion.ABIERTOS)]
        for i in ids:
            conn.execute("UPDATE solicitudes_sicop SET estado = 'fallido', motivo = ?, terminada_en = ? WHERE id = ?",
                         (f"El correo con el enlace no llegó antes de la solicitud de las {turno}; la nueva la "
                          "reemplaza. Si llega tarde, se puede descargar igual.",
                          reloj().isoformat(timespec="seconds"), i))
    return ids


def _hay_abierta(settings: Settings) -> bool:
    with closing(connect(settings.database_path)) as conn:
        return conn.execute("SELECT 1 FROM solicitudes_sicop WHERE estado IN (?, ?, ?, ?) LIMIT 1",
                            obtencion.ABIERTOS).fetchone() is not None


def _obtener(settings, v: Vuelta, ahora: datetime, crear_lector, solicitar, sondear, reloj) -> None:
    horas = settings.obtain_request_hours
    turno = sicop_browser.turno_de(settings, ahora)
    actual = _solicitud_del_turno(settings, ahora.date().isoformat(), turno)
    pedir = actual is None and ahora.time() >= horas[0]
    if actual is None and not pedir:
        v.nota(f"Todavía no es hora de pedir el reporte (desde las {horas[0]:%H:%M}).")
    elif actual is not None and actual["estado"] == "validado":
        v.nota(f"La solicitud del turno de las {turno} (#{actual['id']}) ya está validada.")
    elif actual is not None and actual["estado"] == "enlace_recibido":
        v.nota(f"La solicitud del turno de las {turno} (#{actual['id']}) ya tiene su enlace: la descarga es a mano.")
    elif actual is not None and actual["estado"] == "fallido":
        v.nota(f"La solicitud del turno de las {turno} (#{actual['id']}) falló: no se pide otra en este turno (una "
               "por turno). Ver la alerta.")
    if not pedir and not _hay_abierta(settings):
        return
    try:
        lector = crear_lector(settings)
    except GmailError as exc:
        v.nota(f"No se pudo abrir Gmail: {exc} No se pidió ni revisó nada.", fallo=True)
        return
    if pedir:
        for anterior in _cerrar_anteriores(settings, turno, reloj):
            v.nota(f"La solicitud #{anterior} seguía esperando el enlace: se cerró al pedir la del turno de las "
                   f"{turno} (se manda su alerta).", fallo=True)
        try:
            r = solicitar(settings, lector)
        except YaSolicitadoHoy as exc:
            v.nota(str(exc))
        except FalloObtencion as exc:  # solicitar_reporte ya la dejó «fallido» en la base
            v.nota(f"Solicitud a SICOP: {exc.motivo}", fallo=True)
            return
        else:
            v.nota(f"Solicitud #{r.solicitud_id} (turno de las {turno}) hecha: SICOP mostró «Procesando el reporte».")
    try:
        r = sondear(settings, lector, reloj=reloj)
    except CicloOcupado:
        v.nota("Hay un obtain poll en curso (¿a mano?): esta vuelta no revisó el buzón.")
    except GmailError as exc:
        v.nota(f"Error de Gmail: {exc} La solicitud sigue abierta; se revisa en la próxima vuelta.", fallo=True)
    except FalloObtencion as exc:
        v.nota(exc.motivo, fallo=True)
    else:
        v.nota(r.mensaje, fallo=r.fallo)


# --- 4: alerta de FALLO ------------------------------------------------------------------------------------

def texto_alerta(settings: Settings, fila: sqlite3.Row) -> tuple[str, str]:
    """(asunto, cuerpo) de la alerta. Sin enlace, código ni processId: solo el motivo y qué hacer."""
    llego_enlace = fila["enlace_recibido_en"] is not None
    pasos = ([f"1. Abre en {settings.sicop_request_email or 'el buzón de SICOP'} el correo de info@sicop.go.cr "
              "«Envío de reporte» de hoy.",
              "2. Haz clic en el enlace y guarda el ZIP (tarda unos segundos)."]
             if llego_enlace else
             ["1. El reporte no llegó a pedirse o su correo no llegó: no se pide otro automáticamente hoy.",
              "2. Si hace falta, pídelo a mano en SICOP (modo asistido, docs/OPERACION.md) y descarga el ZIP."])
    pasos.append(f"3. Deja el ZIP en la carpeta de entrada ({settings.incoming_dir}): la próxima vuelta de "
                 "obtain auto (cada 15 min) lo importa, evalúa y prepara los avisos.")
    cuerpo = "\n".join([
        "SICOP CONNECT · la obtención automática de hoy FALLÓ.",
        "",
        f"Solicitud #{fila['id']}, pedida el {fila['solicitada_en'][:16].replace('T', ' a las ')}.",
        f"Motivo: {fila['motivo'] or 'sin detalle'}",
        *([f"Captura: {fila['captura']}"] if fila["captura"] else []),
        "",
        "Plan B (descarga en modo asistido):",
        *pasos,
        "",
        "No respondas este correo. Detalle: python -m app.cli obtain status.",
    ])
    return f"SICOP CONNECT · FALLO en la obtención (solicitud #{fila['id']})", cuerpo


def texto_recordatorio(settings: Settings, fila: sqlite3.Row) -> tuple[str, str]:
    """(asunto, cuerpo) del recordatorio cuando llegó el enlace y la descarga es a mano. Sin enlace ni processId."""
    turno = f"de las {fila['turno']}" if fila["turno"] else f"#{fila['id']}"
    llegada = (fila["enlace_recibido_en"] or "")[11:16]
    panel = settings.app_base_url.rstrip("/") + "/cargar"
    cuerpo = "\n".join([
        f"SICOP CONNECT · ya llegó el reporte {turno} (correo de SICOP de las {llegada}).",
        "",
        "Para que entre al panel y salgan los avisos:",
        f"1. Abre en {settings.sicop_request_email or 'el buzón de SICOP'} el correo de info@sicop.go.cr «Envío de "
        "reporte» más reciente.",
        "2. Toca «URL de descarga» y guarda el ZIP. No lo abras ni lo descomprimas.",
        f"3. Súbelo en el panel, «Cargar archivo» ({panel}): tipo «pliegos», origen «real».",
        "",
        "Al subirlo, la app lo importa y lo evalúa enseguida: los carteles nuevos se ven en el panel. El correo de",
        "avisos sale a las 8:00 (lunes a viernes) con todo lo subido hasta esa hora.",
        "Hazlo hoy: el enlace de SICOP vence (se vio uno vencido a las 16 h).",
        "",
        "No respondas este correo.",
    ])
    return f"SICOP CONNECT · descargar el reporte {turno} (solicitud #{fila['id']})", cuerpo


def _alertar(settings: Settings, v: Vuelta, reloj, proveedor_alerta) -> None:
    with closing(connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute("SELECT * FROM solicitudes_sicop WHERE estado IN ('fallido', 'enlace_recibido')"
                             " AND alerta_estado IS NULL ORDER BY id").fetchall()
        for fila in filas:
            recordatorio = fila["estado"] == "enlace_recibido"
            asunto, cuerpo = (texto_recordatorio if recordatorio else texto_alerta)(settings, fila)
            que = "Recordatorio" if recordatorio else "Alerta"
            real = settings.notifications_enabled and not settings.notifications_dry_run and settings.obtain_alert_to
            if not real or proveedor_alerta is None:
                ruta = settings.exports_dir / f"{que.lower()}-obtencion-{fila['id']}.txt"
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text(f"Para: {settings.obtain_alert_to or '(falta OBTAIN_ALERT_TO)'}\n"
                                f"Asunto: {asunto}\n\n{cuerpo}\n", encoding="utf-8")
                _marcar(conn, fila["id"], "vista_previa", reloj)
                v.nota(f"{que} de la solicitud #{fila['id']}: vista previa en {ruta} (avisos en dry-run, no se envió).")
                continue
            _marcar(conn, fila["id"], "incierta", reloj)  # antes de llamar a Gmail: si se cae, no se reenvía sola
            try:
                proveedor_alerta(settings).enviar(settings.obtain_alert_to, asunto, f"<pre>{_html(cuerpo)}</pre>",
                                                  cuerpo)
            except EnvioRechazado as exc:
                _marcar(conn, fila["id"], "fallida", reloj)
                v.nota(f"{que} de la solicitud #{fila['id']}: Gmail la rechazó ({exc}).", fallo=True)
            except Exception as exc:  # noqa: BLE001 — EnvioIncierto o cualquier otro: queda incierta
                v.nota(f"{que} de la solicitud #{fila['id']}: sin respuesta clara de Gmail ({type(exc).__name__}). "
                       "Revisar Gmail › Enviados; no se reenvía sola.", fallo=True)
            else:
                _marcar(conn, fila["id"], "aceptada", reloj)
                v.nota(f"{que} de la solicitud #{fila['id']} enviado a {settings.obtain_alert_to}.")


def _marcar(conn: sqlite3.Connection, solicitud_id: int, estado: str, reloj) -> None:
    conn.execute("UPDATE solicitudes_sicop SET alerta_estado = ?, alerta_en = ? WHERE id = ?",
                 (estado, reloj().isoformat(timespec="seconds"), solicitud_id))


def _html(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
