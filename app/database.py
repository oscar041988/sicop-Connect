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
# Una migración que reconstruye una tabla a la que otras apuntan lo pide con esta línea (procedimiento de 12 pasos de
# la documentación de SQLite, «ALTER TABLE»): corre con las llaves foráneas apagadas y, ANTES de confirmar, se
# revisan todas con PRAGMA foreign_key_check; si alguna quedó rota, no se aplica nada.
SIN_LLAVES_FORANEAS = "-- migracion: sin llaves foraneas"
# Segundos que una conexión espera si otro programa está escribiendo (el panel, el enriquecimiento) antes de fallar con
# «database is locked». Con los 5 s de Python, el ciclo del 2026-11-05 a las 8:00 se detuvo.
ESPERA_BASE_OCUPADA_S = 30
# Las tareas programadas (ciclo, enriquecimiento, cola de IA, obtención) esperan más: nadie las mira, y una carga
# grande en «Cargar archivo» ocupa la base unos minutos. El 2026-11-10 a las 10:00, una carga de 11 390 carteles
# tuvo la base ocupada más de 2 min y el enriquecimiento y la cola de IA se cayeron a los 30 s.
ESPERA_TAREAS_S = 600
_espera_s = ESPERA_BASE_OCUPADA_S


@contextmanager
def espera_de_tarea():
    """Dentro del bloque, las conexiones nuevas esperan ESPERA_TAREAS_S; al salir, vuelve la espera normal. Lo usan
    los comandos de las tareas programadas (app/cli.py); el panel no."""
    global _espera_s
    anterior, _espera_s = _espera_s, ESPERA_TAREAS_S
    try:
        yield
    finally:
        _espera_s = anterior


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
    """Todo lo de adentro se guarda junto o no se guarda nada (para conexiones de connect()).

    IMMEDIATE: reserva la escritura al empezar. Con un BEGIN normal, una transacción que lee y después escribe
    mientras otro programa escribe queda trabada con él: SQLite falla en los dos con «database is locked» sin
    esperar ESPERA_BASE_OCUPADA_S. Así, si la base está ocupada, espera en el BEGIN y sigue."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def connect(path: Path) -> sqlite3.Connection:
    """Conexión con claves foráneas activas, transacciones explícitas y espera ante la base ocupada."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, timeout=_espera_s)
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
            sin_llaves = SIN_LLAVES_FORANEAS in migration.sql
            if sin_llaves:
                conn.execute("PRAGMA foreign_keys = OFF")   # solo fuera de una transacción tiene efecto
            try:
                # Todo el archivo y su registro van en una sola transacción: o se aplica completo o nada.
                conn.executescript("BEGIN;\n" + migration.sql)
                if sin_llaves and (rotas := conn.execute("PRAGMA foreign_key_check").fetchall()):
                    raise sqlite3.IntegrityError(f"quedarían {len(rotas)} llaves foráneas rotas (p. ej. {rotas[0]})")
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
            finally:
                if sin_llaves:
                    conn.execute("PRAGMA foreign_keys = ON")
            done.append(migration.name)
        # Modo WAL (Ivania, 2026-11-13): el panel lee mientras una tarea escribe, sin esperar. Dos escrituras a la vez
        # siguen esperando su turno (ESPERA_BASE_OCUPADA_S, ESPERA_TAREAS_S). Queda guardado en el archivo de la
        # base, por eso basta con hacerlo aquí: migrate corre con el panel y las tareas cerrados. Junto a la base
        # aparecen sicop.db-wal y sicop.db-shm; al restaurar un respaldo se apartan con ella (OPERACION.md 6.2).
        conn.execute("PRAGMA journal_mode = WAL")
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
