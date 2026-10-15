"""Respaldo consistente (lección 8, encargo B): backup --output CARPETA. Base temporal con datos SINTÉTICOS."""

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest

from app import destinatarios, respaldo
from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect
from app.importers.comun import HORA_CR

AHORA = datetime(2026, 10, 14, 8, 0, 0, tzinfo=HORA_CR)


@pytest.fixture
def base(tmp_path):
    db = tmp_path / "data" / "sicop.db"
    apply_migrations(db)
    with closing(connect(db)) as conn:
        destinatarios.agregar(conn, "oscar@ejemplo.test", "Oscar")
    return db


def test_respaldo_con_manifiesto_que_se_puede_restaurar(base, tmp_path):
    r = respaldo.respaldar(base, tmp_path / "respaldos", AHORA)

    assert (r.base.name, r.manifiesto.name) == ("sicop_20261014-080000.db", "sicop_20261014-080000.json")
    manifiesto = json.loads(r.manifiesto.read_text(encoding="utf-8"))
    assert manifiesto["fecha"] == "2026-10-14T08:00:00-06:00"
    assert manifiesto["version_esquema"] == "0007"
    assert manifiesto["integridad"] == "ok"
    assert manifiesto["sha256"] == respaldo.sha256(r.base)
    assert re.fullmatch(r"[0-9a-f]{40}(\+cambios)?|desconocido", manifiesto["commit"])
    # «Restaurar»: copiar el .db a otra carpeta y abrirlo; el dato conocido está ahí.
    restaurada = tmp_path / "restaurada" / "sicop.db"
    restaurada.parent.mkdir()
    restaurada.write_bytes(r.base.read_bytes())
    with closing(sqlite3.connect(restaurada)) as conn:
        assert conn.execute("SELECT email FROM notification_recipients").fetchall() == [("oscar@ejemplo.test",)]


def test_el_respaldo_es_consistente_aunque_alguien_este_escribiendo(base, tmp_path):
    """Una transacción a medio escribir no entra en la copia: la copia es una foto coherente."""
    with closing(sqlite3.connect(base, isolation_level=None)) as otro:
        otro.execute("BEGIN IMMEDIATE")
        otro.execute("INSERT INTO notification_recipients (email, nombre, created_at)"
                     " VALUES ('a_medias@ejemplo.test', 'A medias', '2026-10-14')")
        r = respaldo.respaldar(base, tmp_path / "respaldos", AHORA)
        otro.execute("ROLLBACK")

    with closing(sqlite3.connect(r.base)) as conn:
        assert [e for (e,) in conn.execute("SELECT email FROM notification_recipients")] == ["oscar@ejemplo.test"]


def test_nunca_sobrescribe_un_respaldo(base, tmp_path):
    respaldo.respaldar(base, tmp_path / "respaldos", AHORA)
    antes = (tmp_path / "respaldos" / "sicop_20261014-080000.db").read_bytes()

    with pytest.raises(respaldo.RespaldoError, match="ya existe"):
        respaldo.respaldar(base, tmp_path / "respaldos", AHORA)
    assert (tmp_path / "respaldos" / "sicop_20261014-080000.db").read_bytes() == antes
    assert sorted(p.name for p in (tmp_path / "respaldos").iterdir()) == [
        "sicop_20261014-080000.db", "sicop_20261014-080000.json"]   # tampoco quedó un temporal


def test_no_respalda_en_la_misma_carpeta_ni_sin_base(base, tmp_path):
    with pytest.raises(respaldo.RespaldoError, match="no puede ser la misma"):
        respaldo.respaldar(base, base.parent, AHORA)
    with pytest.raises(respaldo.RespaldoError, match="no existe la base"):
        respaldo.respaldar(tmp_path / "no_hay.db", tmp_path / "respaldos", AHORA)


def test_el_commit_del_paquete_viene_de_app_commit(tmp_path, monkeypatch):
    archivo = tmp_path / "COMMIT"
    archivo.write_text("8b1a8ae" + "0" * 33 + "\n", encoding="utf-8")   # como lo deja git archive
    monkeypatch.setattr(respaldo, "ARCHIVO_COMMIT", archivo)
    assert respaldo.commit_del_codigo() == "8b1a8ae" + "0" * 33


def test_comando_backup(base, tmp_path, capsys):
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(base)})

    assert main(["backup", "--output", str(tmp_path / "respaldos")], settings) == 0

    salida = capsys.readouterr().out
    assert "Respaldo:" in salida and "esquema 0007 · integridad ok" in salida
    assert "notification_outbox 0" in salida
    assert main(["backup", "--output", str(base.parent)], settings) == 1
    assert "No se hizo el respaldo" in capsys.readouterr().err
