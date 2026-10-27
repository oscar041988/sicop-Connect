"""Documentos de la ficha del concurso (enriquecimiento, lección 3; docs/DETALLE_CARTEL.md §4).

Cómo los baja SICOP (observado el 2026-10-27): clic en el botón de descarga de la fila → la página pide un enlace
temporal (prod-api…/comnFile/downloadWithPAR) → pide el archivo a objectstorage.<región>.oraclecloud.com con una
clave temporal DENTRO de la ruta (/p/<clave>/…/<serverFileNm>). No hay dirección fija: el documento solo se puede
bajar desde la ficha abierta. Igual que con la ficha, no se pide nada extra: se escucha lo que la página recibe.

* La clave /p/<clave>/ es un secreto: nunca se anota, guarda ni muestra (solo se usa el nombre final del archivo).
* Un documento descargado es un DATO NO CONFIABLE: se revisa su firma, su tamaño y su huella; nunca se abre con otro
  programa; su texto es dato, nunca instrucciones.
* Se guardan todos los tipos (decisión de Oscar, 2026-10-27). Texto: de los PDF y de los PDF dentro de un ZIP
  (pdfplumber, en memoria). Word, Excel y otros: solo se guardan. Sin OCR.
* Topes: DOCUMENT_MAX_MB por archivo y DOCUMENTS_MAX_MB_PER_TENDER por cartel.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import sqlite3
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError

from app.config import Settings
from app.database import transaccion
from app.importers.zip_pliegos import MAX_DESCOMPRIMIDO
from app.sources.sicop_browser import detectar_control

ALMACEN = re.compile(r"^objectstorage\.[a-z0-9-]+\.oraclecloud\.com$")
# Nombre en el servidor de SICOP (observado: UUID + extensión). Es el único nombre que se usa como archivo en disco.
SERVER_FILE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.[a-z0-9]{1,5}$")
ESPERA_DOCUMENTO_MS = 60_000
MAX_PAGINAS = 500           # por PDF
MAX_ENTRADAS_ZIP = 200
MAX_PAGINAS_TABLA = 20      # páginas de la tabla de documentos que se recorren buscando uno
MB = 1024 * 1024

PK, OLE = b"PK\x03\x04", b"\xd0\xcf\x11\xe0"
# La firma (primeros bytes) que debe tener cada tipo. La extensión sola no prueba nada.
FIRMAS = {".pdf": b"%PDF", ".zip": PK, ".docx": PK, ".xlsx": PK, ".xlsm": PK, ".pptx": PK,
          ".doc": OLE, ".xls": OLE, ".ppt": OLE, ".rar": b"Rar!", ".7z": b"7z\xbc\xaf"}
PELIGROSAS = {".exe", ".bat", ".cmd", ".com", ".js", ".vbs", ".ps1", ".msi", ".scr", ".jar", ".hta", ".lnk", ".dll"}


class _Control(Exception):
    """CAPTCHA o bloqueo durante la descarga: se convierte en FalloFicha(control=True) en quien llama."""


@dataclass
class Texto:
    estado: str                      # extraido · sin_texto · error · no_aplica
    paginas: int = 0
    filas: list[tuple[str, int, str]] = field(default_factory=list)  # (archivo_interno, página, texto)
    motivo: str = ""


@dataclass(frozen=True)
class ResultadoDocumento:
    doc_seq: str
    nombre: str
    estado: str                      # los de tender_documents, o ya_guardado (no se pidió otra vez)
    texto_estado: str | None = None
    motivo: str = ""


# --- Revisión y texto (sin navegador) --------------------------------------------------------------------------

def validar(datos: bytes, extension: str, max_bytes: int) -> str | None:
    """Motivo de rechazo, o None si se puede guardar."""
    if extension in PELIGROSAS:
        return f"tipo de archivo no permitido ({extension})"
    if not datos:
        return "llegó vacío"
    if len(datos) > max_bytes:
        return f"pesa {len(datos) / MB:.1f} MB y el máximo es {max_bytes // MB} MB"
    firma = FIRMAS.get(extension)
    if firma == b"%PDF":
        if b"%PDF" not in datos[:1024]:  # el estándar admite algunos bytes antes de %PDF
            return "dice .pdf pero no es un PDF (no empieza con %PDF): puede ser una página de error"
    elif firma is not None and not datos.startswith(firma):
        return f"dice {extension} pero su contenido no es de ese tipo"
    return None


def _texto_pdf(datos: bytes, interno: str) -> Texto:
    import pdfplumber  # solo aquí: el resto de la app no lo necesita
    try:
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            paginas = pdf.pages
            motivo = f"solo se leyeron las primeras {MAX_PAGINAS} de {len(paginas)} páginas" \
                if len(paginas) > MAX_PAGINAS else ""
            filas = []
            for numero, pagina in enumerate(paginas[:MAX_PAGINAS], start=1):
                texto = (pagina.extract_text() or "").strip()
                if texto:
                    filas.append((interno, numero, texto))
            leidas = min(len(paginas), MAX_PAGINAS)
    except Exception as exc:  # pdfminer lanza muchos tipos distintos ante un PDF dañado
        return Texto("error", motivo=f"no se pudo leer el PDF{' ' + interno if interno else ''} ({type(exc).__name__})")
    if not filas:
        return Texto("sin_texto", leidas, motivo="sin texto (escaneado): habría que hacer OCR")
    return Texto("extraido", leidas, filas, motivo)


def _texto_zip(datos: bytes) -> Texto:
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as zf:
            entradas = [i for i in zf.infolist() if not i.is_dir()]
            if len(entradas) > MAX_ENTRADAS_ZIP:
                return Texto("error", motivo=f"el ZIP trae {len(entradas)} archivos (máximo {MAX_ENTRADAS_ZIP})")
            pdfs = [i for i in entradas if i.filename.lower().endswith(".pdf")]
            if sum(i.file_size for i in pdfs) > MAX_DESCOMPRIMIDO:
                return Texto("error", motivo=f"los PDF del ZIP pasan de {MAX_DESCOMPRIMIDO // MB} MB descomprimidos")
            if not pdfs:
                return Texto("no_aplica", motivo="el ZIP no trae PDF")
            # Se leen en memoria: el nombre de adentro es solo un dato, nunca una ruta en el disco.
            partes = []
            for info in pdfs:
                contenido = zf.read(info)
                partes.append(_texto_pdf(contenido, info.filename) if b"%PDF" in contenido[:1024]
                              else Texto("error", motivo=f"{info.filename} no es un PDF"))
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError) as exc:
        return Texto("error", motivo=f"el ZIP no se puede leer ({type(exc).__name__})")
    filas = [f for p in partes for f in p.filas]
    motivos = "; ".join(p.motivo for p in partes if p.motivo)
    paginas = sum(p.paginas for p in partes)
    if filas:
        return Texto("extraido", paginas, filas, motivos)
    if all(p.estado == "error" for p in partes):
        return Texto("error", paginas, motivo=motivos)
    return Texto("sin_texto", paginas, motivo=motivos or "los PDF del ZIP no tienen texto")


def extraer_texto(datos: bytes, extension: str) -> Texto:
    if extension == ".pdf":
        return _texto_pdf(datos, "")
    if extension == ".zip":
        return _texto_zip(datos)
    return Texto("no_aplica", motivo="se guarda sin extraer texto (Word, Excel u otro)")


# --- Registro ----------------------------------------------------------------------------------------------------

def _registrar(conn: sqlite3.Connection, nro: str, detalle_id: int, doc: dict, server: str, ahora: datetime,
               estado: str, motivo: str = "", datos: bytes | None = None, ruta: str | None = None,
               texto: Texto | None = None) -> int:
    with transaccion(conn):
        documento_id = conn.execute(
            "INSERT INTO tender_documents (nro_sicop, detalle_id, doc_seq, tipo_documento, nombre_documento,"
            " nombre_original, server_file, extension, tamano_bytes, sha256, ruta_local, registrado_en, estado,"
            " motivo, texto_estado, paginas) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nro, detalle_id, _t(doc.get("docFileSeqno")), _t(doc.get("fileTypeNm")), _t(doc.get("docNm")),
             _t(doc.get("clientFileNm")), server, Path(server).suffix.lower() or None,
             len(datos) if datos is not None else None, hashlib.sha256(datos).hexdigest() if datos else None, ruta,
             ahora.isoformat(timespec="seconds"), estado, motivo or None, texto.estado if texto else None,
             texto.paginas if texto else None)).lastrowid
        if texto is not None and estado == "guardado":
            conn.executemany("INSERT INTO tender_document_text (documento_id, archivo_interno, pagina, texto)"
                             " VALUES (?, ?, ?, ?)", [(documento_id, *fila) for fila in texto.filas])
    return documento_id


def _t(valor) -> str | None:
    return None if valor is None else str(valor)


def _mb_de_la_lista(doc: dict) -> Decimal | None:
    try:
        return Decimal(str(doc.get("fileSizeMb")))
    except (InvalidOperation, ValueError):
        return None


def guardar_documento(conn: sqlite3.Connection, settings: Settings, nro: str, detalle_id: int, doc: dict,
                      datos: bytes, ahora: datetime) -> ResultadoDocumento:
    """Revisa y guarda un documento ya descargado. El archivo se escribe solo si pasa la revisión."""
    server = str(doc["serverFileNm"])
    extension = Path(server).suffix.lower()
    seq, nombre = _t(doc.get("docFileSeqno")) or "", _t(doc.get("clientFileNm")) or server
    motivo = validar(datos, extension, settings.document_max_mb * MB)
    if motivo:
        estado = "omitido_tamano" if motivo.startswith("pesa") else "rechazado"
        _registrar(conn, nro, detalle_id, doc, server, ahora, estado, motivo, datos)
        return ResultadoDocumento(seq, nombre, estado, motivo=motivo)
    sha = hashlib.sha256(datos).hexdigest()
    igual = conn.execute("SELECT server_file FROM tender_documents WHERE nro_sicop = ? AND sha256 = ? AND"
                         " estado = 'guardado'", (nro, sha)).fetchone()
    if igual:
        motivo = f"mismo contenido que el documento ya guardado {igual[0]}: no se guarda otra vez"
        _registrar(conn, nro, detalle_id, doc, server, ahora, "duplicado", motivo, datos)
        return ResultadoDocumento(seq, nombre, "duplicado", motivo=motivo)
    texto = extraer_texto(datos, extension)
    carpeta = settings.documents_dir / nro
    carpeta.mkdir(parents=True, exist_ok=True)
    destino, temporal = carpeta / server, carpeta / f".{server}.parcial"
    temporal.write_bytes(datos)
    os.replace(temporal, destino)  # nunca queda un archivo a medias con el nombre final
    try:
        _registrar(conn, nro, detalle_id, doc, server, ahora, "guardado", texto.motivo, datos,
                   f"{nro}/{server}", texto)
    except sqlite3.Error:
        destino.unlink(missing_ok=True)
        raise
    return ResultadoDocumento(seq, nombre, "guardado", texto.estado, texto.motivo)


# --- Descarga con el navegador -------------------------------------------------------------------------------

class _EscuchaArchivos:
    """Guarda el cuerpo de los archivos que la página baja del almacén de SICOP, por su nombre final. Nunca guarda
    la dirección (lleva la clave temporal)."""

    def __init__(self) -> None:
        self.cuerpos: dict[str, bytes] = {}
        self.errores: dict[str, str] = {}
        self.bloqueo: str | None = None

    def __call__(self, respuesta) -> None:
        partes = urlsplit(respuesta.url)
        if not ALMACEN.match(partes.netloc):
            return
        nombre = partes.path.rsplit("/", 1)[-1]
        if respuesta.status in (403, 429):
            self.bloqueo = f"control no automatizable: el almacén de documentos respondió HTTP {respuesta.status}"
            return
        if respuesta.status != 200:
            self.errores[nombre] = f"el almacén de documentos respondió HTTP {respuesta.status}"
            return
        if nombre in self.cuerpos:  # la página lo pide dos veces (observado): basta el primero
            return
        try:
            self.cuerpos[nombre] = respuesta.body()
        except PlaywrightError:
            self.errores[nombre] = "no se pudo leer el archivo que llegó"


def _texto_exacto(texto) -> re.Pattern:
    """La celda con exactamente ese texto. Los espacios seguidos cuentan como uno (el navegador los junta: «2026  -
    Alquiler» se ve «2026 - Alquiler»)."""
    partes = str(texto).split()
    return re.compile(r"^\s*" + r"\s+".join(re.escape(p) for p in partes) + r"\s*$")


def _boton_descarga(page, doc: dict):
    """El botón de descarga (última columna) de la fila con el nombre del archivo y el nombre del documento. La celda
    del nombre no descarga nada, y la columna «No.» es el número de fila, no docFileSeqno (pruebas reales del
    2026-10-27). Si la tabla tiene páginas, avanza hasta hallar la fila. Si hay más de una fila con esos nombres o la
    fila no tiene exactamente un botón, lanza ValueError (no se adivina)."""
    archivo = _texto_exacto(doc.get("clientFileNm"))
    documento = _texto_exacto(doc.get("docNm")) if doc.get("docNm") else None
    # El contenedor (.first: el de afuera), no el <table> de adentro: los botones de página están fuera del <table>.
    tabla = page.locator(".p-datatable, table").filter(has=page.get_by_text("Nombre del documento")).first

    def buscar_hacia(boton: re.Pattern):
        for _ in range(MAX_PAGINAS_TABLA):
            fila = page.locator("tr").filter(has=page.locator("td").filter(has_text=archivo))
            if documento is not None:
                fila = fila.filter(has=page.locator("td").filter(has_text=documento))
            if fila.count() > 1:
                raise ValueError(f"hay {fila.count()} filas con el mismo nombre de archivo: no se elige ninguna")
            if fila.count():
                botones = fila.first.get_by_role("button")
                if botones.count() != 1:
                    raise ValueError(f"la fila del documento tiene {botones.count()} botones y se esperaba 1 "
                                     "(el de descarga): SICOP pudo cambiar la tabla")
                return botones
            mover = tabla.get_by_role("button", name=boton)
            if not mover.count() or not mover.first.is_enabled():
                return None
            mover.first.click()
            page.wait_for_timeout(500)
        return None

    # Primero hacia adelante; si no estaba, vuelve a la primera página y busca otra vez desde ahí.
    boton = buscar_hacia(re.compile(r"siguiente|next", re.IGNORECASE))
    if boton is None:
        anterior = tabla.get_by_role("button", name=re.compile(r"anterior|previous", re.IGNORECASE))
        for _ in range(MAX_PAGINAS_TABLA):
            if not anterior.count() or not anterior.first.is_enabled():
                break
            anterior.first.click()
            page.wait_for_timeout(500)
        boton = buscar_hacia(re.compile(r"siguiente|next", re.IGNORECASE))
    return boton


def descargar_documentos(page, contexto, conn: sqlite3.Connection, settings: Settings, nro: str, detalle_id: int,
                         documentos: list[dict], resultados: list[ResultadoDocumento], *, revisar: Callable[[], None],
                         dormir: Callable[[float], None], reloj: Callable[[], datetime],
                         avisar: Callable[[str], None] = lambda _: None,
                         espera_ms: int = ESPERA_DOCUMENTO_MS) -> None:
    """Baja y guarda los documentos de la ficha abierta, uno por uno, con pausa. Un fallo de un documento queda
    registrado y se sigue con el siguiente. Ante CAPTCHA o bloqueo lanza _Control. `resultados` se va llenando
    (aunque se detenga a la mitad)."""
    escucha = _EscuchaArchivos()
    contexto.on("response", escucha)
    nuevas: list = []
    contexto.on("page", lambda pg: nuevas.append(pg))  # Playwright no acepta un método de lista directo
    tope = settings.documents_max_mb_per_tender * MB

    def control(pg=page) -> None:
        revisar()
        motivo = escucha.bloqueo or detectar_control(pg)
        if motivo:
            raise _Control(motivo)

    for doc in documentos:  # en el orden de SICOP, que es el de la tabla: así se avanza página por página
        seq, nombre, server = _t(doc.get("docFileSeqno")) or "", _t(doc.get("clientFileNm")) or "", \
            _t(doc.get("serverFileNm")) or ""
        ahora = reloj()
        if not SERVER_FILE.match(server):
            motivo = "el nombre del archivo en el servidor de SICOP no tiene la forma esperada: no se pide"
            _registrar(conn, nro, detalle_id, doc, server or "?", ahora, "rechazado", motivo)
            resultados.append(ResultadoDocumento(seq, nombre, "rechazado", motivo=motivo))
            continue
        if conn.execute("SELECT 1 FROM tender_documents WHERE nro_sicop = ? AND server_file = ? AND"
                        " estado = 'guardado'", (nro, server)).fetchone():
            resultados.append(ResultadoDocumento(seq, nombre, "ya_guardado", motivo="ya estaba guardado"))
            continue
        mb = _mb_de_la_lista(doc)
        if mb is not None and mb > settings.document_max_mb:
            motivo = f"SICOP dice que pesa {mb} MB y el máximo es {settings.document_max_mb} MB: no se pide"
            _registrar(conn, nro, detalle_id, doc, server, ahora, "omitido_tamano", motivo)
            resultados.append(ResultadoDocumento(seq, nombre, "omitido_tamano", motivo=motivo))
            continue
        guardado = conn.execute("SELECT coalesce(sum(tamano_bytes), 0) FROM tender_documents WHERE nro_sicop = ?"
                                " AND estado = 'guardado'", (nro,)).fetchone()[0]
        if mb is not None and guardado + mb * MB > tope:
            motivo = (f"el cartel ya tiene {guardado / MB:.1f} MB guardados y con este pasaría el tope de "
                      f"{settings.documents_max_mb_per_tender} MB: no se pide")
            _registrar(conn, nro, detalle_id, doc, server, ahora, "omitido_tope", motivo)
            resultados.append(ResultadoDocumento(seq, nombre, "omitido_tope", motivo=motivo))
            continue

        avisar(f"  Pausa de {settings.enrich_delay_seconds} s; después: documento {seq} ({nombre})…")
        dormir(settings.enrich_delay_seconds)
        try:
            boton = _boton_descarga(page, doc)
            motivo = None if boton is not None else \
                "no se encontró su fila en la tabla de documentos: SICOP pudo cambiar la página"
        except ValueError as exc:
            boton, motivo = None, str(exc)
        if boton is None:
            _registrar(conn, nro, detalle_id, doc, server, reloj(), "fallo", motivo)
            resultados.append(ResultadoDocumento(seq, nombre, "fallo", motivo=motivo))
            continue
        escucha.cuerpos.pop(server, None)
        escucha.errores.pop(server, None)
        boton.click()
        limite = time.monotonic() + espera_ms / 1000
        while server not in escucha.cuerpos and server not in escucha.errores:
            control()
            if time.monotonic() > limite:
                break
            page.wait_for_timeout(200)
        for pg in list(nuevas):  # la página abre una pestaña con el porcentaje de descarga
            try:
                control(pg)
            finally:
                nuevas.remove(pg)
                try:
                    pg.close()
                except PlaywrightError:
                    pass
        control()
        if server not in escucha.cuerpos:
            motivo = escucha.errores.get(server) or f"el archivo no llegó en {espera_ms // 1000} s"
            _registrar(conn, nro, detalle_id, doc, server, reloj(), "fallo", motivo)
            resultados.append(ResultadoDocumento(seq, nombre, "fallo", motivo=motivo))
            continue
        resultados.append(guardar_documento(conn, settings, nro, detalle_id, doc, escucha.cuerpos.pop(server),
                                            reloj()))
