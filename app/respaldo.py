"""Respaldo consistente de la base (lección 8, encargo B): backup --output CARPETA.

Por qué no basta con copiar el archivo .db: si el panel o el ciclo están escribiendo justo en ese momento, la
copia puede quedar a medias (una transacción escrita solo en parte) y no abrir, o abrir con datos rotos. La
API de backup de SQLite copia una foto coherente de la base aunque esté en uso.

Cada respaldo son dos archivos en la carpeta indicada, que nunca se sobrescriben:
* sicop_AAAAMMDD-HHMMSS.db: la copia.
* sicop_AAAAMMDD-HHMMSS.json: el manifiesto (fecha, commit del código, versión del esquema, SHA-256 de la copia,
  revisión de integridad y cuántas filas tienen las tablas principales), para comprobar después que la copia es
  la misma y saber con qué versión del código se puede abrir.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app import __version__
from app.config import PROJECT_ROOT

# En el paquete del servidor (git archive) este archivo trae el commit; en desarrollo dice $Format y se pregunta a git.
ARCHIVO_COMMIT = PROJECT_ROOT / "app" / "COMMIT"
# Tablas que se cuentan en el manifiesto: lo que más importa no perder.
TABLAS = ("tenders", "tender_lines", "reviews", "notification_outbox", "users", "source_runs")


class RespaldoError(Exception):
    """El respaldo no se pudo hacer; el mensaje es el que verá la usuaria."""


@dataclass
class Respaldo:
    base: Path
    manifiesto: Path
    datos: dict


def commit_del_codigo() -> str:
    """Commit con el que corre la app. «+cambios» si en desarrollo hay archivos sin guardar en git."""
    try:
        texto = ARCHIVO_COMMIT.read_text(encoding="utf-8").strip()
    except OSError:
        texto = ""
    if texto and "$Format" not in texto:
        return texto
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True,
                                timeout=10, check=True).stdout.strip()
        cambios = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=PROJECT_ROOT,
                                 capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "desconocido"
    return commit + ("+cambios" if cambios else "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while bloque := f.read(1024 * 1024):
            h.update(bloque)
    return h.hexdigest()


def respaldar(origen: Path, carpeta: Path, ahora: datetime) -> Respaldo:
    """Copia consistente de `origen` en `carpeta`, con su manifiesto. No sobrescribe nada."""
    if not origen.is_file():
        raise RespaldoError(f"no existe la base {origen}")
    carpeta.mkdir(parents=True, exist_ok=True)
    if carpeta.resolve() == origen.resolve().parent:
        raise RespaldoError("la carpeta del respaldo no puede ser la misma de la base: usa otra (idealmente otro disco)")
    nombre = f"sicop_{ahora:%Y%m%d-%H%M%S}"
    destino, manifiesto = carpeta / f"{nombre}.db", carpeta / f"{nombre}.json"
    if destino.exists() or manifiesto.exists():
        raise RespaldoError(f"ya existe un respaldo llamado {nombre}: espera un segundo y repite")
    temporal = carpeta / f".{nombre}.db.parcial"  # si algo falla, nunca queda un .db a medias con el nombre final
    try:
        # Solo lectura: el respaldo nunca cambia la base original.
        with closing(sqlite3.connect(f"{origen.resolve().as_uri()}?mode=ro", uri=True)) as fuente, \
                closing(sqlite3.connect(temporal)) as copia:
            fuente.backup(copia)
        with closing(sqlite3.connect(f"{temporal.resolve().as_uri()}?mode=ro", uri=True)) as copia:
            integridad = copia.execute("PRAGMA integrity_check").fetchone()[0]
            esquema = copia.execute("SELECT max(version) FROM schema_migrations").fetchone()[0]
            existentes = {n for (n,) in copia.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            filas = {t: copia.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLAS if t in existentes}
        if integridad != "ok":
            raise RespaldoError(f"la copia no pasó la revisión de integridad ({integridad})")
        os.replace(temporal, destino)
    except sqlite3.Error as exc:
        raise RespaldoError(f"SQLite: {exc}") from exc
    finally:
        temporal.unlink(missing_ok=True)
    datos = {
        "archivo": destino.name,
        "fecha": ahora.isoformat(timespec="seconds"),
        "commit": commit_del_codigo(),
        "version_app": __version__,
        "version_esquema": esquema,
        "sha256": sha256(destino),
        "bytes": destino.stat().st_size,
        "integridad": integridad,
        "filas": filas,
        "base_original": str(origen),
    }
    with open(manifiesto, "x", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return Respaldo(destino, manifiesto, datos)
