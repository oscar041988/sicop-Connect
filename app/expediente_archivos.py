"""Gestor de documentos, paso 2: subir y bajar archivos del expediente (docs/GESTOR_DOCUMENTOS.md).

* Lo suben y lo bajan quienes entran al expediente (seguimiento.puede_entrar: el encargado vigente y los
  administradores); eso lo revisa la ruta. Así, en un traspaso, el encargado nuevo baja todo lo del anterior.
* Tipos: PDF, Word (.docx, .doc), Excel (.xlsx, .xls) y ZIP. Se comprueba el CONTENIDO (su firma), no solo la
  extensión: un .exe renombrado a .pdf no empieza con «%PDF-» y se rechaza.
* Tamaño máximo: EXPEDIENTE_MAX_MB (10 por ahora). Se corta al copiar: nunca se lee más que el límite.
* Se guarda en EXPEDIENTES_DIR/<N.º SICOP>/<sha256>.<extensión>. El nombre que manda el navegador solo se muestra;
  nunca se usa como ruta.
* Nada se borra: cada subida agrega una fila (migración 0027) y una línea en audit_log. El mismo archivo (misma
  huella) no entra dos veces en el mismo expediente.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO

from app import historial, visor
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

TIPOS = {".pdf": "PDF", ".docx": "Word", ".doc": "Word", ".xlsx": "Excel", ".xls": "Excel", ".zip": "ZIP"}
MIME = {".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel", ".zip": "application/zip"}
FIRMA_PDF = b"%PDF-"
FIRMA_ZIP = b"PK\x03\x04"
FIRMA_OLE = bytes.fromhex("D0CF11E0A1B11AE1")   # Word y Excel viejos (.doc, .xls)
BLOQUE = 1024 * 1024
LARGO_MAXIMO_NOMBRE = 150
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class ArchivoInvalido(ValueError):
    """El archivo no se acepta; el mensaje es el que verá la persona."""


class ArchivoMuyGrande(ArchivoInvalido):
    pass


class YaEsta(ArchivoInvalido):
    pass


@dataclass(frozen=True)
class Archivo:
    id: int
    nombre: str
    extension: str
    tamano: int
    sha256: str
    subido_por: str
    fecha: str

    @property
    def tipo(self) -> str:
        return TIPOS[self.extension]

    @property
    def vista(self) -> str | None:
        """'pdf', 'excel' o 'zip' si se puede «Ver» (app/visor.py); Word y .xls solo se descargan."""
        return visor.vista(f"x{self.extension}")


def nombre_para_mostrar(original: str | None) -> str:
    """«C:\\Users\\…\\Pliego final.pdf» → «Pliego final.pdf»: solo el último tramo, sin caracteres de control."""
    base = PureWindowsPath(PurePosixPath(original or "").name).name
    base = _CONTROL.sub("", unicodedata.normalize("NFC", base)).strip()
    if len(base) > LARGO_MAXIMO_NOMBRE:
        raiz, ext = os.path.splitext(base)
        base = raiz[:LARGO_MAXIMO_NOMBRE - len(ext)] + ext
    return base


def extension_de(nombre: str) -> str:
    extension = PurePosixPath(nombre).suffix.lower()
    if extension not in TIPOS:
        raise ArchivoInvalido(f"Se aceptan PDF, Word (.docx, .doc), Excel (.xlsx, .xls) y ZIP (se recibió"
                              f" «{extension or 'sin extensión'}»).")
    return extension


def contenido_valido(ruta: Path, extension: str) -> bool:
    """True si el contenido del archivo es del tipo que dice su extensión (la firma de sus primeros bytes)."""
    with open(ruta, "rb") as f:
        inicio = f.read(8)
    if extension == ".pdf":
        return inicio.startswith(FIRMA_PDF)
    if extension in (".doc", ".xls"):
        return inicio.startswith(FIRMA_OLE)
    if not inicio.startswith(FIRMA_ZIP):
        return False
    try:
        with zipfile.ZipFile(ruta) as zf:
            nombres = set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False
    if extension == ".docx":   # un .docx es un ZIP con las piezas de Word
        return "[Content_Types].xml" in nombres and "word/document.xml" in nombres
    if extension == ".xlsx":
        return "[Content_Types].xml" in nombres and "xl/workbook.xml" in nombres
    return True


def _seguimiento_id(conn: sqlite3.Connection, nro_sicop: str) -> int:
    fila = conn.execute("SELECT id FROM seguimientos WHERE nro_sicop = ?", (nro_sicop,)).fetchone()
    if fila is None:
        raise ArchivoInvalido(f"El cartel {nro_sicop} no está en seguimiento: primero «Dar seguimiento».")
    return fila[0]


def _nombre_activo(conn: sqlite3.Connection, user_id: int | None) -> str:
    fila = conn.execute("SELECT coalesce(nombre, email) FROM users WHERE id = ? AND active = 1",
                        (user_id,)).fetchone()
    if fila is None:
        raise ArchivoInvalido("Tu usuario no existe o está desactivado. Vuelve a iniciar sesión.")
    return fila[0]


def _carpeta(base: Path, nro_sicop: str) -> Path:
    if not nro_sicop.isdigit():
        raise ArchivoInvalido("El Número SICOP solo lleva dígitos.")
    carpeta = base / nro_sicop
    if carpeta.resolve().parent != base.resolve():   # comprobación final: nunca fuera de EXPEDIENTES_DIR
        raise ArchivoInvalido("Número SICOP no válido.")
    return carpeta


def guardar(conn: sqlite3.Connection, base: Path, nro_sicop: str, origen: BinaryIO, nombre_original: str | None,
            limite: int, quien: Quien, ahora: datetime) -> Archivo:
    """Revisa y guarda un archivo subido al expediente. Lanza ArchivoInvalido (o ArchivoMuyGrande, YaEsta)."""
    nombre = nombre_para_mostrar(nombre_original)
    if not nombre:
        raise ArchivoInvalido("Elige un archivo.")
    extension = extension_de(nombre)
    seguimiento_id = _seguimiento_id(conn, nro_sicop)
    autor = _nombre_activo(conn, quien.user_id)
    carpeta = _carpeta(base, nro_sicop)
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / f".subiendo-{secrets.token_hex(8)}"
    huella, tamano = hashlib.sha256(), 0
    try:
        with open(temporal, "xb") as salida:
            while bloque := origen.read(BLOQUE):
                tamano += len(bloque)
                if tamano > limite:
                    raise ArchivoMuyGrande(f"El archivo supera el límite de {limite // (1024 * 1024)} MB"
                                           " (EXPEDIENTE_MAX_MB).")
                huella.update(bloque)
                salida.write(bloque)
        if tamano == 0:
            raise ArchivoInvalido("El archivo está vacío.")
        if not contenido_valido(temporal, extension):
            raise ArchivoInvalido(f"El contenido de «{nombre}» no es un {TIPOS[extension]} de verdad: no coincide"
                                  f" con la extensión {extension}.")
        sha = huella.hexdigest()
        ya = conn.execute("SELECT nombre FROM seguimiento_archivos WHERE seguimiento_id = ? AND sha256 = ?",
                          (seguimiento_id, sha)).fetchone()
        if ya:
            raise YaEsta(f"Ese archivo ya está en el expediente (como «{ya[0]}»): no se duplica.")
        destino = carpeta / f"{sha}{extension}"
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
    momento = ahora.astimezone(HORA_CR).isoformat(timespec="seconds")
    try:
        with transaccion(conn):   # la fila y su línea del historial, juntas
            archivo_id = conn.execute(
                "INSERT INTO seguimiento_archivos (seguimiento_id, nombre, extension, tamano, sha256, ruta, subido_por,"
                " subido_por_nombre, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (seguimiento_id, nombre, extension, tamano, sha, f"{nro_sicop}/{destino.name}", quien.user_id, autor,
                 momento)).lastrowid
            historial.registrar(conn, quien, "subir_archivo", f"{nro_sicop}: {nombre} ({tamano} bytes)")
    except sqlite3.IntegrityError:
        # Dos subidas del mismo archivo a la vez: la otra ya lo anotó y el archivo en disco es el mismo (misma huella).
        raise YaEsta("Ese archivo ya está en el expediente: no se duplica.") from None
    return Archivo(archivo_id, nombre, extension, tamano, sha, autor, momento)


def listar(conn: sqlite3.Connection, nro_sicop: str) -> list[Archivo]:
    """Los archivos del expediente, del más reciente al más viejo."""
    return [Archivo(*fila) for fila in conn.execute(
        "SELECT a.id, a.nombre, a.extension, a.tamano, a.sha256, a.subido_por_nombre, a.created_at"
        " FROM seguimiento_archivos a JOIN seguimientos s ON s.id = a.seguimiento_id WHERE s.nro_sicop = ?"
        " ORDER BY a.id DESC", (nro_sicop,))]


def obtener(conn: sqlite3.Connection, base: Path, nro_sicop: str, archivo_id: int) -> tuple[Path, Archivo] | None:
    """La ruta en disco y los datos de un archivo de ESTE expediente, o None si no existe."""
    fila = conn.execute(
        "SELECT a.id, a.nombre, a.extension, a.tamano, a.sha256, a.subido_por_nombre, a.created_at, a.ruta"
        " FROM seguimiento_archivos a JOIN seguimientos s ON s.id = a.seguimiento_id"
        " WHERE s.nro_sicop = ? AND a.id = ?", (nro_sicop, archivo_id)).fetchone()
    if fila is None:
        return None
    ruta = base / fila[7]
    if ruta.resolve().parent != (base / nro_sicop).resolve() or not ruta.is_file():
        return None
    return ruta, Archivo(*fila[:7])
