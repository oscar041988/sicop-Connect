"""Importador del reporte 10.2 «Catálogo de bienes y servicios» → tabla catalog_items.

El portal entrega un ZIP por código de clasificación (8 dígitos) con tres CSV. Se usa
`Codigos Identificacion.csv`; los otros dos quedan en la copia del original.

Observado en los archivos reales (2026-10-08, docs/MAPEO_DATOS.md): `Código identificación` trae
solo 8 dígitos. El código de 16 que usan las líneas es clasificación (8) + identificación (8),
como dice el diccionario oficial; se comprobó con las 36 líneas de las 3 clasificaciones descargadas.
"""

from __future__ import annotations

import io
import sqlite3
import zipfile
from pathlib import Path

from app.importers.comun import Fila, ImportacionError, Resultado, exigir_digitos, importar_reporte, upsert
from app.importers.csv_reader import parse_csv

ARCHIVO_EN_ZIP = "Codigos Identificacion.csv"
COLUMNAS = ("Codigo Clasificación", "Código identificación", "Nombre Identificacion", "En Uso")


def _leer(path: Path) -> bytes:
    """Bytes del CSV de identificación, venga suelto o dentro del ZIP del portal."""
    if not zipfile.is_zipfile(path):
        return path.read_bytes()
    with zipfile.ZipFile(path) as zf:
        if ARCHIVO_EN_ZIP not in zf.namelist():
            raise ImportacionError(f"El ZIP no contiene {ARCHIVO_EN_ZIP!r} (trae: {', '.join(zf.namelist())})")
        return zf.read(ARCHIVO_EN_ZIP)


def _validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
    clasificacion = exigir_digitos("Codigo Clasificación", fila["Codigo Clasificación"], longitud=8)
    identificacion = exigir_digitos("Código identificación", fila["Código identificación"], longitud=8)
    codigo = clasificacion + identificacion
    return Fila(codigo, {"codigo_clasificacion": clasificacion, "nombre": fila["Nombre Identificacion"]}, fila)


def _guardar(conn: sqlite3.Connection, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
    return upsert(conn, "catalog_items", {"codigo_identificacion": fila.clave}, fila.campos, content_hash, momento)


def import_catalogo(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                    source_run_id: int | None = None) -> Resultado:
    """Importa un ZIP (o CSV) del catálogo. Se puede importar uno por cada clasificación descargada."""
    raw = path.read_bytes()  # el hash y la copia son del archivo tal como se descargó
    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(_leer(path)), report="catalogo",
        entidad="catalogo", origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS,
        nombre_clave="Código (clasificación + identificación)", validar=_validar, guardar=_guardar,
        source_run_id=source_run_id,
    )
