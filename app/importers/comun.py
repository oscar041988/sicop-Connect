"""Lo que comparten todos los importadores de reportes SICOP.

Cada importador define sus columnas, cómo validar una fila y cómo guardarla; este módulo hace el resto:
* Idempotencia: el mismo archivo (mismo hash) no se importa dos veces.
* El archivo original se copia a RAW_DATA_DIR y cada fila aceptada se guarda tal cual en raw_snapshots.
* Rechazos con línea y motivo; advertencias agrupadas por tipo (la fila se acepta).
* Todo en una transacción: o se escribe la importación completa o nada.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

from app.importers.csv_reader import CsvFile

ORIGENES = ("real", "sintetico", "simulado")

# Confirmado (MAPEO_DATOS.md, 2026-10-09): las fechas de SICOP están en hora de Costa Rica.
# Costa Rica no tiene horario de verano, así que un desfase fijo de -6 h es exacto
# y no requiere la base de zonas horarias (en Windows haría falta instalar tzdata).
HORA_CR = timezone(timedelta(hours=-6), "America/Costa_Rica")

_NOTACION_CIENTIFICA = re.compile(r"^-?\d+(?:[.,]\d+)?[Ee][+-]?\d+$")
SOLO_DIGITOS = re.compile(r"^[0-9]+$")


class ImportacionError(Exception):
    """El archivo completo no se puede importar (nada se escribe en la base)."""


class FilaRechazada(Exception):
    """La fila no se importa; el mensaje es el motivo que verá la usuaria."""


@dataclass
class Rechazo:
    linea: int
    motivo: str


@dataclass
class Fila:
    """Fila validada: clave natural, campos para la tabla y la fila original para raw_snapshots."""
    clave: str
    campos: dict[str, str | None]
    original: dict[str, str]


@dataclass
class Resultado:
    archivo: str
    file_hash: str
    encoding: str = ""
    delimiter: str = ""
    leidas: int = 0
    nuevas: int = 0
    actualizadas: int = 0
    sin_cambios: int = 0
    huerfanas: int = 0  # válidas, pero sin registro padre: solo quedan en raw_snapshots
    rechazos: list[Rechazo] = field(default_factory=list)
    advertencias: dict[str, list[int]] = field(default_factory=dict)  # tipo → líneas
    avisos_archivo: list[str] = field(default_factory=list)
    import_id: int | None = None
    ya_importado: int | None = None  # id de la importación anterior del mismo archivo
    copia_original: Path | None = None
    periodo: tuple[str | None, str | None] = (None, None)  # fechas de publicación (solo carteles)

    @property
    def aceptadas(self) -> int:
        return self.nuevas + self.actualizadas + self.sin_cambios + self.huerfanas

    def advertir(self, tipo: str, linea: int) -> None:
        self.advertencias.setdefault(tipo, []).append(linea)


def ahora() -> str:
    return datetime.now(HORA_CR).isoformat(timespec="seconds")


def exigir_digitos(columna: str, valor: str, longitud: int | None = None) -> str:
    """Valida un identificador como texto de dígitos (con su longitud exacta si se indica)."""
    if not valor:
        raise FilaRechazada(f"«{columna}» vacío")
    if not SOLO_DIGITOS.match(valor):
        raise FilaRechazada(f"«{columna}» no numérico ({valor!r})")
    if longitud is not None and len(valor) != longitud:
        raise FilaRechazada(f"«{columna}» con {len(valor)} dígitos ({valor}); se esperan {longitud}")
    return valor


def _copiar_original(raw: bytes, nombre: str, file_hash: str, raw_dir: Path) -> Path:
    destino = raw_dir / "importados" / f"{file_hash[:16]}_{nombre}"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(raw)
    return destino


def upsert(conn: sqlite3.Connection, tabla: str, clave: dict[str, str], campos: dict[str, str | None],
           content_hash: str, momento: str, al_crear: dict | None = None, siempre: dict | None = None) -> str:
    """Inserta o actualiza una fila por su clave natural. Nunca borra (las revisiones humanas no se tocan).

    Devuelve 'nueva', 'actualizada' o 'sin_cambios'. `tabla` y los nombres de columna son constantes
    del código, nunca vienen del archivo.
    """
    siempre = siempre or {}
    donde = " AND ".join(f"{c} = :k_{c}" for c in clave)
    params = {**{f"k_{c}": v for c, v in clave.items()}, **campos, **siempre,
              "content_hash": content_hash, "momento": momento}
    actual = conn.execute(f"SELECT content_hash FROM {tabla} WHERE {donde}", params).fetchone()
    if actual is None:
        valores = {**clave, **campos, **(al_crear or {}), **siempre,
                   "content_hash": content_hash, "first_seen": momento, "last_seen": momento}
        columnas = ", ".join(valores)
        marcas = ", ".join(f":{c}" for c in valores)
        conn.execute(f"INSERT INTO {tabla} ({columnas}) VALUES ({marcas})", valores)
        return "nueva"
    if actual[0] == content_hash:
        cambios = ", ".join(["last_seen = :momento", *(f"{c} = :{c}" for c in siempre)])
        estado = "sin_cambios"
    else:
        # UPDATE (nunca REPLACE): la fila no se borra, así nada que dependa de ella se pierde.
        cambios = ", ".join([*(f"{c} = :{c}" for c in [*campos, *siempre]),
                             "content_hash = :content_hash", "last_seen = :momento"])
        estado = "actualizada"
    conn.execute(f"UPDATE {tabla} SET {cambios} WHERE {donde}", params)
    return estado


_CONTADORES = {"nueva": "nuevas", "actualizada": "actualizadas", "sin_cambios": "sin_cambios",
               "huerfana": "huerfanas"}

Validar = Callable[[dict[str, str], int, Resultado], Fila]
Guardar = Callable[[sqlite3.Connection, Fila, str, int, str], str]


def importar_reporte(
    conn: sqlite3.Connection, *, nombre_archivo: str, raw: bytes, csv_file: CsvFile, report: str,
    entidad: str, origen: str, raw_dir: Path, requeridas: Iterable[str], nombre_clave: str,
    validar: Validar, guardar: Guardar,
    periodo: Callable[[list[Fila]], tuple[str | None, str | None]] | None = None,
    source_run_id: int | None = None,
) -> Resultado:
    """Valida todas las filas y, si el archivo es nuevo, las guarda en una sola transacción.

    * validar(fila, línea, resultado) devuelve una Fila o lanza FilaRechazada.
    * guardar(conn, fila, content_hash, import_id, momento) devuelve 'nueva', 'actualizada',
      'sin_cambios' o 'huerfana'.
    * source_run_id: la ejecución de run-cycle a la que pertenece; sin él, la importación suelta crea la suya.
    """
    if origen not in ORIGENES:
        raise ImportacionError(f"Origen no válido: {origen!r} (usa {', '.join(ORIGENES)})")
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'view' AND name = 'v_tender_lines'").fetchone():
        raise ImportacionError("La base no está migrada: ejecuta python -m app.cli migrate")

    file_hash = hashlib.sha256(raw).hexdigest()
    resultado = Resultado(archivo=nombre_archivo, file_hash=file_hash, encoding=csv_file.encoding,
                          delimiter=csv_file.delimiter, leidas=len(csv_file.rows),
                          avisos_archivo=list(csv_file.warnings))

    faltan = [c for c in requeridas if c not in csv_file.header]
    if faltan:
        raise ImportacionError(
            f"Faltan encabezados del mapeo: {', '.join(faltan)}. Separador detectado: {csv_file.delimiter!r}. "
            "¿Es el reporte correcto? ¿Pasó por Excel? (docs/MAPEO_DATOS.md)"
        )

    anterior = conn.execute("SELECT id FROM imports WHERE file_hash = ?", (file_hash,)).fetchone()
    if anterior:
        resultado.ya_importado = anterior[0]
        return resultado

    filas: list[Fila] = []
    vistos: dict[str, int] = {}
    header = csv_file.header
    for linea, valores in csv_file.rows:
        try:
            if len(valores) != len(header):
                raise FilaRechazada(f"tiene {len(valores)} columnas; se esperaban {len(header)}")
            original = dict(zip(header, valores))
            for columna, valor in original.items():
                if _NOTACION_CIENTIFICA.match(valor):
                    raise FilaRechazada(f"«{columna}» en notación científica ({valor}): código dañado por Excel")
            fila = validar(original, linea, resultado)
            if fila.clave in vistos:
                raise FilaRechazada(f"{nombre_clave} {fila.clave} repetido (ya está en la línea {vistos[fila.clave]})")
        except FilaRechazada as exc:
            resultado.rechazos.append(Rechazo(linea, str(exc)))
            for lineas in resultado.advertencias.values():  # una fila rechazada no deja advertencias
                if linea in lineas:
                    lineas.remove(linea)
            continue
        vistos[fila.clave] = linea
        filas.append(fila)

    resultado.copia_original = _copiar_original(raw, nombre_archivo, file_hash, raw_dir)
    desde, hasta = resultado.periodo = periodo(filas) if periodo else (None, None)
    momento = ahora()
    conn.execute("BEGIN")
    try:
        run_id = source_run_id or conn.execute(
            "INSERT INTO source_runs (started_at, finished_at, mode, data_origin, period_from, period_to, status)"
            " VALUES (?, ?, 'manual', ?, ?, ?, 'ok')",
            (momento, momento, origen, desde, hasta),
        ).lastrowid
        import_id = conn.execute(
            "INSERT INTO imports (source_run_id, report, file_name, file_hash, data_origin,"
            " rows_accepted, rows_rejected, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, report, nombre_archivo, file_hash, origen, len(filas), len(resultado.rechazos), momento),
        ).lastrowid
        for fila in filas:
            payload = json.dumps(fila.original, ensure_ascii=False, sort_keys=True)
            content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            conn.execute(
                "INSERT OR IGNORE INTO raw_snapshots (import_id, entity, natural_key, content_hash, payload, captured_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (import_id, entidad, fila.clave, content_hash, payload, momento),
            )
            contador = _CONTADORES[guardar(conn, fila, content_hash, import_id, momento)]
            setattr(resultado, contador, getattr(resultado, contador) + 1)
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    resultado.import_id = import_id
    return resultado
