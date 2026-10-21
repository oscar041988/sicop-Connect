"""Solicitud automática del reporte en SICOP con Playwright (obtención automática, lección 2).

Hace los mismos clics que una persona en Datos abiertos: «Detalle pliego de condiciones» → CSV → escribe
SICOP_REQUEST_EMAIL → «Continuar» → espera el código con el lector de Gmail (lección 1) → lo escribe → «Continuar»
→ «Procesando el reporte» → «Aceptar». Selectores por texto visible y rol, observados el 2026-10-21 (ver
docs/ACCESO_SICOP.md). Reglas: docs/DECISION_OBTENCION.md §8.

* Una sola solicitud por día: cuenta desde que se pulsa «Continuar» con el correo (SICOP manda un código).
* CAPTCHA, bloqueo o aviso contra programas → FALLO «control no automatizable», sin reintentar.
* Todo fallo queda en solicitudes_sicop con su motivo y una captura en EXPORTS_DIR (con los campos vaciados).
* Nunca se muestran el correo, el código ni el processId: el código va enmascarado y el processId solo se guarda
  en la base local, para la lección 3.
"""

from __future__ import annotations

import re
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.config import Settings
from app.database import connect
from app.importers.comun import HORA_CR
from app.sources.gmail_reader import CorreoNoLlego, FormatoDesconocido, GmailError

URL = "https://www.sicop.go.cr/app/module/pcont/public/ce-open-data"
REPORTE = "Detalle pliego de condiciones"
TEXTO_CORREO = "Correo electrónico donde se le notificará"
TEXTO_CODIGO = "Digite el código de verificación"
TEXTO_PROCESANDO = "Procesando el reporte"
ESPERA_MS = 30_000          # espera explícita máxima de cada ventana o botón
SONDEO_CODIGO_S = 15        # cada cuánto se revisa el buzón mientras se espera el código
MARGEN_RELOJ = timedelta(minutes=1)  # el reloj de la PC y el de Gmail pueden diferir unos segundos
CONTROL = re.compile(r"captcha|no soy un robot|acceso denegado|demasiadas solicitudes", re.IGNORECASE)


class FalloObtencion(Exception):
    """La solicitud no llegó a «Procesando el reporte». El motivo nunca incluye el correo, el código ni enlaces."""

    def __init__(self, motivo: str, control: bool = False):
        super().__init__(motivo)
        self.motivo = motivo
        self.control = control  # True: CAPTCHA o bloqueo, no se reintenta
        self.captura: Path | None = None


class YaSolicitadoHoy(Exception):
    """Hoy ya se envió una solicitud a SICOP (regla: una por día). No se abrió el navegador."""


@dataclass(frozen=True)
class Resultado:
    solicitud_id: int
    codigo: str = field(repr=False)
    process_id: str | None = field(repr=False)


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def _revisar_control(page, respuesta=None) -> None:
    """Se detiene ante un CAPTCHA, un bloqueo o un aviso contra programas: es un control que no se salta."""
    if respuesta is not None and respuesta.status in (403, 429):
        raise FalloObtencion(f"control no automatizable: SICOP respondió HTTP {respuesta.status} (bloqueo). "
                             "No se reintenta: volver al modo manual y avisar.", control=True)
    if page.locator("iframe[src*='captcha' i]").count() or page.get_by_text(CONTROL).count():
        raise FalloObtencion("control no automatizable: la página muestra un CAPTCHA o un aviso de bloqueo. "
                             "No se reintenta: volver al modo manual y avisar.", control=True)


def _esperar_codigo(lector, desde: datetime, minutos: int, reloj, dormir):
    limite = reloj() + timedelta(minutes=minutos)
    while True:
        try:
            return lector.buscar_codigo(desde)
        except CorreoNoLlego:
            if reloj() >= limite:
                raise FalloObtencion(f"No llegó el correo con el código en {minutos} min. No se repite la solicitud "
                                     "hoy: revisar en Gmail si llegó a otra carpeta o con otro asunto.") from None
            dormir(SONDEO_CODIGO_S)
        except (FormatoDesconocido, GmailError) as exc:
            raise FalloObtencion(f"No se pudo leer el código: {exc}") from None


def _pasos(page, settings: Settings, lector, marcar_correo_enviado, reloj, dormir, avisar) -> tuple:
    estado = {"paso": "abrir Datos abiertos"}

    def paso(nombre: str) -> None:
        estado["paso"] = nombre

    try:
        respuesta = page.goto(URL, wait_until="domcontentloaded")
        _revisar_control(page, respuesta)

        paso(f"desplegar «{REPORTE}»")
        page.get_by_role("button", name=REPORTE).click()
        _revisar_control(page)

        paso("hacer clic en CSV")
        csv = page.locator("img[alt='CSV']:visible")
        csv.first.wait_for()
        if csv.count() != 1:
            raise FalloObtencion(f"Hay {csv.count()} iconos CSV visibles y se esperaba 1: SICOP cambió la página.")
        csv.click()

        paso("ventana del correo")
        ventana = page.get_by_role("dialog").filter(has_text=TEXTO_CORREO)
        ventana.wait_for()
        _revisar_control(page)
        ventana.get_by_role("textbox").fill(settings.sicop_request_email)
        desde = reloj() - MARGEN_RELOJ
        ventana.get_by_role("button", name="Continuar").click()
        marcar_correo_enviado()
        avisar("Correo escrito y «Continuar»: SICOP manda el código (la solicitud de hoy ya cuenta).")

        paso("ventana del código")
        ventana = page.get_by_role("dialog").filter(has_text=TEXTO_CODIGO)
        ventana.wait_for()
        avisar(f"Esperando el correo con el código (hasta {settings.obtain_code_timeout_min} min)…")
        codigo = _esperar_codigo(lector, desde, settings.obtain_code_timeout_min, reloj, dormir).valor
        avisar("Código encontrado en el buzón; se escribe en SICOP.")
        ventana.get_by_role("textbox").fill(codigo)
        ventana.get_by_role("button", name="Continuar").click()

        paso(f"ventana «{TEXTO_PROCESANDO}»")
        ventana = page.get_by_role("dialog").filter(has_text=TEXTO_PROCESANDO)
        try:
            ventana.wait_for()
        except PlaywrightTimeout:
            _revisar_control(page)
            raise FalloObtencion("SICOP no aceptó el código o cambió la ventana: no apareció "
                                 f"«{TEXTO_PROCESANDO}». No se repite la solicitud hoy.") from None
        enlace = ventana.get_by_role("link", name="URL de descarga")
        href = enlace.first.get_attribute("href") if enlace.count() else None
        encontrado = re.search(r"processId=(\d+)", href or "")
        ventana.get_by_role("button", name="Aceptar").click()
        return codigo, (encontrado.group(1) if encontrado else None)
    except PlaywrightTimeout:
        raise FalloObtencion(f"Paso «{estado['paso']}»: no apareció a tiempo. SICOP pudo cambiar la página "
                             "(ver la captura y docs/ACCESO_SICOP.md).") from None
    except PlaywrightError as exc:
        raise FalloObtencion(f"Paso «{estado['paso']}»: error del navegador ({type(exc).__name__}).") from None


def _captura(page, carpeta: Path, nombre: str) -> Path | None:
    """Captura del fallo con los campos vaciados antes, para que no se vean el correo ni el código."""
    try:
        page.evaluate("document.querySelectorAll('input, textarea').forEach(e => { e.value = ''; })")
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / nombre
        page.screenshot(path=str(ruta), full_page=True)
        return ruta
    except PlaywrightError:
        return None


def _hoy_ya_se_envio(conn: sqlite3.Connection, hoy: str) -> bool:
    return conn.execute("SELECT 1 FROM solicitudes_sicop WHERE substr(solicitada_en, 1, 10) = ? AND correo_enviado = 1",
                        (hoy,)).fetchone() is not None


def solicitar_reporte(settings: Settings, lector, *, ver: bool = False, reloj: Callable[[], datetime] = _ahora,
                      dormir: Callable[[float], None] = time.sleep, avisar: Callable[[str], None] = lambda _: None,
                      preparar_contexto: Callable | None = None, espera_ms: int = ESPERA_MS) -> Resultado:
    """Una solicitud del «Detalle pliego de condiciones» en CSV. Lanza YaSolicitadoHoy o FalloObtencion."""
    if not settings.sicop_request_email:
        raise FalloObtencion("Falta SICOP_REQUEST_EMAIL en .env (el buzón donde llegan los correos de SICOP).")
    inicio = reloj()
    with closing(connect(settings.database_path)) as conn:
        try:
            if _hoy_ya_se_envio(conn, inicio.date().isoformat()):
                raise YaSolicitadoHoy("Hoy ya se envió una solicitud a SICOP (regla: una por día). No se pidió nada.")
            solicitud_id = conn.execute("INSERT INTO solicitudes_sicop (solicitada_en) VALUES (?)",
                                        (inicio.isoformat(timespec="seconds"),)).lastrowid
        except sqlite3.OperationalError:
            raise FalloObtencion("La base no tiene la tabla solicitudes_sicop: ejecuta python -m app.cli migrate.") from None

        def marcar_correo_enviado() -> None:
            conn.execute("UPDATE solicitudes_sicop SET correo_enviado = 1 WHERE id = ?", (solicitud_id,))

        def terminar(estado: str, motivo: str | None = None, process_id: str | None = None,
                     captura: Path | None = None) -> None:
            conn.execute("UPDATE solicitudes_sicop SET estado = ?, motivo = ?, process_id = ?, captura = ?,"
                         " terminada_en = ? WHERE id = ?",
                         (estado, motivo, process_id, str(captura) if captura else None,
                          reloj().isoformat(timespec="seconds"), solicitud_id))

        try:
            with sync_playwright() as p:
                navegador = p.chromium.launch(headless=not ver)
                try:
                    contexto = navegador.new_context(locale="es-CR")  # nuevo: sin cookies guardadas
                    if preparar_contexto is not None:
                        preparar_contexto(contexto)
                    page = contexto.new_page()
                    page.set_default_timeout(espera_ms)
                    avisar(f"Abriendo SICOP {'con' if ver else 'sin'} ventana…")
                    try:
                        codigo, process_id = _pasos(page, settings, lector, marcar_correo_enviado, reloj, dormir,
                                                    avisar)
                    except FalloObtencion as fallo:
                        fallo.captura = _captura(page, settings.exports_dir,
                                                 f"obtencion-fallo-{inicio:%Y%m%d-%H%M%S}-{solicitud_id}.png")
                        raise
                finally:
                    navegador.close()
        except FalloObtencion as fallo:
            terminar("fallo", fallo.motivo, captura=fallo.captura)
            raise
        except PlaywrightError as exc:
            fallo = FalloObtencion(f"No se pudo abrir el navegador ({type(exc).__name__}). "
                                   "¿Falta python -m playwright install chromium?")
            terminar("fallo", fallo.motivo)
            raise fallo from None
        terminar("procesando", process_id=process_id)
        return Resultado(solicitud_id, codigo, process_id)

