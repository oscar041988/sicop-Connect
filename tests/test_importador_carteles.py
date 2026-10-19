"""Importador de carteles: base temporal migrada; nunca toca data/."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect
from app.importers.carteles import ADV_INICIO_ANTES, ADV_SIN_RECEPCION, ImportacionError, import_carteles

FIXTURES = Path(__file__).parent / "fixtures"
MUESTRA_REAL = FIXTURES / "carteles_muestra.csv"
SINTETICO = FIXTURES / "carteles_sintetico.csv"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    return path


@pytest.fixture
def raw_dir(tmp_path):
    return tmp_path / "raw"


def _importar(db, path, raw_dir, origen="sintetico"):
    with closing(connect(db)) as conn:
        return import_carteles(conn, path, origen, raw_dir)


def _contar(db, tabla):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]


def _uno(db, sql, params=()):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(sql, params).fetchone()


def test_muestra_real_se_importa_completa_y_exacta(db, raw_dir):
    r = _importar(db, MUESTRA_REAL, raw_dir, origen="real")

    assert (r.leidas, r.nuevas, len(r.rechazos)) == (5, 5, 0)
    nro, desc, fecha = _uno(db, "SELECT nro_sicop, descripcion, fecha_publicacion FROM tenders"
                                " WHERE nro_sicop = '20260700179'")
    assert nro == "20260700179"
    assert "\xa0" in desc  # el espacio duro original se conserva
    assert fecha.endswith("-06:00")
    assert _uno(db, "SELECT data_origin FROM imports")[0] == "real"


def test_ceros_iniciales_y_codigo_de_24_digitos_se_conservan(db, raw_dir):
    _importar(db, SINTETICO, raw_dir)

    assert _uno(db, "SELECT nro_sicop FROM tenders WHERE nro_sicop = '00099900002'") == ("00099900002",)
    payload = json.loads(_uno(db, "SELECT payload FROM raw_snapshots WHERE natural_key = '00099900002'")[0])
    assert payload["Cod Unidad Compra"] == "000000000000000000012345"


def test_filas_invalidas_se_rechazan_con_linea_y_motivo(db, raw_dir):
    r = _importar(db, SINTETICO, raw_dir)

    motivos = {rechazo.linea: rechazo.motivo for rechazo in r.rechazos}
    assert set(motivos) == {4, 5, 6, 7, 8}
    assert "notación científica" in motivos[4]
    assert "formato inválido" in motivos[5]
    assert "vacío" in motivos[6]
    assert "columnas" in motivos[7]
    assert "repetido" in motivos[8] and "línea 2" in motivos[8]
    assert r.nuevas == 3
    assert r.advertencias[ADV_SIN_RECEPCION] == [9]
    assert _uno(db, "SELECT rows_accepted, rows_rejected FROM imports") == (3, 5)


def test_inicio_antes_de_publicacion_solo_advierte_pasada_1_hora(db, raw_dir, tmp_path):
    original = SINTETICO.read_bytes()
    linea2 = next(l for l in original.split(b"\r\n") if l.startswith(b"20269900001;"))
    linea3 = next(l for l in original.split(b"\r\n") if l.startswith(b"00099900002;"))
    # Publicación 01/10/2026 09:00:00. Línea 2: inicio 14 min antes (normal). Línea 3: 1 h 1 min antes.
    casos = tmp_path / "inicio_antes.csv"
    casos.write_bytes(original
                      .replace(linea2, linea2.replace(b";01/10/2026 09:00:00;15/10", b";01/10/2026 08:46:00;15/10"))
                      .replace(linea3, linea3.replace(b";01/10/2026 09:00:00;15/10", b";01/10/2026 07:59:00;15/10")))

    r = _importar(db, casos, raw_dir)

    assert r.advertencias[ADV_INICIO_ANTES] == [3]


def test_mismo_archivo_dos_veces_no_agrega_nada(db, raw_dir):
    _importar(db, MUESTRA_REAL, raw_dir)
    antes = [_contar(db, t) for t in ("imports", "tenders", "raw_snapshots", "source_runs")]

    r = _importar(db, MUESTRA_REAL, raw_dir)

    assert r.ya_importado is not None and r.nuevas == 0
    assert [_contar(db, t) for t in ("imports", "tenders", "raw_snapshots", "source_runs")] == antes


def test_cartel_modificado_crea_nueva_version_sin_perder_la_anterior(db, raw_dir, tmp_path):
    _importar(db, MUESTRA_REAL, raw_dir)
    original = MUESTRA_REAL.read_bytes()
    linea = next(l for l in original.split(b"\r\n") if l.startswith(b"20260700384;"))
    campos = linea.split(b";")
    campos[13] = b"30/12/2026 10:00:00"  # Fecha Cierre Recepción cambia
    modificado = tmp_path / "carteles_v2.csv"
    modificado.write_bytes(original.replace(linea, b";".join(campos)))

    r = _importar(db, modificado, raw_dir)

    assert (r.nuevas, r.actualizadas, r.sin_cambios) == (0, 1, 4)
    assert _uno(db, "SELECT fecha_cierre_recepcion FROM tenders WHERE nro_sicop = '20260700384'") == (
        "2026-12-30T10:00:00-06:00",)
    assert _uno(db, "SELECT count(*) FROM raw_snapshots WHERE natural_key = '20260700384'") == (2,)


def test_original_se_copia_identico_a_raw(db, raw_dir):
    r = _importar(db, MUESTRA_REAL, raw_dir)

    assert r.copia_original.parent == raw_dir / "importados"
    assert r.copia_original.read_bytes() == MUESTRA_REAL.read_bytes()


def test_falta_encabezado_requerido_no_escribe_nada(db, raw_dir, tmp_path):
    malo = tmp_path / "malo.csv"
    malo.write_bytes(MUESTRA_REAL.read_bytes().replace("Número SICOP".encode(), b"Numero SICOP", 1))

    with pytest.raises(ImportacionError, match="Faltan encabezados"):
        _importar(db, malo, raw_dir)
    assert _contar(db, "imports") == 0 and _contar(db, "tenders") == 0


def test_archivo_cp1252_se_lee_con_advertencia(db, raw_dir, tmp_path):
    texto = SINTETICO.read_bytes().decode("utf-8-sig").replace("\xa0", " ")
    windows = tmp_path / "windows.csv"
    windows.write_bytes(texto.encode("cp1252"))

    r = _importar(db, windows, raw_dir)

    assert r.encoding == "cp1252" and r.avisos_archivo
    assert r.nuevas == 3  # «Número SICOP» con tilde se reconoció bien


def test_revision_humana_sobrevive_a_la_reimportacion(db, raw_dir, tmp_path):
    _importar(db, MUESTRA_REAL, raw_dir)
    with closing(connect(db)) as conn:
        conn.execute("INSERT INTO reviews (nro_sicop, responsable, decision, created_at)"
                     " VALUES ('20260700384', 'Ivania', 'interesa', '2026-10-07T10:00:00-06:00')")
    modificado = tmp_path / "v2.csv"
    original = MUESTRA_REAL.read_bytes()
    linea = next(l for l in original.split(b"\r\n") if l.startswith(b"20260700384;"))
    modificado.write_bytes(original.replace(linea, linea.replace(b";N;", b";Y;", 1)))

    r = _importar(db, modificado, raw_dir)

    assert r.actualizadas == 1
    assert _uno(db, "SELECT decision FROM reviews WHERE nro_sicop = '20260700384'") == ("interesa",)


def test_cli_import_resumen_e_idempotencia(tmp_path, capsys):
    db = tmp_path / "sicop.db"
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "RAW_DATA_DIR": str(tmp_path / "raw")})
    args = ["import", "--path", str(SINTETICO), "--report", "carteles", "--origen", "sintetico"]

    assert main(args, settings=settings) == 1  # base sin migrar
    assert "migrate" in capsys.readouterr().err

    apply_migrations(db)
    assert main(args, settings=settings) == 0
    salida = capsys.readouterr().out
    assert "Aceptadas: 3" in salida and "Rechazadas: 5" in salida and "línea 4:" in salida

    assert main(args, settings=settings) == 0
    assert "0 filas nuevas" in capsys.readouterr().out


def test_cli_import_exige_origen(tmp_path):
    with pytest.raises(SystemExit):
        main(["import", "--path", str(SINTETICO), "--report", "carteles"],
             settings=load_settings(env_file=None, environ={"DATABASE_PATH": str(tmp_path / "x.db")}))
