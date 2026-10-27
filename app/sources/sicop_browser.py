"""Solicitud automática del reporte en SICOP con Playwright (obtención automática, lección 2).

Hace los mismos clics que una persona en Datos abiertos: «Detalle pliego de condiciones» → CSV → escribe
SICOP_REQUEST_EMAIL → «Continuar» → espera el código con el lector de Gmail (lección 1) → lo escribe → «Continuar»
→ «Procesando el reporte» → «Aceptar». Selectores por texto visible y rol, observados el 2026-10-21 (ver
docs/ACCESO_SICOP.md). Reglas: docs/DECISION_OBTENCION.md §8.

* Una sola solicitud por turno (OBTAIN_REQUEST_HOUR: 06:30 y 14:00, dos por día; 2026-10-26): cuenta
  desde que se pulsa «Continuar» con el correo (SICOP manda un código).
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
from urllib.parse import urlsplit
from typing import Callable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import expect, sync_playwright

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
ESPERA_DESCARGA_MS = 120_000  # la página de SICOP tarda unos segundos en empezar la descarga
ANIMACION_MS = 10_000      # lo que puede tardar en cerrarse el panel que estaba abierto
SONDEO_CODIGO_S = 15        # cada cuánto se revisa el buzón mientras se espera el código
MARGEN_RELOJ = timedelta(minutes=1)  # el reloj de la PC y el de Gmail pueden diferir unos segundos
CONTROL = re.compile(r"captcha|no soy un robot|acceso denegado|demasiadas solicitudes"
                     r"|no fue posible acceder a la página solicitada", re.IGNORECASE)  # la última: 22/10, al descargar
ID_SOPORTE = re.compile(r"ID de soporte:\s*([0-9a-f-]{8,64})", re.IGNORECASE)


class FalloObtencion(Exception):
    """La solicitud no llegó a «Procesando el reporte». El motivo nunca incluye el correo, el código ni enlaces."""

    def __init__(self, motivo: str, control: bool = False):
        super().__init__(motivo)
        self.motivo = motivo
        self.control = control  # True: CAPTCHA o bloqueo, no se reintenta
        self.captura: Path | None = None


class YaSolicitadoHoy(Exception):
    """Este turno ya tiene una solicitud enviada a SICOP (regla: una por turno, dos turnos por día). No se abrió el
    navegador."""


@dataclass(frozen=True)
class Resultado:
    solicitud_id: int
    codigo: str = field(repr=False)
    process_id: str | None = field(repr=False)


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def detectar_control(page, respuesta=None) -> str | None:
    """CAPTCHA, bloqueo o aviso contra programas: devuelve el motivo («control no automatizable: …») o None.
    También lo usa la ficha del concurso (sicop_tender_detail.py)."""
    if respuesta is not None and respuesta.status in (403, 429):
        return f"control no automatizable: SICOP respondió HTTP {respuesta.status} (bloqueo)"
    if page.locator("iframe[src*='captcha' i]").count() or page.get_by_text(CONTROL).count():
        soporte = ID_SOPORTE.search(page.inner_text("body"))
        detalle = f" (ID de soporte de SICOP: {soporte.group(1)})" if soporte else ""
        return f"control no automatizable: la página muestra un CAPTCHA o un aviso de bloqueo{detalle}"
    return None


def _revisar_control(page, respuesta=None) -> None:
    """Se detiene ante un CAPTCHA, un bloqueo o un aviso contra programas: es un control que no se salta."""
    motivo = detectar_control(page, respuesta)
    if motivo:
        raise FalloObtencion(f"{motivo}. No se reintenta: volver al modo manual y avisar.", control=True)


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


def _pasos(page, settings: Settings, lector, anotar, reloj, dormir, avisar, foto=lambda _: None) -> tuple:
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
        # Al abrir un panel, el que estaba abierto se cierra con una animación: por un momento se ven dos iconos
        # CSV (observado el 2026-10-21). Se espera a que quede uno solo.
        try:
            expect(csv).to_have_count(1, timeout=ANIMACION_MS)
        except AssertionError:
            raise FalloObtencion(f"Hay {csv.count()} iconos CSV visibles y se esperaba 1: SICOP cambió la "
                                 "página.") from None
        csv.click()

        paso("ventana del correo")
        ventana = page.get_by_role("dialog").filter(has_text=TEXTO_CORREO)
        ventana.wait_for()
        _revisar_control(page)
        foto("1-ventana-correo")  # antes de escribir: la captura no muestra el correo
        ventana.get_by_role("textbox").fill(settings.sicop_request_email)
        desde = reloj() - MARGEN_RELOJ
        ventana.get_by_role("button", name="Continuar").click()
        anotar("correo_enviado")
        avisar("Correo escrito y «Continuar»: SICOP manda el código (la solicitud de hoy ya cuenta).")

        paso("ventana del código")
        ventana = page.get_by_role("dialog").filter(has_text=TEXTO_CODIGO)
        ventana.wait_for()
        foto("2-ventana-codigo")
        avisar(f"Esperando el correo con el código (hasta {settings.obtain_code_timeout_min} min)…")
        codigo = _esperar_codigo(lector, desde, settings.obtain_code_timeout_min, reloj, dormir).valor
        avisar("Código encontrado en el buzón; se escribe en SICOP.")
        foto("3-codigo-encontrado")  # antes de escribirlo: ¿sigue abierta la ventana?
        # 2026-10-21 15:18: la ventana del código desapareció mientras se esperaba el correo (nadie tocó Chrome).
        cerrada = FalloObtencion("La ventana del código se cerró antes de escribir el código. SICOP no recibió el "
                                 "código: hoy no habrá reporte. Ver las capturas paso a paso.")
        if not ventana.is_visible():
            raise cerrada
        try:
            ventana.get_by_role("textbox").fill(codigo)
            ventana.get_by_role("button", name="Continuar").click()
        except PlaywrightTimeout:
            if not ventana.is_visible():
                raise cerrada from None
            raise
        anotar("codigo_ingresado")

        paso(f"ventana «{TEXTO_PROCESANDO}»")
        ventana = page.get_by_role("dialog").filter(has_text=TEXTO_PROCESANDO)
        try:
            ventana.wait_for()
        except PlaywrightTimeout:
            _revisar_control(page)
            raise FalloObtencion("SICOP no aceptó el código o cambió la ventana: no apareció "
                                 f"«{TEXTO_PROCESANDO}». No se repite la solicitud hoy.") from None
        foto("4-procesando")
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


class _Diagnostico:
    """Con --ver: una captura en cada paso y un resumen (pasos con su hora y peticiones a SICOP) en
    EXPORTS_DIR/obtencion-AAAAMMDD-HHMMSS-<id>/. Las capturas se toman con los campos vacíos y el resumen no lleva
    correos, códigos ni parámetros de las direcciones."""

    def __init__(self, carpeta: Path, reloj):
        self.carpeta, self.reloj, self.lineas, self.red = carpeta, reloj, [], []
        carpeta.mkdir(parents=True, exist_ok=True)

    def nota(self, texto: str) -> None:
        self.lineas.append(f"{self.reloj():%H:%M:%S} · {texto}")

    def foto(self, page, nombre: str) -> None:
        try:
            page.screenshot(path=str(self.carpeta / f"{nombre}.png"), full_page=True)
            self.nota(f"captura {nombre}.png")
        except PlaywrightError:
            self.nota(f"no se pudo tomar la captura {nombre}")

    def respuesta(self, respuesta) -> None:
        pedido = respuesta.request
        if pedido.resource_type in ("document", "xhr", "fetch"):
            partes = urlsplit(pedido.url)  # sin ?parámetros
            self.red.append(f"{self.reloj():%H:%M:%S} · {pedido.method} {partes.netloc}{partes.path} → "
                            f"{respuesta.status}")

    def guardar(self) -> Path:
        ruta = self.carpeta / "diagnostico.txt"
        ruta.write_text("Pasos:\n" + "\n".join(self.lineas) + "\n\nPeticiones de la página (sin parámetros):\n"
                        + "\n".join(self.red) + "\n", encoding="utf-8")
        return ruta


def turno_de(settings: Settings, momento: datetime) -> str:
    """El turno («06:30», «14:00») al que pertenece una solicitud hecha en ese momento: la última hora de
    OBTAIN_REQUEST_HOUR ya pasada. Antes de la primera hora cuenta como la primera, para que una solicitud a mano
    temprano no sume una tercera en el día."""
    horas = settings.obtain_request_hours
    pasadas = [h for h in horas if momento.time() >= h]
    return f"{(pasadas or horas)[-1 if pasadas else 0]:%H:%M}"


def _turno_ya_se_envio(conn: sqlite3.Connection, hoy: str, turno: str) -> bool:
    return conn.execute("SELECT 1 FROM solicitudes_sicop WHERE substr(solicitada_en, 1, 10) = ? AND turno = ?"
                        " AND correo_enviado = 1", (hoy, turno)).fetchone() is not None


def solicitar_reporte(settings: Settings, lector, *, ver: bool = False, reloj: Callable[[], datetime] = _ahora,
                      dormir: Callable[[float], None] = time.sleep, avisar: Callable[[str], None] = lambda _: None,
                      preparar_contexto: Callable | None = None, espera_ms: int = ESPERA_MS,
                      diagnostico: bool | None = None) -> Resultado:
    """Una solicitud del «Detalle pliego de condiciones» en CSV. Lanza YaSolicitadoHoy o FalloObtencion.

    diagnostico (por defecto, igual que ver): capturas de cada paso y resumen en EXPORTS_DIR (ver _Diagnostico)."""
    if not settings.sicop_request_email:
        raise FalloObtencion("Falta SICOP_REQUEST_EMAIL en .env (el buzón donde llegan los correos de SICOP).")
    inicio = reloj()
    turno = turno_de(settings, inicio)
    with closing(connect(settings.database_path)) as conn:
        try:
            if _turno_ya_se_envio(conn, inicio.date().isoformat(), turno):
                raise YaSolicitadoHoy(f"El turno de las {turno} de hoy ya tiene una solicitud a SICOP (regla: una por "
                                      "turno). No se pidió nada.")
            solicitud_id = conn.execute("INSERT INTO solicitudes_sicop (solicitada_en, turno) VALUES (?, ?)",
                                        (inicio.isoformat(timespec="seconds"), turno)).lastrowid
        except sqlite3.OperationalError:
            raise FalloObtencion("La base no tiene la tabla solicitudes_sicop: ejecuta python -m app.cli migrate.") from None

        def anotar(evento: str) -> None:
            if evento == "correo_enviado":
                conn.execute("UPDATE solicitudes_sicop SET correo_enviado = 1 WHERE id = ?", (solicitud_id,))
            else:  # codigo_ingresado
                conn.execute("UPDATE solicitudes_sicop SET estado = 'codigo_ingresado', codigo_ingresado_en = ?"
                             " WHERE id = ?", (reloj().isoformat(timespec="seconds"), solicitud_id))

        def fallar(fallo: FalloObtencion) -> None:
            conn.execute("UPDATE solicitudes_sicop SET estado = 'fallido', motivo = ?, captura = ?, terminada_en = ?"
                         " WHERE id = ?", (fallo.motivo, str(fallo.captura) if fallo.captura else None,
                                           reloj().isoformat(timespec="seconds"), solicitud_id))

        diag = None
        if ver if diagnostico is None else diagnostico:
            diag = _Diagnostico(settings.exports_dir / f"obtencion-{inicio:%Y%m%d-%H%M%S}-{solicitud_id}", reloj)
            aviso_original = avisar

            def avisar(texto: str) -> None:  # noqa: F811 — también queda en el resumen del diagnóstico
                diag.nota(texto)
                aviso_original(texto)

        try:
            with sync_playwright() as p:
                navegador = p.chromium.launch(headless=not ver)
                try:
                    contexto = navegador.new_context(locale="es-CR")  # nuevo: sin cookies guardadas
                    if preparar_contexto is not None:
                        preparar_contexto(contexto)
                    page = contexto.new_page()
                    page.set_default_timeout(espera_ms)
                    if diag:
                        page.on("response", diag.respuesta)
                    avisar(f"Abriendo SICOP {'con' if ver else 'sin'} ventana…")
                    foto = (lambda nombre: diag.foto(page, nombre)) if diag else (lambda _: None)
                    try:
                        codigo, process_id = _pasos(page, settings, lector, anotar, reloj, dormir, avisar, foto)
                    except FalloObtencion as fallo:
                        fallo.captura = _captura(page, settings.exports_dir,
                                                 f"obtencion-fallo-{inicio:%Y%m%d-%H%M%S}-{solicitud_id}.png")
                        if diag:
                            diag.nota(f"FALLO · {fallo.motivo}")
                        raise
                finally:
                    navegador.close()
                    if diag:
                        avisar(f"Capturas y resumen del diagnóstico en {diag.guardar().parent}")
        except FalloObtencion as fallo:
            fallar(fallo)
            raise
        except PlaywrightError as exc:
            fallo = FalloObtencion(f"No se pudo abrir el navegador ({type(exc).__name__}). "
                                   "¿Falta python -m playwright install chromium?")
            fallar(fallo)
            raise fallo from None
        # Siguiente paso: obtain poll espera el correo con el enlace (app/sources/obtencion.py).
        conn.execute("UPDATE solicitudes_sicop SET estado = 'esperando_enlace', esperando_enlace_en = ?, process_id = ?"
                     " WHERE id = ?", (reloj().isoformat(timespec="seconds"), process_id, solicitud_id))
        return Resultado(solicitud_id, codigo, process_id)


def _texto_diagnostico(diagnostico: dict) -> str:
    """« Diagnóstico: enlace abierto a las 08:56:52 · HTTP 200 · página www.sicop.go.cr/…» (sin parámetros)."""
    if diagnostico["abierto"] is None:
        return ""
    partes = [f"enlace abierto a las {diagnostico['abierto']:%H:%M:%S}",
              f"HTTP {diagnostico['http']}" if diagnostico["http"] is not None else "sin respuesta HTTP"]
    if diagnostico["pagina"]:
        partes.append(f"página {diagnostico['pagina']}")
    return " Diagnóstico: " + " · ".join(partes) + "."


def descargar(url: str, carpeta: Path, nombre: str, *, preparar_contexto: Callable | None = None,
              espera_ms: int = ESPERA_DESCARGA_MS) -> Path:
    """Abre el enlace «Reporte» y guarda lo que SICOP descargue en carpeta/nombre (lección 3).

    La página muestra «Espere mientras se descarga el archivo» y el navegador baja el archivo: se espera el evento
    de descarga. Se guarda primero como .part y se renombra al terminar. Sin descarga → FalloObtencion."""
    carpeta.mkdir(parents=True, exist_ok=True)
    destino, parcial = carpeta / nombre, carpeta / f"{nombre}.part"
    diagnostico = {"abierto": None, "http": None, "pagina": None}  # solo para el motivo de un FALLO
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            try:
                contexto = navegador.new_context(locale="es-CR", accept_downloads=True)
                if preparar_contexto is not None:
                    preparar_contexto(contexto)
                page = contexto.new_page()
                try:
                    with page.expect_download(timeout=espera_ms) as info:
                        try:
                            diagnostico["abierto"] = _ahora()
                            respuesta = page.goto(url, wait_until="domcontentloaded", timeout=espera_ms)
                            if respuesta is not None:
                                partes = urlsplit(respuesta.url)  # sin ?parámetros: el processId no se muestra
                                diagnostico.update(http=respuesta.status, pagina=f"{partes.netloc}{partes.path}")
                            _revisar_control(page, respuesta)
                        except PlaywrightError as exc:
                            if "Download is starting" not in str(exc):  # el enlace descargó sin abrir página
                                raise
                    descarga = info.value
                    if descarga.failure():
                        raise FalloObtencion("La descarga de SICOP se interrumpió: descargar a mano con el enlace "
                                             "del correo.")
                    descarga.save_as(str(parcial))
                except FalloObtencion as fallo:
                    if fallo.control and fallo.captura is None:
                        fallo.captura = _captura(page, carpeta, f"{nombre}-bloqueo.png")
                    fallo.motivo += _texto_diagnostico(diagnostico)
                    raise
                except PlaywrightTimeout:
                    fallo = FalloObtencion("Enlace vencido o SICOP no inició la descarga (no llegó ningún archivo "
                                           f"en {espera_ms // 1000} s).{_texto_diagnostico(diagnostico)}")
                    fallo.captura = _captura(page, carpeta, f"{nombre}-sin-descarga.png")
                    raise fallo from None
            finally:
                navegador.close()
    except PlaywrightError as exc:
        raise FalloObtencion(f"Error del navegador al descargar ({type(exc).__name__}).") from None
    parcial.replace(destino)
    return destino
