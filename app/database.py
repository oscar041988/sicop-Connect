"""Acceso a SQLite: revisión de la base y migraciones versionadas."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# Nombre esperado: 0001_esquema_inicial.sql (4 dígitos, guion bajo, minúsculas).
_MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


class MigrationError(Exception):
    """Una migración no se puede aplicar o no coincide con lo ya aplicado."""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    sql: str
    checksum: str


def _checksum(sql: str) -> str:
    # Se normalizan los saltos de línea para que Windows (CRLF) y Linux (LF) den la misma huella.
    return hashlib.sha256(sql.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Lee los archivos .sql de la carpeta, en orden de versión."""
    migrations: list[Migration] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_NAME.match(path.name)
        if not match:
            raise MigrationError(f"Nombre de migración no válido: {path.name} (esperado 0001_nombre.sql)")
        version = match.group(1)
        if version in seen:
            raise MigrationError(f"Versión repetida: {version}")
        seen.add(version)
        sql = path.read_text(encoding="utf-8")
        migrations.append(Migration(version, path.name, sql, _checksum(sql)))
    return migrations


@contextmanager
def transaccion(conn: sqlite3.Connection):
    """Todo lo de adentro se guarda junto o no se guarda nada (para conexiones de connect())."""
    conn.execute("BEGIN")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def connect(path: Path) -> sqlite3.Connection:
    """Conexión con claves foráneas activas y transacciones explícitas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_migrations(path: Path, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Aplica las migraciones pendientes y devuelve sus nombres. Repetible: si no hay nada, devuelve []."""
    migrations = discover_migrations(directory)
    with closing(connect(path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version TEXT PRIMARY KEY, name TEXT NOT NULL,"
            " checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        applied = dict(conn.execute("SELECT version, checksum FROM schema_migrations"))

        # Antes de aplicar nada: lo ya aplicado debe coincidir con los archivos.
        known = {m.version: m for m in migrations}
        for version, checksum in applied.items():
            if version not in known:
                raise MigrationError(f"La base tiene la migración {version}, que no existe en {directory.name}/")
            if known[version].checksum != checksum:
                raise MigrationError(
                    f"{known[version].name} cambió después de aplicarse. No se edita una migración aplicada: "
                    "crea una nueva (0002_...)."
                )

        done: list[str] = []
        for migration in migrations:
            if migration.version in applied:
                continue
            try:
                # Todo el archivo y su registro van en una sola transacción: o se aplica completo o nada.
                conn.executescript("BEGIN;\n" + migration.sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
                    (migration.version, migration.name, migration.checksum,
                     datetime.now(timezone.utc).isoformat(timespec="seconds")),
                )
                conn.execute("COMMIT")
            except sqlite3.Error as exc:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise MigrationError(f"Falló {migration.name}: {exc}") from exc
            done.append(migration.name)
        return done


def _ultima_version(directory: Path) -> str | None:
    versiones = [m.group(1) for p in directory.glob("*.sql") if (m := _MIGRATION_NAME.match(p.name))]
    return max(versiones, default=None)


def check_database(path: Path, directory: Path = MIGRATIONS_DIR) -> dict[str, str]:
    """Verifica si la base existe y tiene todas las migraciones aplicadas, sin crearla ni modificarla."""
    if not path.is_file():
        return {"status": "pendiente", "detail": "La base aún no existe (se creará con migrate)."}
    try:
        # mode=ro: abre en solo lectura, así una revisión nunca crea ni altera la base.
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as conn:
            has_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
            ).fetchone()
            version = conn.execute("SELECT max(version) FROM schema_migrations").fetchone()[0] if has_table else None
    except sqlite3.Error as exc:
        return {"status": "error", "detail": f"No se pudo abrir la base: {exc.__class__.__name__}"}
    if version is None:
        return {"status": "pendiente", "detail": "La base existe pero no está migrada (ejecuta migrate)."}
    ultima = _ultima_version(directory)
    if ultima is not None and version < ultima:
        # Código nuevo con una base vieja: mejor un aviso claro que un error 500 al buscar una tabla que no existe.
        return {"status": "pendiente",
                "detail": f"Faltan migraciones (base en {version}, código en {ultima}): ejecuta python -m app.cli migrate"}
    return {"status": "ok", "detail": f"Esquema aplicado (versión {version})."}
