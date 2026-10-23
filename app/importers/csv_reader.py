"""Lectura de CSV de SICOP sin convertir valores: todo queda como texto."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

SEPARADORES = (";", ",", "\t")


class ImportacionError(Exception):
    """El archivo completo no se puede importar (nada se escribe en la base). Se usa desde app.importers.comun;
    vive aquí porque leer el archivo ya puede fallar así."""


@dataclass
class CsvFile:
    encoding: str
    delimiter: str
    header: list[str]
    rows: list[tuple[int, list[str]]]  # (línea física en el archivo, valores)
    warnings: list[str] = field(default_factory=list)


def decode(raw: bytes) -> tuple[str, str, list[str]]:
    """Devuelve (texto, codificación, advertencias). UTF-8 primero; si falla, cp1252.

    Algunos bytes (0x81, 0x8D, 0x8F, 0x90, 0x9D) no existen en cp1252: un archivo así no se puede leer y se
    rechaza con ImportacionError (antes salía un error 500 en el panel)."""
    try:
        return raw.decode("utf-8-sig"), "utf-8", []
    except UnicodeDecodeError:
        aviso = "El archivo no es UTF-8; se leyó como cp1252 (Windows). ¿Pasó por Excel?"
        try:
            return raw.decode("cp1252"), "cp1252", [aviso]
        except UnicodeDecodeError as exc:
            raise ImportacionError(
                f"no se puede leer el texto: no es UTF-8 ni cp1252 (byte 0x{raw[exc.start]:02X} en la posición "
                f"{exc.start}). No parece un reporte de SICOP o está dañado: vuelve a descargarlo") from None


def read_csv(path: Path) -> CsvFile:
    return parse_csv(path.read_bytes())


def parse_csv(raw: bytes) -> CsvFile:
    texto, encoding, warnings = decode(raw)
    primera = texto.split("\n", 1)[0]
    delimiter = max(SEPARADORES, key=primera.count)

    reader = csv.reader(io.StringIO(texto, newline=""), delimiter=delimiter)
    header = next(reader, [])
    rows: list[tuple[int, list[str]]] = []
    for valores in reader:
        # line_num cuenta líneas físicas: una celda con salto de línea no desordena la numeración.
        if valores:
            rows.append((reader.line_num, valores))
    return CsvFile(encoding, delimiter, header, rows, warnings)
