"""Líneas, catálogo e instituciones y sus relaciones: base temporal migrada; nunca toca data/."""

import sqlite3
import zipfile
from contextlib import closing
from decimal import Decimal
from pathlib import Path

import pytest

from app.cli import main
from app.compras import detalle_compra
from app.config import load_settings
from app.database import apply_migrations, connect
from app.dinero import Monto, MonedasDistintasError, totales_por_moneda
from app.importers.carteles import import_carteles
from app.importers.catalogo import ARCHIVO_EN_ZIP, import_catalogo
from app.importers.comun import ImportacionError
from app.importers.instituciones import import_instituciones
from app.importers.lineas import (ADV_EN_CERO, ADV_HUERFANA, ADV_NO_EN_CATALOGO, ADV_SIN_CATALOGO,
                                  import_lineas)

FIXTURES = Path(__file__).parent / "fixtures"
CARTELES_REAL = FIXTURES / "carteles_muestra.csv"
LINEAS_REAL = FIXTURES / "lineas_muestra.csv"
CARTELES = FIXTURES / "carteles_sintetico.csv"
LINEAS = FIXTURES / "lineas_sintetico.csv"
CATALOGO = FIXTURES / "catalogo_identificacion_sintetico.csv"
INSTITUCIONES = FIXTURES / "instituciones_sintetico.csv"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    return path


@pytest.fixture
def raw_dir(tmp_path):
    return tmp_path / "raw"


@pytest.fixture
def catalogo_zip(tmp_path):
    """ZIP con la misma forma que entrega el portal (tres CSV; solo uno se usa)."""
    path = tmp_path / "Reporte de catálogo de bienes y servicios.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Codigos Clasificacion.csv", "Codigo Clasificación;Nombre Clasificacion;En Uso\r\n")
        zf.writestr(ARCHIVO_EN_ZIP, CATALOGO.read_bytes())
        zf.writestr("Codigos Productos.csv", "Codigo Clasificación;Código identificación;Código Producto\r\n")
    return path


def _importar(db, funcion, path, raw_dir, origen="sintetico"):
    with closing(connect(db)) as conn:
        return funcion(conn, path, origen, raw_dir)


def _todo_sintetico(db, raw_dir, catalogo):
    _importar(db, import_instituciones, INSTITUCIONES, raw_dir)
    _importar(db, import_catalogo, catalogo, raw_dir)
    _importar(db, import_carteles, CARTELES, raw_dir)
    return _importar(db, import_lineas, LINEAS, raw_dir)


def _compra(db, nro):
    with closing(connect(db)) as conn:
        return detalle_compra(conn, nro)


def _uno(db, sql, params=()):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(sql, params).fetchone()


# --- Criterios de aceptación de la guía ---------------------------------------------------

def test_cartel_con_3_lineas_recupera_las_3(db, raw_dir, catalogo_zip):
    _todo_sintetico(db, raw_dir, catalogo_zip)

    compra = _compra(db, "20269900001")

    assert [l.numero_linea for l in compra.lineas] == ["1", "2", "3"]
    assert compra.institucion == "INSTITUCION SINTETICA DE PRUEBA"


def test_codigo_sin_catalogo_queda_marcado_sin_inventar_nombre(db, raw_dir, catalogo_zip):
    r = _todo_sintetico(db, raw_dir, catalogo_zip)

    estados = {l.numero_linea: (l.estado_catalogo, l.nombre_catalogo) for l in _compra(db, "20269900001").lineas}
    assert estados == {
        "1": ("en_catalogo", "SINTETICO SERVICIO DE MONITOREO GPS"),
        "2": ("codigo_no_esta_en_catalogo", None),
        "3": ("clasificacion_no_descargada", None),
    }
    assert r.advertencias[ADV_NO_EN_CATALOGO] == [3]
    assert r.advertencias[ADV_SIN_CATALOGO] == [4, 5]


def test_montos_en_monedas_distintas_nunca_se_suman(db, raw_dir, catalogo_zip):
    _todo_sintetico(db, raw_dir, catalogo_zip)

    totales = _compra(db, "20269900001").estimado_por_moneda

    assert totales == {"CRC": Monto(Decimal("4001.00"), "CRC"), "USD": Monto(Decimal("30.75"), "USD")}
    with pytest.raises(MonedasDistintasError):
        Monto(Decimal("1"), "CRC") + Monto(Decimal("1"), "USD")


# --- Líneas -------------------------------------------------------------------------------

def test_estimacion_por_linea_exacta_en_decimal(db, raw_dir, catalogo_zip):
    _todo_sintetico(db, raw_dir, catalogo_zip)

    assert _uno(db, "SELECT cantidad_solicitada, precio_unitario_estimado, estimado_linea, moneda"
                    " FROM tender_lines WHERE nro_sicop = '20269900001' AND numero_linea = '1'") == (
        "2", "1500.50", "3001.00", "CRC")


def test_lineas_invalidas_se_rechazan_con_linea_y_motivo(db, raw_dir, catalogo_zip):
    r = _todo_sintetico(db, raw_dir, catalogo_zip)

    motivos = {rechazo.linea: rechazo.motivo for rechazo in r.rechazos}
    assert set(motivos) == {7, 8, 9, 10, 11}
    assert "notación científica" in motivos[7]
    assert "15 dígitos" in motivos[8] and "16" in motivos[8]
    assert "repetido" in motivos[9] and "línea 2" in motivos[9]
    assert "Moneda" in motivos[10]
    assert "monto inválido" in motivos[11]
    assert r.advertencias[ADV_EN_CERO] == [5]


def test_linea_huerfana_se_advierte_y_no_se_inventa_el_cartel(db, raw_dir, catalogo_zip):
    r = _todo_sintetico(db, raw_dir, catalogo_zip)

    assert r.advertencias[ADV_HUERFANA] == [6]
    assert (r.nuevas, r.huerfanas) == (4, 1)
    assert _uno(db, "SELECT count(*) FROM tender_lines WHERE nro_sicop = '20269900077'") == (0,)
    assert _uno(db, "SELECT count(*) FROM tenders WHERE nro_sicop = '20269900077'") == (0,)
    assert _uno(db, "SELECT count(*) FROM raw_snapshots WHERE natural_key = '20269900077|1'") == (1,)


def test_ceros_iniciales_del_codigo_se_conservan(db, raw_dir, catalogo_zip):
    _todo_sintetico(db, raw_dir, catalogo_zip)

    assert _uno(db, "SELECT nro_sicop, codigo_identificacion FROM tender_lines WHERE nro_sicop = '00099900002'") == (
        "00099900002", "0000000100000001")


def test_mismo_archivo_de_lineas_dos_veces_no_agrega_nada(db, raw_dir, catalogo_zip):
    _todo_sintetico(db, raw_dir, catalogo_zip)
    antes = _uno(db, "SELECT (SELECT count(*) FROM tender_lines), (SELECT count(*) FROM raw_snapshots)")

    r = _importar(db, import_lineas, LINEAS, raw_dir)

    assert r.ya_importado is not None
    assert _uno(db, "SELECT (SELECT count(*) FROM tender_lines), (SELECT count(*) FROM raw_snapshots)") == antes


def test_linea_modificada_se_actualiza_y_conserva_la_version_anterior(db, raw_dir, catalogo_zip, tmp_path):
    _todo_sintetico(db, raw_dir, catalogo_zip)
    v2 = tmp_path / "lineas_v2.csv"
    v2.write_bytes(LINEAS.read_bytes().replace(b"20269900001;3;2;1;1000;CRC", b"20269900001;3;2;4;1000;CRC"))

    r = _importar(db, import_lineas, v2, raw_dir)

    assert (r.nuevas, r.actualizadas, r.sin_cambios) == (0, 1, 3)
    assert _uno(db, "SELECT estimado_linea FROM tender_lines WHERE nro_sicop = '20269900001'"
                    " AND numero_linea = '3'") == ("4000",)
    assert _uno(db, "SELECT count(*) FROM raw_snapshots WHERE natural_key = '20269900001|3'") == (2,)


def test_muestra_real_cada_cartel_recupera_su_linea(db, raw_dir):
    _importar(db, import_carteles, CARTELES_REAL, raw_dir, origen="real")
    r = _importar(db, import_lineas, LINEAS_REAL, raw_dir, origen="real")

    assert (r.leidas, r.nuevas, r.huerfanas, len(r.rechazos)) == (5, 5, 0, 0)
    compra = _compra(db, "20260700384")
    assert [(l.codigo_identificacion, l.estimado) for l in compra.lineas] == [
        ("4222151292227442", Monto(Decimal("17100"), "USD"))]
    assert compra.institucion is None  # el reporte 11 no se importó: se muestra como faltante


# --- Catálogo -----------------------------------------------------------------------------

def test_catalogo_desde_zip_une_clasificacion_e_identificacion(db, raw_dir, catalogo_zip):
    r = _importar(db, import_catalogo, catalogo_zip, raw_dir)

    assert (r.nuevas, len(r.rechazos)) == (2, 1)
    assert "8" in r.rechazos[0].motivo  # clasificación de 7 dígitos
    assert _uno(db, "SELECT codigo_identificacion, codigo_clasificacion, nombre FROM catalog_items"
                    " WHERE nombre LIKE '%RASTREO%'") == ("9999990100000002", "99999901", "SINTETICO DISPOSITIVO DE RASTREO")
    assert r.copia_original.read_bytes() == catalogo_zip.read_bytes()


def test_zip_sin_el_csv_de_identificacion_no_escribe_nada(db, raw_dir, tmp_path):
    malo = tmp_path / "otro.zip"
    with zipfile.ZipFile(malo, "w") as zf:
        zf.writestr("Codigos Productos.csv", "x\r\n")

    with pytest.raises(ImportacionError, match=ARCHIVO_EN_ZIP):
        _importar(db, import_catalogo, malo, raw_dir)
    assert _uno(db, "SELECT count(*) FROM imports") == (0,)


def test_catalogo_importado_despues_actualiza_la_marca(db, raw_dir, catalogo_zip):
    _importar(db, import_carteles, CARTELES, raw_dir)
    _importar(db, import_lineas, LINEAS, raw_dir)
    assert _compra(db, "20269900001").lineas[0].estado_catalogo == "clasificacion_no_descargada"

    _importar(db, import_catalogo, catalogo_zip, raw_dir)

    assert _compra(db, "20269900001").lineas[0].estado_catalogo == "en_catalogo"


# --- Instituciones ------------------------------------------------------------------------

def test_instituciones_cedula_como_texto_y_sin_representante(db, raw_dir):
    r = _importar(db, import_instituciones, INSTITUCIONES, raw_dir)

    assert (r.nuevas, [x.linea for x in r.rechazos]) == (2, [4])
    assert _uno(db, "SELECT cedula FROM institutions WHERE nombre LIKE '%CEROS'") == ("0009999999",)
    assert _uno(db, "SELECT count(*) FROM raw_snapshots WHERE payload LIKE '%PERSONA SINTETICA%'") == (0,)


# --- Dinero -------------------------------------------------------------------------------

def test_totales_por_moneda_y_monto_exige_decimal():
    montos = [Monto(Decimal("0.10"), "CRC"), Monto(Decimal("0.20"), "CRC"), Monto(Decimal("5"), "USD")]

    assert totales_por_moneda(montos)["CRC"].valor == Decimal("0.30")  # con float sería 0.30000000000000004
    with pytest.raises(TypeError):
        Monto(0.1, "CRC")


# --- Línea de comandos --------------------------------------------------------------------

def test_cli_importa_los_cuatro_reportes_y_muestra_la_compra(tmp_path, capsys, catalogo_zip):
    db = tmp_path / "cli.db"
    apply_migrations(db)
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "RAW_DATA_DIR": str(tmp_path / "raw")})
    for report, path in [("instituciones", INSTITUCIONES), ("catalogo", catalogo_zip),
                         ("carteles", CARTELES), ("lineas", LINEAS)]:
        assert main(["import", "--path", str(path), "--report", report, "--origen", "sintetico"],
                    settings=settings) == 0
    assert "huérfanas 1" in capsys.readouterr().out

    assert main(["compra", "20269900001"], settings=settings) == 0
    salida = capsys.readouterr().out
    assert "Comprador: INSTITUCION SINTETICA DE PRUEBA" in salida and "Líneas: 3" in salida
    assert "SIN CATÁLOGO" in salida and "4001.00 CRC · 30.75 USD" in salida

    assert main(["compra", "20269999999"], settings=settings) == 1
