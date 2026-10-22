"""Obtención automática integrada al ciclo (lección 4): una «vuelta» de obtain auto.

La tarea programada llama a obtain auto cada 15 minutos (07:00–20:00, lunes a viernes). Cada vuelta:
1. Con SOURCE_MODE=manual no hace nada: no abre SICOP ni lee Gmail.
2. Desde OBTAIN_REQUEST_HOUR, si hoy no hay ninguna solicitud, pide el reporte (obtain request). Una por día: si
   la de hoy falló, no se pide otra (regla 4 de DECISION_OBTENCION.md §8).
3. Si hay una solicitud abierta, revisa el buzón una vez (obtain poll: enlace → descarga → validación → la copia
   a INCOMING_DIR).
4. Una solicitud que terminó «fallido» manda UNA alerta a OBTAIN_ALERT_TO con el motivo y el plan B: descargar a
   mano con el correo «Envío de reporte» y dejar el ZIP en la carpeta de entrada. La alerta nunca lleva el enlace,
   el código ni el processId (regla 7). Mientras los avisos estén en dry-run, solo se escribe la vista previa.
5. Si hay un archivo listo en INCOMING_DIR (el que dejó la descarga automática o uno dejado a mano), corre el ciclo:
   importar → evaluar → avisar, SIEMPRE en dry-run, con el bloqueo de run-cycle y modo «auto» en source_runs.
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

from app import ciclo
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
    ciclo_id: int | None = None

    def nota(self, texto: str, fallo: bool = False) -> None:
        self.lineas.append(("FALLO · " if fallo else "") + texto)
        self.fallo = self.fallo or fallo


def ruta_bloqueo(settings: Settings) -> Path:
    return settings.database_path.parent / "obtain-auto.lock"


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def vuelta(settings: Settings, *, crear_lector: Callable, proveedor_alerta: Callable | None = None,
           reloj: Callable[[], datetime] = _ahora, solicitar: Callable = sicop_browser.solicitar_reporte,
           sondear: Callable = obtencion.sondear, correr_ciclo: Callable = ciclo.run_cycle) -> Vuelta:
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
        _ciclo(settings, v, ahora, correr_ciclo)
    return v


# --- 2 y 3: pedir y sondear --------------------------------------------------------------------------------

def _solicitud_de_hoy(settings: Settings, hoy: str) -> sqlite3.Row | None:
    with closing(connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute("SELECT id, estado FROM solicitudes_sicop WHERE substr(solicitada_en, 1, 10) = ?"
                            " ORDER BY id DESC LIMIT 1", (hoy,)).fetchone()


def _hay_abierta(settings: Settings) -> bool:
    with closing(connect(settings.database_path)) as conn:
        return conn.execute("SELECT 1 FROM solicitudes_sicop WHERE estado IN (?, ?, ?, ?) LIMIT 1",
                            obtencion.ABIERTOS).fetchone() is not None


def _obtener(settings, v: Vuelta, ahora: datetime, crear_lector, solicitar, sondear, reloj) -> None:
    hoy = _solicitud_de_hoy(settings, ahora.date().isoformat())
    pedir = hoy is None and ahora.time() >= settings.obtain_request_hour
    if hoy is None and not pedir:
        v.nota(f"Todavía no es hora de pedir el reporte (desde las {settings.obtain_request_hour:%H:%M}).")
    elif hoy is not None and hoy["estado"] == "validado":
        v.nota(f"La solicitud de hoy (#{hoy['id']}) ya está validada.")
    elif hoy is not None and hoy["estado"] == "fallido":
        v.nota(f"La solicitud de hoy (#{hoy['id']}) falló: no se pide otra hoy (una por día). Ver la alerta.")
    if not pedir and not _hay_abierta(settings):
        return
    try:
        lector = crear_lector(settings)
    except GmailError as exc:
        v.nota(f"No se pudo abrir Gmail: {exc} No se pidió ni revisó nada.", fallo=True)
        return
    if pedir:
        try:
            r = solicitar(settings, lector)
        except YaSolicitadoHoy as exc:
            v.nota(str(exc))
        except FalloObtencion as exc:  # solicitar_reporte ya la dejó «fallido» en la base
            v.nota(f"Solicitud a SICOP: {exc.motivo}", fallo=True)
            return
        else:
            v.nota(f"Solicitud #{r.solicitud_id} hecha: SICOP mostró «Procesando el reporte».")
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


def _alertar(settings: Settings, v: Vuelta, reloj, proveedor_alerta) -> None:
    with closing(connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute("SELECT * FROM solicitudes_sicop WHERE estado = 'fallido' AND alerta_estado IS NULL"
                             " ORDER BY id").fetchall()
        for fila in filas:
            asunto, cuerpo = texto_alerta(settings, fila)
            real = settings.notifications_enabled and not settings.notifications_dry_run and settings.obtain_alert_to
            if not real or proveedor_alerta is None:
                ruta = settings.exports_dir / f"alerta-obtencion-{fila['id']}.txt"
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text(f"Para: {settings.obtain_alert_to or '(falta OBTAIN_ALERT_TO)'}\n"
                                f"Asunto: {asunto}\n\n{cuerpo}\n", encoding="utf-8")
                _marcar(conn, fila["id"], "vista_previa", reloj)
                v.nota(f"Alerta de la solicitud #{fila['id']}: vista previa en {ruta} (avisos en dry-run, no se envió).")
                continue
            _marcar(conn, fila["id"], "incierta", reloj)  # antes de llamar a Gmail: si se cae, no se reenvía sola
            try:
                proveedor_alerta(settings).enviar(settings.obtain_alert_to, asunto, f"<pre>{_html(cuerpo)}</pre>",
                                                  cuerpo)
            except EnvioRechazado as exc:
                _marcar(conn, fila["id"], "fallida", reloj)
                v.nota(f"Alerta de la solicitud #{fila['id']}: Gmail la rechazó ({exc}).", fallo=True)
            except Exception as exc:  # noqa: BLE001 — EnvioIncierto o cualquier otro: queda incierta
                v.nota(f"Alerta de la solicitud #{fila['id']}: sin respuesta clara de Gmail ({type(exc).__name__}). "
                       "Revisar Gmail › Enviados; no se reenvía sola.", fallo=True)
            else:
                _marcar(conn, fila["id"], "aceptada", reloj)
                v.nota(f"Alerta de la solicitud #{fila['id']} enviada a {settings.obtain_alert_to}.")


def _marcar(conn: sqlite3.Connection, solicitud_id: int, estado: str, reloj) -> None:
    conn.execute("UPDATE solicitudes_sicop SET alerta_estado = ?, alerta_en = ? WHERE id = ?",
                 (estado, reloj().isoformat(timespec="seconds"), solicitud_id))


def _html(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- 5: ciclo ----------------------------------------------------------------------------------------------

def _ciclo(settings: Settings, v: Vuelta, ahora: datetime, correr_ciclo) -> None:
    if not settings.incoming_dir.is_dir():
        return
    listos, apartados = ciclo.recoger(settings.incoming_dir)
    if not listos:
        if any(a.resultado == "en_espera" for a in apartados):
            v.nota("Hay un archivo recién copiado en la carpeta de entrada: se importa en la próxima vuelta.")
        return
    try:
        c = correr_ciclo(settings, "real", dry_run=True, ahora=ahora, modo="auto")
    except CicloOcupado:
        v.nota("Hay un ciclo en curso (¿run-cycle a mano?): el archivo se importa en la próxima vuelta.")
        return
    except Exception as exc:  # noqa: BLE001 — run_cycle ya lo registró como fallo en source_runs
        v.nota(f"El ciclo se detuvo ({type(exc).__name__}: {exc}). Quedó registrado como fallo.", fallo=True)
        return
    v.ciclo_id = c.id
    importados = c.contar("importado")
    if c.estado == "ok":
        preparados = sum(len(x) for x in c.avisos.preparados.values()) if c.avisos else 0
        v.nota(f"Ciclo #{c.id} OK (dry-run): {importados} reporte(s) importado(s), {preparados} aviso(s) preparado(s).")
    else:
        v.nota(f"Ciclo #{c.id}: {c.error}", fallo=True)
