"""Recibir un archivo subido desde el panel, igual para el expediente y el perfil de Hermatix.

* Se copia a un temporal dentro de la carpeta de destino, cortando apenas pasa el límite: nunca se lee de más.
* Se calcula su huella SHA-256 mientras se copia.
* El nombre que manda el navegador solo se muestra (nombre_para_mostrar); nunca se usa como ruta.
Quien llama revisa el contenido (la firma), decide el nombre final y mueve el temporal con os.replace.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Iterator

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
class Recibido:
    temporal: Path
    sha256: str
    tamano: int


def nombre_para_mostrar(original: str | None) -> str:
    """«C:\\Users\\…\\Pliego final.pdf» → «Pliego final.pdf»: solo el último tramo, sin caracteres de control."""
    base = PureWindowsPath(PurePosixPath(original or "").name).name
    base = _CONTROL.sub("", unicodedata.normalize("NFC", base)).strip()
    if len(base) > LARGO_MAXIMO_NOMBRE:
        raiz, ext = os.path.splitext(base)
        base = raiz[:LARGO_MAXIMO_NOMBRE - len(ext)] + ext
    return base


def primeros_bytes(ruta: Path, n: int = 8) -> bytes:
    with open(ruta, "rb") as f:
        return f.read(n)


@contextmanager
def recibir(origen: BinaryIO, carpeta: Path, limite: int, aviso_limite: str) -> Iterator[Recibido]:
    """Copia `origen` a un temporal de `carpeta` (máximo `limite` bytes). El temporal se borra al salir, salvo que
    quien llama ya lo haya movido con os.replace."""
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / f".subiendo-{secrets.token_hex(8)}"
    huella, tamano = hashlib.sha256(), 0
    try:
        with open(temporal, "xb") as salida:
            while bloque := origen.read(BLOQUE):
                tamano += len(bloque)
                if tamano > limite:
                    raise ArchivoMuyGrande(aviso_limite)
                huella.update(bloque)
                salida.write(bloque)
        if tamano == 0:
            raise ArchivoInvalido("El archivo está vacío.")
        yield Recibido(temporal, huella.hexdigest(), tamano)
    finally:
        temporal.unlink(missing_ok=True)
