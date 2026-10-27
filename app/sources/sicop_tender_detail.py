"""Ficha del concurso en la consulta pública de SICOP (enriquecimiento, lección 2; docs/DETALLE_CARTEL.md).

Hace lo mismo que una persona: abre la consulta de concursos, «Búsqueda avanzada», escribe el Número SICOP en su
casilla, «Consultar» y abre el resultado. Los datos NO se leen de la pantalla (están en casillas de solo lectura):
se escuchan las respuestas JSON que la propia página recibe de prod-api.sicop.go.cr. No se hace ninguna petición
extra a SICOP ni se llama a esa dirección sin el navegador (SICOP no ofrece API a terceros, DECISION_OBTENCION.md §8).

* Navegador CON ventana por defecto (BROWSER_HEADLESS=false), con video y una captura por paso en
  RECORDINGS_DIR/<fecha>/<Número SICOP>/.
* La ficha se une al cartel solo por su Número SICOP: la búsqueda debe traer exactamente un resultado con ese número.
* No se guardan datos de funcionarios (decisión de Oscar, 2026-10-27): se quitan de la copia fiel.
* Cada cambio de la ficha es una fila nueva en tender_details; la misma ficha otra vez no agrega nada.
* CAPTCHA, bloqueo o «No fue posible acceder…» → FALLO «control no automatizable»: se detiene todo, sin reintentar.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from app.config import Settings
from app.database import connect, transaccion
from app.dinero import texto_decimal
from app.importers.comun import HORA_CR
from app.sources.sicop_browser import detectar_control

URL = "https://www.sicop.go.cr/app/module/bid/public/tenders"
API = "prod-api.sicop.go.cr"
ESPERA_MS = 30_000
ESPERA_OPCIONALES_MS = 3_000
MAX_POR_CORRIDA = 3  # lección 2: pruebas a mano; la cola con ENRICH_MAX_PER_DAY es de la lección 4

# Respuestas que se guardan (observadas el 2026-10-27). Las de funcionarios (epCartelRoleStaff, umUser) no.
RUTAS = {
    "busqueda": "/bid/api/v1/public/epCartel/searchEpCartelsSp",
    "ficha": "/bid/api/v1/public/epCartel/findPublishedById",
    "lineas": "/bid/api/v1/public/epCartelProd/findByEpCartelId",
    "documentos": "/bid/api/v1/public/epCartelFile/getCartelFilesById",
    "criterios": "/bid/api/v1/public/epCartelSustCriteria/findAllByCartelId",
    "impactos": "/bid/api/v1/public/epCartelSustCriteriaImpact/findAllByCartelId",
}
OBLIGATORIAS = ("ficha", "lineas", "documentos")
OPCIONALES = ("criterios", "impactos")
CAMPOS_FICHA = ("cartelNo", "cartelSeq", "cartelVersion", "instCartelNo", "cartelNm", "cartelStatStr", "biddocEndDt")

# Campos de personas, en cualquier nivel del JSON: nombres, identificaciones, correos y teléfonos de funcionarios,
# y el nombre de quien presentó un recurso.
PERSONALES = re.compile(r"(?i)^(executor(nm|id)\d?|writer(nm|id)|\w*staff(nm|id)|userid|inputerid|email|m?telno"
                        r"|cartelsupnm)$")
# Campos que cambian solos con el reloj (¿ya pasó el inicio, el cierre…?) o con la paginación: no cuentan para saber
# si la ficha cambió.
VOLATILES = re.compile(r"^(startPassYn|endPassYn|openbidPassYn|isOpenbidDtYn|isDateTrue|\w+EndYn|pageable|sort)$")
GARANTIAS = ("participationGuarnRcvYnNm", "participationGuarnAmt", "participationGuarnAmtType", "participationGuarnDur",
             "fulfillmentGuarnRcvYnNm", "fulfillmentGuarnAmt", "fulfillmentGuarnAmtType", "fulfillmentGuarnDur",
             "collateralGuarnRcvYnNm", "collateralGuarnAmt", "collateralGuarnAmtType", "collateralGuarnDur",
             "advancedNm", "advancedAmt", "advancedCont", "fine", "fineArticle", "amtReadjustYnNm", "amtReadjustCont",
             "contractDur", "contractDurUnitNm", "contractExtendDur", "contractExtendDurUnitNm")
DOCUMENTO = ("docFileSeqno", "fileTypeNm", "docNm", "clientFileNm", "fileSizeMb", "serverFileNm", "fileServerPath")


class FalloFicha(Exception):
    """La ficha no se pudo obtener o no tiene la forma esperada. El motivo nunca trae datos de personas."""

    def __init__(self, motivo: str, control: bool = False):
        super().__init__(motivo)
        self.motivo = motivo
        self.control = control  # True: CAPTCHA o bloqueo; se detiene todo y no se reintenta
        self.captura: Path | None = None


@dataclass(frozen=True)
class Ficha:
    """Las respuestas de SICOP sin los campos de personas (números como Decimal)."""
    nro_sicop: str
    respuestas: dict = field(repr=False)
    campos_quitados: tuple[str, ...] = ()


@dataclass(frozen=True)
class Guardado:
    nueva: bool
    detalle_id: int
    desde: str  # cuándo se guardó esa versión
    versiones: int


@dataclass
class Consulta:
    """Resultado de un cartel en enriquecer(): nueva · sin_cambios · fallo · control · no_consultado."""
    nro_sicop: str
    resultado: str
    motivo: str = ""
    guardado: Guardado | None = None
    campos: dict | None = None
    documentos: list | None = None  # ResultadoDocumento de sicop_documentos (con --documentos)
    grabacion: str | None = None    # «AAAA-MM-DD/<nro>/HHMMSS»: prefijo de su video y capturas en RECORDINGS_DIR
    duracion_s: float | None = None
    iniciada_en: str | None = None


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


# --- Respuestas: limpieza, copia fiel y huella ----------------------------------------------------------------

def _limpiar(valor, quitados: set[str]):
    if isinstance(valor, dict):
        limpio = {}
        for clave, sub in valor.items():
            if PERSONALES.match(clave):
                quitados.add(clave)
            else:
                limpio[clave] = _limpiar(sub, quitados)
        return limpio
    if isinstance(valor, list):
        return [_limpiar(x, quitados) for x in valor]
    return valor


def _sin_volatiles(valor):
    if isinstance(valor, dict):
        return {k: _sin_volatiles(v) for k, v in valor.items() if not VOLATILES.match(k)}
    if isinstance(valor, list):
        return [_sin_volatiles(x) for x in valor]
    return valor


def _numero(valor):
    if isinstance(valor, Decimal):  # en la copia se escribe igual que llegó (291782.16); los campos usan el Decimal
        return float(valor)
    raise TypeError(f"{type(valor).__name__} no se puede guardar en JSON")


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, default=_numero)


def copia_fiel(ficha: Ficha) -> str:
    return _json(ficha.respuestas)


def huella(ficha: Ficha) -> str:
    return hashlib.sha256(_json(_sin_volatiles(ficha.respuestas)).encode("utf-8")).hexdigest()


def ficha_desde_textos(nro: str, textos: dict[str, str]) -> Ficha:
    """Arma la Ficha con los cuerpos JSON tal como llegaron. Montos como Decimal (nunca float)."""
    respuestas, quitados = {}, set()
    for nombre, texto in textos.items():
        try:
            datos = json.loads(texto, parse_float=Decimal)
        except ValueError:
            raise FalloFicha(f"La respuesta «{nombre}» de SICOP no es JSON: SICOP pudo cambiar la página.") from None
        if nombre == "busqueda":
            datos = (datos.get("content") or [None])[0] if isinstance(datos, dict) else None
        respuestas[nombre] = _limpiar(datos, quitados)
    return Ficha(nro, respuestas, tuple(sorted(quitados)))


# --- Campos útiles (los que marcó Oscar, DETALLE_CARTEL.md §3) -----------------------------------------------

def _fecha(campo: str, valor) -> str | None:
    if valor in (None, ""):
        return None
    try:
        fecha = datetime.fromisoformat(str(valor))
    except ValueError:
        raise FalloFicha(f"La fecha «{campo}» de la ficha tiene otro formato ({valor!r}): SICOP cambió la ficha.") from None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=HORA_CR)  # SICOP no trae zona: es hora de Costa Rica
    return fecha.isoformat(timespec="seconds")


def _monto(campo: str, valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, Decimal)):
        raise FalloFicha(f"El monto «{campo}» de la ficha no es un número ({valor!r}): SICOP cambió la ficha.")
    return texto_decimal(Decimal(valor))


def _texto(valor) -> str | None:
    return None if valor is None else str(valor)


def extraer_campos(ficha: Ficha) -> dict:
    r = ficha.respuestas
    f, b, lineas = r["ficha"], r.get("busqueda") or {}, r["lineas"]
    if not isinstance(lineas, dict) or not isinstance(r["documentos"], list):
        raise FalloFicha("Las líneas o los documentos de la ficha tienen otra forma: SICOP cambió la ficha.")
    monto = _monto("cartelBudget", f.get("cartelBudget"))
    recepcion = " · ".join(str(v) for v in (f.get("biddocTypeNm"), f.get("onlineYnNm")) if v)
    return {
        "estado_concurso": _texto(f.get("cartelStatStr") or b.get("cartelStatStr")),
        "version_pliego": _texto(f.get("cartelVersion")),
        "secuencia": _texto(f.get("cartelSeq")),
        "modificado": f.get("cartelModYn") if f.get("cartelModYn") in ("Y", "N") else None,
        "numero_procedimiento": _texto(f.get("instCartelNo")),
        "descripcion": _texto(f.get("cartelNm")),
        "tipo_procedimiento": _texto(f.get("proceTypeNm")),
        "tipo_modalidad": _texto(f.get("proceTypeDetailNm")),
        "tipo_recepcion": recepcion or None,
        "inicio_recepcion": _fecha("biddocStartDt", f.get("biddocStartDt")),
        "cierre_recepcion": _fecha("biddocEndDt", f.get("biddocEndDt")),
        "apertura": _fecha("openbidDt", f.get("openbidDt")),
        "limite_aclaraciones": _fecha("explainRcvEndDt", f.get("explainRcvEndDt")),
        # «Monto total estimado» en colones; el presupuesto en dólares viene aparte (DETALLE_CARTEL.md §3).
        "monto_estimado": monto,
        "moneda_monto": "CRC" if monto is not None else None,
        "monto_estimado_usd": _monto("cartelBudgetUsd", f.get("cartelBudgetUsd")),
        "garantias": _json({k: f[k] for k in GARANTIAS if k in f}),
        "criterios": _json({"criterios": [c.get("criterioCont") for c in r.get("criterios") or []],
                            "impactos": [c.get("impactDesc") for c in r.get("impactos") or []]}),
        "lineas_total": lineas.get("totalElements"),
        "documentos": _json([{k: d.get(k) for k in DOCUMENTO} for d in r["documentos"]]),
    }


def guardar_ficha(conn: sqlite3.Connection, ficha: Ficha, consultado_en: datetime) -> tuple[Guardado, dict]:
    """Mismo hash que una versión guardada → no agrega nada. Si cambió → fila nueva; las anteriores no se tocan."""
    campos = extraer_campos(ficha)
    hash_ = huella(ficha)
    existente = conn.execute("SELECT id, consultado_en FROM tender_details WHERE nro_sicop = ? AND content_hash = ?",
                             (ficha.nro_sicop, hash_)).fetchone()
    if existente is None:
        columnas = {"nro_sicop": ficha.nro_sicop, "consultado_en": consultado_en.isoformat(timespec="seconds"),
                    "content_hash": hash_, "copia_fiel": copia_fiel(ficha),
                    "campos_quitados": _json(list(ficha.campos_quitados)), **campos}
        detalle_id = conn.execute(f"INSERT INTO tender_details ({', '.join(columnas)}) "
                                  f"VALUES ({', '.join('?' * len(columnas))})", tuple(columnas.values())).lastrowid
        desde = columnas["consultado_en"]
    else:
        detalle_id, desde = existente
    versiones = conn.execute("SELECT count(*) FROM tender_details WHERE nro_sicop = ?",
                             (ficha.nro_sicop,)).fetchone()[0]
    return Guardado(existente is None, detalle_id, desde, versiones), campos


# --- Navegador -------------------------------------------------------------------------------------------------

class _Escucha:
    """Guarda el cuerpo de las respuestas de prod-api que interesan, tal como llegaron (texto)."""

    def __init__(self) -> None:
        self.textos: dict[str, str] = {}
        self.bloqueo: str | None = None
        self.error: str | None = None

    def __call__(self, respuesta) -> None:
        partes = urlsplit(respuesta.url)
        if partes.netloc != API:
            return
        if respuesta.status in (403, 429):
            self.bloqueo = f"control no automatizable: SICOP respondió HTTP {respuesta.status} (bloqueo)"
            return
        nombre = next((n for n, ruta in RUTAS.items() if partes.path == ruta), None)
        if nombre is None:
            return
        if respuesta.status != 200:
            self.error = f"SICOP respondió HTTP {respuesta.status} a «{nombre}»"
            return
        try:
            self.textos[nombre] = respuesta.text()
        except PlaywrightError:
            self.error = f"no se pudo leer la respuesta «{nombre}»"


def _revisar(page, escucha: _Escucha, respuesta=None) -> None:
    motivo = escucha.bloqueo or detectar_control(page, respuesta)
    if motivo:
        raise FalloFicha(f"{motivo}. No se reintenta: se detiene todo y se avisa.", control=True)


def _esperar(page, escucha: _Escucha, nombres, espera_ms: int, paso: str, obligatorio: bool = True) -> None:
    limite = time.monotonic() + espera_ms / 1000
    while not all(n in escucha.textos for n in nombres):
        _revisar(page, escucha)
        if escucha.error:
            raise FalloFicha(f"Paso «{paso}»: {escucha.error}.")
        if time.monotonic() > limite:
            if not obligatorio:
                return
            faltan = ", ".join(n for n in nombres if n not in escucha.textos)
            raise FalloFicha(f"Paso «{paso}»: SICOP no envió {faltan} en {espera_ms // 1000} s. Pudo cambiar la "
                             "página (ver la captura y docs/DETALLE_CARTEL.md).")
        page.wait_for_timeout(200)


def _pasos(page, nro: str, escucha: _Escucha, foto: Callable[[str], None], espera_ms: int) -> dict[str, str]:
    paso = "abrir la consulta de concursos"
    try:
        respuesta = page.goto(URL, wait_until="domcontentloaded")
        _revisar(page, escucha, respuesta)
        foto("1-inicio")

        paso = "abrir «Búsqueda avanzada»"
        page.get_by_role("button", name="Búsqueda avanzada").click()
        _revisar(page, escucha)

        paso = "escribir el Número SICOP"
        # Etiqueta flotante, no unida a su casilla: va DESPUÉS de la casilla, en el mismo contenedor (prueba real del
        # 2026-10-27: la casilla SIGUIENTE a la etiqueta es «Código de clasificación»).
        etiqueta = page.locator("label").filter(has_text=re.compile(r"^\s*Número de SICOP\s*$"))
        etiqueta.first.wait_for()
        if etiqueta.count() != 1:
            raise FalloFicha(f"Hay {etiqueta.count()} etiquetas «Número de SICOP» y se esperaba 1: SICOP cambió la "
                             "página.")
        casilla = etiqueta.locator("xpath=parent::*").locator("input")
        if casilla.count() != 1:
            raise FalloFicha(f"Junto a la etiqueta «Número de SICOP» hay {casilla.count()} casillas y se esperaba 1: "
                             "SICOP cambió la página.")
        casilla.fill(nro)
        foto("2-busqueda")

        paso = "consultar"
        escucha.textos.pop("busqueda", None)
        page.get_by_role("button", name="Consultar").click()
        _esperar(page, escucha, ("busqueda",), espera_ms, paso)
        try:
            datos = json.loads(escucha.textos["busqueda"])
            encontrados = datos["content"]
        except (ValueError, KeyError, TypeError):
            raise FalloFicha("La respuesta de la búsqueda tiene otra forma: SICOP cambió la página.") from None
        foto("3-resultado")
        if not encontrados:
            raise FalloFicha(f"La búsqueda no encontró el cartel {nro}. Revisa en la captura que el número quedó en "
                             "la casilla «Número de SICOP». Si está bien: la consulta solo muestra lo publicado en los "
                             "últimos 6 meses y el filtro «Estado de concurso» viene puesto; revisar a mano en SICOP.")
        if len(encontrados) > 1:
            raise FalloFicha(f"La búsqueda de {nro} trajo {len(encontrados)} resultados y se esperaba 1: no se elige "
                             "ninguno para no mezclar carteles.")
        cartel = encontrados[0]
        if str(cartel.get("cartelNo")) != nro:
            raise FalloFicha(f"La búsqueda de {nro} trajo otro cartel ({cartel.get('cartelNo')}): no se guarda nada.")

        paso = "abrir el resultado"
        fila = page.locator("tr").filter(has_text=str(cartel.get("instCartelNo")))
        enlace = fila.get_by_role("link").filter(has_text=re.compile(rf"^\s*\[{re.escape(str(cartel.get('proceType')))}\]"))
        if enlace.count() < 1:
            raise FalloFicha(f"No se encontró el enlace del resultado de {nro}: SICOP cambió la página.")
        enlace.first.click()
        _esperar(page, escucha, OBLIGATORIAS, espera_ms, paso)
        _esperar(page, escucha, OPCIONALES, ESPERA_OPCIONALES_MS, paso, obligatorio=False)
        _revisar(page, escucha)
        foto("4-ficha")
        return {n: escucha.textos[n] for n in ("busqueda", *OBLIGATORIAS, *OPCIONALES) if n in escucha.textos}
    except PlaywrightTimeout:
        raise FalloFicha(f"Paso «{paso}»: no apareció a tiempo. SICOP pudo cambiar la página (ver la captura y "
                         "docs/DETALLE_CARTEL.md).") from None
    except PlaywrightError as exc:
        raise FalloFicha(f"Paso «{paso}»: error del navegador ({type(exc).__name__}).") from None


def _validar(ficha: Ficha) -> None:
    f = ficha.respuestas.get("ficha")
    if not isinstance(f, dict):
        raise FalloFicha("La ficha llegó vacía o con otra forma: SICOP cambió la página.")
    faltan = [c for c in CAMPOS_FICHA if c not in f]
    if faltan:
        raise FalloFicha(f"A la ficha le faltan campos ({', '.join(faltan)}): SICOP cambió la ficha "
                         "(ver docs/DETALLE_CARTEL.md).")
    if str(f["cartelNo"]) != ficha.nro_sicop:
        raise FalloFicha(f"La ficha abierta es de otro cartel ({f['cartelNo']}) y se buscó {ficha.nro_sicop}: "
                         "no se guarda nada.")
    extraer_campos(ficha)  # fechas y montos con otra forma: FALLO con la ventana todavía abierta (captura)


def _foto(page, ruta: Path) -> None:
    try:
        page.screenshot(path=str(ruta), full_page=True)
    except PlaywrightError:
        pass


def buscar_ficha(nro: str, settings: Settings, *, reloj: Callable[[], datetime] = _ahora,
                 preparar_contexto: Callable | None = None, espera_ms: int = ESPERA_MS,
                 headless: bool | None = None, al_abrir_ficha: Callable | None = None,
                 inicio: datetime | None = None) -> Ficha:
    """Una consulta en SICOP. Lanza FalloFicha (control=True ante CAPTCHA o bloqueo).

    al_abrir_ficha(page, contexto, ficha, revisar): se llama con la ficha todavía abierta (lección 3: guardar la
    ficha y bajar sus documentos en la misma ventana, porque los documentos solo se bajan desde ahí).
    inicio: la hora que nombra la grabación (RECORDINGS_DIR/<fecha>/<nro>/<HHMMSS>-…); por defecto, reloj()."""
    inicio = inicio or reloj()
    carpeta = settings.recordings_dir / f"{inicio:%Y-%m-%d}" / nro
    carpeta.mkdir(parents=True, exist_ok=True)
    prefijo = f"{inicio:%H%M%S}"
    escucha = _Escucha()
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=settings.browser_headless if headless is None else headless)
            try:
                tamano = {"width": 1280, "height": 900}
                contexto = navegador.new_context(locale="es-CR", viewport=tamano, record_video_dir=str(carpeta),
                                                 record_video_size=tamano)  # nuevo: sin cookies guardadas
                if preparar_contexto is not None:
                    preparar_contexto(contexto)
                contexto.on("response", escucha)
                page = contexto.new_page()
                page.set_default_timeout(espera_ms)
                try:
                    textos = _pasos(page, nro, escucha, lambda nombre: _foto(page, carpeta / f"{prefijo}-{nombre}.png"),
                                    espera_ms)
                    ficha = ficha_desde_textos(nro, textos)
                    _validar(ficha)
                    if al_abrir_ficha is not None:
                        al_abrir_ficha(page, contexto, ficha, lambda: _revisar(page, escucha))
                except FalloFicha as fallo:
                    settings.exports_dir.mkdir(parents=True, exist_ok=True)
                    fallo.captura = settings.exports_dir / f"ficha-fallo-{inicio:%Y%m%d-%H%M%S}-{nro}.png"
                    _foto(page, fallo.captura)
                    _foto(page, carpeta / f"{prefijo}-FALLO.png")
                    raise
                finally:
                    video = page.video
                    contexto.close()  # el video se termina de escribir al cerrar
                    if video is not None:
                        try:
                            video.save_as(carpeta / f"{prefijo}-video.webm")
                            video.delete()
                        except PlaywrightError:
                            pass
            finally:
                navegador.close()
    except PlaywrightError as exc:
        raise FalloFicha(f"No se pudo abrir el navegador ({type(exc).__name__}). "
                         "¿Falta python -m playwright install chromium?") from None
    return ficha


def revisar_base(conn: sqlite3.Connection, nros: list[str], documentos: bool) -> None:
    """ValueError (sin abrir el navegador) si falta la migración o un número no está en la base."""
    try:
        conn.execute("SELECT 1 FROM tender_details LIMIT 1")
        conn.execute("SELECT es_reintento FROM enrich_consultas LIMIT 1")
        conn.execute("SELECT 1 FROM enrich_retiros LIMIT 1")
        conn.execute("SELECT 1 FROM enrich_revisiones LIMIT 1")
        if documentos:
            conn.execute("SELECT 1 FROM tender_documents LIMIT 1")
    except sqlite3.OperationalError:
        raise ValueError("A la base le faltan tablas de las fichas: ejecuta python -m app.cli migrate.") from None
    faltan = [n for n in nros if conn.execute("SELECT 1 FROM tenders WHERE nro_sicop = ?", (n,)).fetchone() is None]
    if faltan:
        raise ValueError(f"No están en la base: {', '.join(faltan)}. Solo se enriquecen carteles ya importados "
                         "(la ficha se une al cartel por su Número SICOP). No se consultó SICOP.")


def consultar_uno(conn: sqlite3.Connection, settings: Settings, nro: str, *, documentos: bool,
                  dormir: Callable[[float], None], reloj: Callable[[], datetime], avisar: Callable[[str], None],
                  espera_documento_ms: int | None = None, **opciones) -> Consulta:
    """Una consulta: ficha (y documentos) de un cartel, en una ventana. La usan enrich --nro y enrich run.
    Nunca lanza FalloFicha: el resultado queda en la Consulta (control = CAPTCHA o bloqueo)."""
    from app.sources import sicop_documentos as sd
    avisar(f"Consultando {nro} en SICOP…")
    hecho: dict = {"documentos": [] if documentos else None}
    inicio = reloj()
    arranque = time.monotonic()

    def al_abrir(page, contexto, ficha, revisar):
        with transaccion(conn):
            hecho["guardado"], hecho["campos"] = guardar_ficha(conn, ficha, reloj())
        if not documentos:
            return
        lista = ficha.respuestas["documentos"]
        avisar(f"Ficha guardada. Documentos: {len(lista)}.")
        extra = {"espera_ms": espera_documento_ms} if espera_documento_ms else {}
        try:
            sd.descargar_documentos(page, contexto, conn, settings, nro, hecho["guardado"].detalle_id, lista,
                                    hecho["documentos"], revisar=revisar, dormir=dormir, reloj=reloj,
                                    avisar=avisar, **extra)
        except sd._Control as exc:
            raise FalloFicha(f"{exc} (al bajar los documentos). No se reintenta: se detiene todo y se "
                             "avisa.", control=True) from None

    grabacion = f"{inicio:%Y-%m-%d}/{nro}/{inicio:%H%M%S}"
    try:
        buscar_ficha(nro, settings, reloj=reloj, al_abrir_ficha=al_abrir, inicio=inicio, **opciones)
        guardado = hecho["guardado"]
        consulta = Consulta(nro, "nueva" if guardado.nueva else "sin_cambios", guardado=guardado,
                            campos=hecho["campos"], documentos=hecho["documentos"])
    except FalloFicha as fallo:
        captura = f" Captura: {fallo.captura}" if fallo.captura else ""
        consulta = Consulta(nro, "control" if fallo.control else "fallo", fallo.motivo + captura,
                            guardado=hecho.get("guardado"), campos=hecho.get("campos"),
                            documentos=hecho["documentos"])
    consulta.grabacion, consulta.duracion_s = grabacion, round(time.monotonic() - arranque, 1)
    consulta.iniciada_en = inicio.isoformat(timespec="seconds")
    return consulta


def registrar_consulta(conn: sqlite3.Connection, consulta: Consulta, run_id: int | None = None,
                       es_reintento: bool = False) -> int | None:
    """Anota la consulta en la bitácora (enrich_consultas, migraciones 0020 y 0021). Las «no consultadas» no se
    anotan. es_reintento: la consulta repetida de enrich run tras un CAPTCHA o bloqueo."""
    if consulta.resultado == "no_consultado":
        return None
    documentos = consulta.documentos or []
    with transaccion(conn):
        return conn.execute(
            "INSERT INTO enrich_consultas (run_id, nro_sicop, iniciada_en, duracion_s, resultado, motivo, detalle_id,"
            " documentos_guardados, documentos_fallo, grabacion, es_reintento) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, consulta.nro_sicop, consulta.iniciada_en, consulta.duracion_s, consulta.resultado,
             consulta.motivo or None, consulta.guardado.detalle_id if consulta.guardado else None,
             sum(d.estado == "guardado" for d in documentos), sum(d.estado == "fallo" for d in documentos),
             consulta.grabacion, int(es_reintento))).lastrowid


def enriquecer(settings: Settings, nros: list[str], *, dormir: Callable[[float], None] = time.sleep,
               reloj: Callable[[], datetime] = _ahora, avisar: Callable[[str], None] = lambda _: None,
               documentos: bool = False, **opciones) -> list[Consulta]:
    """enrich --nro: de 1 a 3 carteles, uno por uno con ENRICH_DELAY_SECONDS de pausa. Un CAPTCHA o bloqueo detiene
    todo. Con documentos=True también baja y guarda los documentos de cada ficha (lección 3).
    Lanza ValueError (sin abrir el navegador) si un número no está en la base o falta la migración."""
    if not 1 <= len(nros) <= MAX_POR_CORRIDA:
        raise ValueError(f"Se consultan de 1 a {MAX_POR_CORRIDA} carteles por corrida.")
    if len(set(nros)) != len(nros):
        raise ValueError("Hay un Número SICOP repetido.")
    pausa = settings.enrich_delay_seconds
    with closing(connect(settings.database_path)) as conn:
        revisar_base(conn, nros, documentos)
        consultas: list[Consulta] = []
        for i, nro in enumerate(nros):
            if i:
                avisar(f"Pausa de {pausa} s antes de la siguiente consulta…")
                dormir(pausa)
            consulta = consultar_uno(conn, settings, nro, documentos=documentos, dormir=dormir, reloj=reloj,
                                     avisar=avisar, **opciones)
            registrar_consulta(conn, consulta)
            consultas.append(consulta)
            if consulta.resultado == "control":
                consultas += [Consulta(n, "no_consultado", "se detuvo por el control de SICOP") for n in nros[i + 1:]]
                break
    return consultas
