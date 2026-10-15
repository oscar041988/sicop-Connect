"""Importador del reporte 2 «Detalle pliego de condiciones» → tabla tenders.

El mapeo columna → campo está en docs/MAPEO_DATOS.md. Lo común (idempotencia, copia del original,
raw_snapshots, rechazos) está en app/importers/comun.py. Un cartel modificado se actualiza en
tenders y su versión anterior queda en raw_snapshots.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.importers.comun import (HORA_CR, ORIGENES, Fila, FilaRechazada, ImportacionError, Rechazo,  # noqa: F401
                                 Resultado, exigir_digitos, importar_reporte, upsert)
from app.importers.csv_reader import parse_csv

# Encabezado real del archivo → campo de tenders (docs/MAPEO_DATOS.md, reporte 2).
COLUMNAS = {
    "Número SICOP": "nro_sicop",
    "Numero de procedimiento": "nro_procedimiento",
    "Cédula": "institution_cedula",
    "Descripción": "descripcion",
    "Fecha Publicación": "fecha_publicacion",
    "Fecha Inicio Recepción": "fecha_inicio_recepcion",
    "Fecha Cierre Recepción": "fecha_cierre_recepcion",
    "Tipo de procedimiento": "tipo_procedimiento",
}
COLUMNAS_FECHA = ("Fecha Publicación", "Fecha Inicio Recepción", "Fecha Cierre Recepción")
FORMATO_FECHA = "%d/%m/%Y %H:%M:%S"

ADV_SIN_RECEPCION = "Sin fechas de recepción"
ADV_INICIO_ANTES = "Inicio de recepción más de 1 hora antes de la publicación"
# Decisión 2026-10-08 (Ivania): en los datos reales, 107 de 108 casos de «inicio antes de la publicación»
# son de 0 a 14 minutos (el inicio se fija al minuto y el sistema publica segundos después). Solo se
# advierte por encima de este margen.
MARGEN_INICIO_ANTES = timedelta(hours=1)


def _fecha(columna: str, valor: str) -> datetime | None:
    if not valor:
        return None
    try:
        return datetime.strptime(valor, FORMATO_FECHA).replace(tzinfo=HORA_CR)
    except ValueError:
        raise FilaRechazada(f"«{columna}» con formato inválido ({valor!r}); se espera dd/mm/aaaa hh:mm:ss")


def _validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
    nro = exigir_digitos("Número SICOP", fila["Número SICOP"])
    fechas = {c: _fecha(c, fila[c]) for c in COLUMNAS_FECHA}
    campos: dict[str, str | None] = {campo: fila[col] for col, campo in COLUMNAS.items()}
    for columna, valor in fechas.items():
        campos[COLUMNAS[columna]] = valor.isoformat() if valor else None

    if fechas["Fecha Inicio Recepción"] is None and fechas["Fecha Cierre Recepción"] is None:
        resultado.advertir(ADV_SIN_RECEPCION, linea)
    inicio, publicacion = fechas["Fecha Inicio Recepción"], fechas["Fecha Publicación"]
    if inicio and publicacion and publicacion - inicio > MARGEN_INICIO_ANTES:
        resultado.advertir(ADV_INICIO_ANTES, linea)
    return Fila(nro, campos, fila)


def _guardar(conn: sqlite3.Connection, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
    campos = {k: v for k, v in fila.campos.items() if k != "nro_sicop"}
    return upsert(conn, "tenders", {"nro_sicop": fila.clave}, campos, content_hash, momento,
                  al_crear={"first_import_id": import_id}, siempre={"last_import_id": import_id})


def _periodo(filas: list[Fila]) -> tuple[str | None, str | None]:
    publicaciones = sorted(f.campos["fecha_publicacion"] for f in filas if f.campos["fecha_publicacion"])
    return (publicaciones[0][:10], publicaciones[-1][:10]) if publicaciones else (None, None)


def import_carteles(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                    source_run_id: int | None = None) -> Resultado:
    """Importa un CSV de carteles. La conexión debe venir de app.database.connect (base migrada)."""
    raw = path.read_bytes()
    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(raw), report="carteles",
        entidad="cartel", origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS, nombre_clave="Número SICOP",
        validar=_validar, guardar=_guardar, periodo=_periodo, source_run_id=source_run_id,
    )
