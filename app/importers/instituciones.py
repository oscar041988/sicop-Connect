"""Importador del reporte 11 «Instituciones compradoras» → tabla institutions.

Relación cartel → institución por cédula (tenders.institution_cedula = institutions.cedula).
Solo se guarda lo decidido en docs/MAPEO_DATOS.md: cédula y nombre. `Representante` es el nombre
de una persona: no se guarda en la base (tampoco en raw_snapshots); queda solo en la copia del original.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.importers.comun import Fila, Resultado, exigir_digitos, importar_reporte, upsert
from app.importers.csv_reader import parse_csv

COLUMNAS = {"Cédula": "cedula", "Institución": "nombre"}
NO_SE_GUARDA = ("Representante",)

ADV_NOMBRE_VACIO = "Institución sin nombre"


def _validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
    cedula = exigir_digitos("Cédula", fila["Cédula"])
    if not fila["Institución"].strip():
        resultado.advertir(ADV_NOMBRE_VACIO, linea)
    original = {k: v for k, v in fila.items() if k not in NO_SE_GUARDA}
    return Fila(cedula, {"nombre": fila["Institución"]}, original)


def _guardar(conn: sqlite3.Connection, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
    return upsert(conn, "institutions", {"cedula": fila.clave}, fila.campos, content_hash, momento)


def import_instituciones(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                         source_run_id: int | None = None) -> Resultado:
    raw = path.read_bytes()
    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(raw), report="instituciones",
        entidad="institucion", origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS, nombre_clave="Cédula",
        validar=_validar, guardar=_guardar, source_run_id=source_run_id,
    )
