"""Migraciones: siempre sobre una base temporal, nunca sobre data/sicop.db. Datos sintéticos."""

import shutil
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app.cli import main
from app.config import load_settings
from app.database import MIGRATIONS_DIR, MigrationError, apply_migrations, check_database
from app.main import app

TABLAS_16_3 = {
    "source_runs", "imports", "raw_snapshots", "institutions", "catalog_items", "tenders",
    "tender_lines", "opportunity_assessments", "reviews", "notification_outbox", "users",
}
AHORA = "2026-10-07T10:00:00-06:00"


@pytest.fixture
def db(tmp_path):
    return tmp_path / "sicop.db"


def _conn(db):
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _esquema(db):
    with closing(sqlite3.connect(db)) as conn:
        objetos = conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
        registro = conn.execute("SELECT version, checksum, applied_at FROM schema_migrations").fetchall()
    return objetos, registro


def _cartel(conn, nro_sicop="20260700001"):
    conn.execute(
        "INSERT INTO tenders (nro_sicop, content_hash, first_seen, last_seen) VALUES (?, 'h', ?, ?)",
        (nro_sicop, AHORA, AHORA),
    )


def test_migrate_crea_las_tablas_de_16_3(db):
    assert apply_migrations(db) == ["0001_esquema_inicial.sql", "0002_lineas_catalogo_instituciones.sql",
                                   "0003_evaluacion.sql", "0004_panel_revisiones.sql",
                                   "0005_historial_admin.sql", "0006_avisos.sql", "0007_ciclo.sql",
                                   "0008_evaluaciones.sql", "0009_solicitudes_sicop.sql", "0010_solicitudes_estados.sql",
                                   "0011_alerta_obtencion.sql", "0012_adjudicaciones.sql", "0013_cierre_y_resumen.sql",
                                   "0014_calidad_reglas.sql", "0015_seguimiento.sql",
                                   "0016_baja_usuarios.sql", "0017_obtencion_dos_turnos.sql", "0018_fichas.sql", "0019_documentos.sql"]

    with closing(sqlite3.connect(db)) as conn:
        tablas = {fila[0] for fila in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert TABLAS_16_3 <= tablas


def test_migrate_dos_veces_no_cambia_nada(db):
    apply_migrations(db)
    antes = _esquema(db)

    assert apply_migrations(db) == []
    assert _esquema(db) == antes


def test_comando_migrate_repetible_y_health_ok(db, capsys, monkeypatch):
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})
    assert check_database(db)["status"] == "pendiente"

    assert main(["migrate"], settings=settings) == 0
    assert main(["migrate"], settings=settings) == 0

    salida = capsys.readouterr().out
    assert "0001_esquema_inicial.sql" in salida
    assert "ya está al día" in salida
    monkeypatch.setenv("DATABASE_PATH", str(db))
    assert TestClient(app).get("/health").json()["database"]["status"] == "ok"


def test_base_existente_sin_migrar_queda_pendiente(db):
    with closing(sqlite3.connect(db)) as conn:  # base con una tabla, pero sin migrar
        conn.execute("CREATE TABLE cualquiera (x)")

    assert check_database(db)["status"] == "pendiente"


def test_mismo_archivo_no_se_importa_dos_veces(db):
    apply_migrations(db)
    sql = ("INSERT INTO imports (report, file_name, file_hash, data_origin, imported_at)"
           " VALUES ('carteles', ?, 'abc123', 'sintetico', ?)")
    with closing(_conn(db)) as conn:
        conn.execute(sql, ("a.csv", AHORA))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, ("otro_nombre.csv", AHORA))


def test_linea_de_cartel_duplicada_se_rechaza(db):
    apply_migrations(db)
    sql = ("INSERT INTO tender_lines (nro_sicop, numero_linea, content_hash, first_seen, last_seen)"
           " VALUES ('20260700001', '1', 'h', ?, ?)")
    with closing(_conn(db)) as conn:
        _cartel(conn)
        conn.execute(sql, (AHORA, AHORA))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (AHORA, AHORA))


def test_identificadores_y_dinero_se_conservan_exactos(db):
    apply_migrations(db)
    with closing(_conn(db)) as conn:
        _cartel(conn, "00012345678")
        conn.execute(
            "INSERT INTO tender_lines (nro_sicop, numero_linea, codigo_identificacion,"
            " precio_unitario_estimado, moneda, content_hash, first_seen, last_seen)"
            " VALUES ('00012345678', '1', '0000000100000001', '1234.50', 'CRC', 'h', ?, ?)",
            (AHORA, AHORA),
        )
        fila = conn.execute(
            "SELECT nro_sicop, codigo_identificacion, precio_unitario_estimado FROM tender_lines"
        ).fetchone()

    assert fila == ("00012345678", "0000000100000001", "1234.50")


def test_precio_sin_moneda_se_rechaza(db):
    apply_migrations(db)
    with closing(_conn(db)) as conn:
        _cartel(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO tender_lines (nro_sicop, numero_linea, precio_unitario_estimado,"
                " content_hash, first_seen, last_seen) VALUES ('20260700001', '1', '10.00', 'h', ?, ?)",
                (AHORA, AHORA),
            )


def test_origen_de_datos_debe_ser_real_sintetico_o_simulado(db):
    apply_migrations(db)
    with closing(_conn(db)) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO imports (report, file_name, file_hash, data_origin, imported_at)"
                " VALUES ('carteles', 'a.csv', 'x', 'inventado', ?)",
                (AHORA,),
            )


def test_revision_humana_no_se_borra_ni_se_modifica(db):
    apply_migrations(db)
    with closing(_conn(db)) as conn:
        _cartel(conn)
        conn.execute(
            "INSERT INTO reviews (nro_sicop, responsable, decision, created_at) VALUES ('20260700001', 'Ivania', 'interesa', ?)",
            (AHORA,),
        )
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM reviews")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE reviews SET decision = 'no_interesa', motivo = 'plazo'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM tenders WHERE nro_sicop = '20260700001'")
        assert conn.execute("SELECT count(*) FROM reviews").fetchone()[0] == 1


@pytest.mark.parametrize("decision, motivo", [
    ("no_interesa", None),         # «no interesa» exige motivo
    ("interesa", "plazo"),         # el motivo solo va con «no interesa»
    ("Interesa", None),            # fuera de la lista
])
def test_revision_valida_decision_y_motivo(db, decision, motivo):
    apply_migrations(db)
    with closing(_conn(db)) as conn:
        _cartel(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO reviews (nro_sicop, responsable, decision, motivo, created_at)"
                         " VALUES ('20260700001', 'Ivania', ?, ?, ?)", (decision, motivo, AHORA))


def test_0004_conserva_revisiones_y_rellena_tipo_de_procedimiento(tmp_path, db):
    hasta_0003 = tmp_path / "hasta_0003"
    hasta_0003.mkdir()
    for archivo in sorted(MIGRATIONS_DIR.glob("000[123]_*.sql")):
        shutil.copy(archivo, hasta_0003)
    apply_migrations(db, hasta_0003)
    with closing(_conn(db)) as conn:
        _cartel(conn)
        conn.execute("INSERT INTO imports (report, file_name, file_hash, data_origin, imported_at)"
                     " VALUES ('carteles', 'a.csv', 'h', 'sintetico', ?)", (AHORA,))
        conn.execute("INSERT INTO raw_snapshots (import_id, entity, natural_key, content_hash, payload, captured_at)"
                     " VALUES (1, 'cartel', '20260700001', 'c', ?, ?)",
                     ('{"Tipo de procedimiento": "Licitación Reducida"}', AHORA))
        conn.execute("INSERT INTO users (email, nombre, role, password_hash, created_at)"
                     " VALUES ('a@ejemplo.test', 'Ivania', 'encargado', 'x', ?)", (AHORA,))
        conn.execute("INSERT INTO reviews (nro_sicop, user_id, decision, created_at)"
                     " VALUES ('20260700001', 1, 'interesa', ?)", (AHORA,))
        conn.commit()

    assert apply_migrations(db) == ["0004_panel_revisiones.sql", "0005_historial_admin.sql", "0006_avisos.sql",
                                    "0007_ciclo.sql", "0008_evaluaciones.sql", "0009_solicitudes_sicop.sql", "0010_solicitudes_estados.sql",
                                    "0011_alerta_obtencion.sql", "0012_adjudicaciones.sql", "0013_cierre_y_resumen.sql",
                                    "0014_calidad_reglas.sql", "0015_seguimiento.sql",
                                   "0016_baja_usuarios.sql", "0017_obtencion_dos_turnos.sql", "0018_fichas.sql", "0019_documentos.sql"]

    with closing(_conn(db)) as conn:
        assert conn.execute("SELECT tipo_procedimiento FROM tenders").fetchone()[0] == "Licitación Reducida"
        assert conn.execute("SELECT nro_sicop, user_id, responsable, decision FROM reviews").fetchall() == [
            ("20260700001", 1, "Ivania", "interesa")]


def test_base_con_migraciones_pendientes_no_queda_ok(tmp_path, db):
    hasta_0004 = tmp_path / "hasta_0004"
    hasta_0004.mkdir()
    for archivo in sorted(MIGRATIONS_DIR.glob("000[1234]_*.sql")):
        shutil.copy(archivo, hasta_0004)
    apply_migrations(db, hasta_0004)

    estado = check_database(db)  # el código ya trae la 0005 y siguientes

    assert estado["status"] == "pendiente"
    assert "Faltan migraciones (base en 0004, código en " in estado["detail"]
    apply_migrations(db)
    assert check_database(db)["status"] == "ok"


def test_migracion_editada_despues_de_aplicarse_se_detecta(tmp_path, db):
    carpeta = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, carpeta)
    apply_migrations(db, carpeta)

    archivo = carpeta / "0001_esquema_inicial.sql"
    archivo.write_text(archivo.read_text(encoding="utf-8") + "\n-- editado\n", encoding="utf-8")

    with pytest.raises(MigrationError, match="cambió después de aplicarse"):
        apply_migrations(db, carpeta)


def test_migracion_con_error_no_deja_nada_a_medias(tmp_path, db):
    carpeta = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, carpeta)
    (carpeta / "9999_rota.sql").write_text(
        "CREATE TABLE tabla_nueva (a TEXT);\nESTO NO ES SQL;\n", encoding="utf-8"
    )

    with pytest.raises(MigrationError, match="9999_rota.sql"):
        apply_migrations(db, carpeta)

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name = 'tabla_nueva'").fetchone() is None
        assert [v for (v,) in conn.execute("SELECT version FROM schema_migrations")] == ["0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009", "0010", "0011", "0012", "0013", "0014", "0015", "0016", "0017", "0018", "0019"]
