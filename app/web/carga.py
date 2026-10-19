"""Carga de archivos desde el panel: se guarda en INCOMING_DIR con nombre seguro y se importa como en la CLI.

Tres defensas antes de importar:
* Tamaño: se rechaza si la petición declara más de UPLOAD_MAX_MB y, por si no lo declara, al copiar.
* Extensión: .csv para todos los reportes; .zip solo para el catálogo (el portal lo entrega así).
* Nombre: el del navegador no se usa tal cual; se limpia y la carpeta la decide el programa.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO

from fastapi import Request
from fastapi.responses import Response

from app.config import load_settings
from app.importers.comun import HORA_CR

RUTA = "/cargar"
EXTENSIONES = {"carteles": (".csv",), "lineas": (".csv",), "catalogo": (".csv", ".zip"),
               "instituciones": (".csv",)}
MARGEN_FORMULARIO = 64 * 1024  # los otros campos del formulario también ocupan bytes
BLOQUE = 1024 * 1024
LARGO_MAXIMO_NOMBRE = 100
_NO_PERMITIDO = re.compile(r"[^A-Za-z0-9._-]+")


class CargaInvalida(Exception):
    """El archivo no se acepta; el mensaje es el que verá la usuaria."""


class ArchivoMuyGrande(CargaInvalida):
    pass


def limite_bytes() -> int:
    return load_settings().upload_max_bytes


def en_megas(limite: int) -> str:
    return f"{round(limite / (1024 * 1024), 3):g}"


def mensaje_limite(limite: int) -> str:
    return f"El archivo supera el límite de {en_megas(limite)} MB."


def nombre_seguro(original: str, extension: str) -> str:
    """«../../Detalles líneas.CSV» → «Detalles_lineas.csv»: sin carpetas, tildes ni caracteres raros."""
    # El navegador puede mandar la ruta completa (C:\\Users\\…\\archivo.csv): se toma solo el último tramo.
    base = PureWindowsPath(PurePosixPath(original or "").name).name
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    raiz = base[: -len(extension)] if base.lower().endswith(extension) else base
    raiz = _NO_PERMITIDO.sub("_", raiz).strip("._-")[:LARGO_MAXIMO_NOMBRE] or "archivo"
    return raiz + extension


def extension_valida(nombre: str, reporte: str) -> str:
    permitidas = EXTENSIONES[reporte]
    extension = PurePosixPath(PureWindowsPath(nombre or "").name).suffix.lower()
    if extension not in permitidas:
        raise CargaInvalida(f"El reporte «{reporte}» acepta archivos {' o '.join(permitidas)}"
                            f" (se recibió «{extension or 'sin extensión'}»).")
    return extension


def guardar_subida(origen: BinaryIO, nombre_original: str, reporte: str, carpeta: Path, limite: int) -> Path:
    """Copia el archivo subido a la carpeta de entrada sin pasar del límite. Devuelve la ruta guardada."""
    extension = extension_valida(nombre_original, reporte)
    momento = datetime.now(HORA_CR).strftime("%Y%m%d-%H%M%S")
    # Fecha y un sufijo aleatorio delante: dos subidas del mismo nombre nunca se pisan.
    destino = carpeta / f"{momento}-{secrets.token_hex(3)}_{nombre_seguro(nombre_original, extension)}"
    carpeta.mkdir(parents=True, exist_ok=True)
    if destino.resolve().parent != carpeta.resolve():  # comprobación final: nunca fuera de la carpeta
        raise CargaInvalida("Nombre de archivo no válido.")
    copiado = 0
    try:
        with open(destino, "xb") as salida:  # «x»: falla si ya existe, nunca sobrescribe
            while bloque := origen.read(BLOQUE):
                copiado += len(bloque)
                if copiado > limite:
                    raise ArchivoMuyGrande(mensaje_limite(limite))
                salida.write(bloque)
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    if copiado == 0:
        destino.unlink()
        raise CargaInvalida("El archivo está vacío.")
    return destino


async def limitar_tamano(request: Request, call_next) -> Response:
    """Middleware: rechaza una subida demasiado grande antes de recibirla, si la petición declara su tamaño."""
    if request.method == "POST" and request.url.path == RUTA:
        declarado = request.headers.get("content-length", "")
        limite = limite_bytes()
        if declarado.isdigit() and int(declarado) > limite + MARGEN_FORMULARIO:
            return Response(mensaje_limite(limite), status_code=413, media_type="text/plain; charset=utf-8")
    return await call_next(request)
