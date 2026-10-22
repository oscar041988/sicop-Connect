"""Inteligencia competitiva: importar «Adjudicaciones en firme», aplicar las familias y la página «Competencia».

Datos SINTÉTICOS (ZIP armado aquí con los encabezados reales del 2026-10-22) en una base temporal; nunca toca data/.
"""

import sqlite3
import zipfile
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import competencia, usuarios
from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect
from app.importers import adjudicaciones, zip_pliegos
from app.main import app
from app.matching.evaluar import evaluar_base
from app.matching.reglas import cargar_reglas
from tests.test_panel import CONTRASENA, iniciar_sesion

ENC_ADJ = "Número SICOP;Numero de procedimiento;Fecha Comunicación;Fecha Adj Firme;Permite Recursos;Fecha Maxima Recursos;Desierto"
ENC_PROV = "Número SICOP;Numero de procedimiento;Cédula Empresa Proveedora"
ENC_LIN = ("Número SICOP;Numero de linea;Cédula Empresa Proveedora;Cantidad;Precio;Moneda;Descuento;IVA;"
           "Otros Impuestos;Acarreos;Tipo Cambio CRC")

ADJ = [
    "00000000101;2026LD-000001-0000000001;10/08/2026 09:00:00;18/08/2026 07:22:31;Si;17/08/2026 23:59:00;N",
    "00000000101;2026LD-000001-0000000001;10/08/2026 09:00:00;18/08/2026 07:23:07;Si;17/08/2026 23:59:00;N",
    "00000000101;2026LD-000001-0000000001;10/08/2026 09:00:00;18/08/2026 07:23:07;Si;17/08/2026 23:59:00;N",  # idéntica
    "00000000102;2026LE-000002-0000000002; ;15/09/2026 10:00:00; ; ;N",  # SICOP marca «sin valor» con un espacio
    "00000000103;2026LE-000003-0000000003;20/08/2026 09:00:00;01/09/2026 10:00:00;Si;31/08/2026 23:59:00;N",
    "00000000104;2026LE-000004-0000000004;20/08/2026 09:00:00;01/09/2026 10:00:00;Si;31/08/2026 23:59:00;N",  # sin cartel
]
PROV = [
    "00000000101;2026LD-000001-0000000001;0101000001",
    "00000000101;2026LD-000001-0000000001;3101000002",
    "00000000101;2026LD-000001-0000000001;0101000001",  # idéntica
    "00000000102;2026LE-000002-0000000002;3101000003",
    "00000000103;2026LE-000003-0000000003;3101000002",
    "00000000104;2026LE-000004-0000000004;3101000002",
]
LIN = [
    "00000000101;1;0101000001;2;1000.50;CRC;1.00;0;0;0;450.10",   # 2 × 1000.50 − 1 = 2000.00 CRC
    "00000000101;2;0101000001;1;300;USD;0;39;0;0;450.10",         # 300 USD (el IVA no se suma)
    "00000000101;3;3101000002;1;500;CRC;0;65;0;0;450.10",         # misma línea y cédula, dos registros
    "00000000101;3;3101000002;1;500;CRC;0;0;0;0;451.20",          # distintos: no se suman
    "00000000101;1;0101000001;2;1000.50;CRC;1.00;0;0;0;450.10",   # idéntica
    "00000000103;1;3101000002;1;999;CRC;0;0;0;0;450.10",          # cartel sin familia
]
COMPETIDORES = 'competidores:\n  "Competidor Uno":\n    cedulas: ["0101000001", "3101000003"]\n'
T = "2026-10-01T00:00:00+00:00"


def _csv(encabezado, filas):
    return ("\n".join([encabezado, *filas]) + "\n").encode("utf-8-sig")


def armar_zip(path, lin=LIN, sin=None):
    with zipfile.ZipFile(path, "w") as zf:
        for nombre, contenido in {"Detalle Adjudicaciones.csv": _csv(ENC_ADJ, ADJ),
                                  "Det Proveedores Adj.csv": _csv(ENC_PROV, PROV),
                                  "Det Lineas Adjudicadas.csv": _csv(ENC_LIN, lin)}.items():
            if nombre != sin:
                zf.writestr(nombre, contenido)
    return path


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    with closing(connect(path)) as conn:
        conn.executemany("INSERT INTO institutions (cedula, nombre, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                         [("3000000001", "Municipalidad Sintética A", T, T), ("3000000002", "Ministerio Sintético B", T, T)])
        conn.executemany(
            "INSERT INTO tenders (nro_sicop, descripcion, institution_cedula, content_hash, first_seen, last_seen)"
            " VALUES (?, ?, ?, 'h', ?, ?)",
            [("00000000101", "Servicio de monitoreo GPS de vehículos", "3000000001", T, T),   # gps_flotas Alta
             ("00000000102", "Alquiler de GPS para la flotilla", "3000000002", T, T),         # gps_flotas Media
             ("00000000103", "Compra de sillas", "3000000001", T, T)])                       # sin familia
        conn.commit()
        evaluar_base(conn, cargar_reglas(), datetime(2026, 10, 22, tzinfo=timezone.utc))
    return path


@pytest.fixture
def importada(db, tmp_path):
    with closing(connect(db)) as conn:
        partes = adjudicaciones.import_zip(conn, armar_zip(tmp_path / "adj.zip"), "sintetico", tmp_path / "raw")
    return db, dict(partes)


def _resumen(db, filtro=competencia.Filtro(), nombres=None):
    with closing(connect(db)) as conn:
        version = conn.execute("SELECT rules_version FROM opportunity_assessments LIMIT 1").fetchone()[0]
        r = competencia.resumen(conn, version, filtro, nombres if nombres is not None else
                                {"0101000001": "Competidor Uno", "3101000003": "Competidor Uno"})
    return r, {f.familia: f for f in r.familias}


# --- Importación ---------------------------------------------------------------------------------------------

def test_importa_los_tres_csv_y_guarda_las_repetidas_una_vez(importada):
    db, partes = importada
    adj, prov, lin = partes["adjudicaciones"], partes["adjudicacion_proveedores"], partes["adjudicacion_lineas"]
    assert (adj.nuevas, prov.nuevas, lin.nuevas) == (5, 5, 5)
    assert not adj.rechazos and not prov.rechazos and not lin.rechazos
    for r in (adj, prov, lin):
        assert len(r.advertencias[adjudicaciones.ADV_IDENTICA]) == 1
    assert len(lin.advertencias[adjudicaciones.ADV_VARIOS_REGISTROS]) == 1
    assert len(adj.advertencias[adjudicaciones.ADV_SIN_CARTEL]) == 1  # el 104

    with closing(connect(db)) as conn:
        # Identificadores como texto: el cero inicial de la cédula se conserva.
        assert conn.execute("SELECT count(*) FROM adjudicacion_proveedores WHERE cedula_proveedor = '0101000001'"
                            ).fetchone()[0] == 1
        fecha, = conn.execute("SELECT min(fecha_adj_firme) FROM adjudicaciones WHERE nro_sicop = '00000000101'").fetchone()
        assert fecha == "2026-08-18T07:22:31-06:00"
        assert conn.execute("SELECT fecha_comunicacion, permite_recursos, fecha_maxima_recursos FROM adjudicaciones"
                            " WHERE nro_sicop = '00000000102'").fetchone() == (None, None, None)
        montos = dict(conn.execute("SELECT numero_linea || moneda, monto_sin_impuestos FROM adjudicacion_lineas"
                                   " WHERE cedula_proveedor = '0101000001'"))
        assert montos == {"1CRC": "2000.00", "2USD": "300"}
        # Rastreable: cada línea guardada tiene su fila original en raw_snapshots, con la misma huella.
        sin_original = conn.execute(
            "SELECT count(*) FROM adjudicacion_lineas l WHERE NOT EXISTS (SELECT 1 FROM raw_snapshots s"
            " WHERE s.entity = 'adjudicacion_linea' AND s.content_hash = l.content_hash)").fetchone()[0]
        assert sin_original == 0


def test_el_mismo_zip_no_se_importa_dos_veces(importada, tmp_path):
    db, _ = importada
    with closing(connect(db)) as conn:
        partes = adjudicaciones.import_zip(conn, armar_zip(tmp_path / "otra-vez.zip"), "sintetico", tmp_path / "raw")
        assert all(r.ya_importado for _, r in partes)
        assert conn.execute("SELECT count(*) FROM adjudicacion_lineas").fetchone()[0] == 5


def test_zip_incompleto_no_importa_nada(db, tmp_path):
    with closing(connect(db)) as conn, pytest.raises(zip_pliegos.ZipInvalido, match="adjudicaciones en firme"):
        adjudicaciones.import_zip(conn, armar_zip(tmp_path / "a.zip", sin="Det Proveedores Adj.csv"),
                                  "sintetico", tmp_path / "raw")


def test_rechaza_moneda_y_descuento_imposibles(db, tmp_path):
    malas = [LIN[0], "00000000101;4;0101000001;1;10;colones;0;0;0;0;450", "00000000101;5;0101000001;1;10;CRC;11;0;0;0;450"]
    with closing(connect(db)) as conn:
        lin = dict(adjudicaciones.import_zip(conn, armar_zip(tmp_path / "a.zip", lin=malas), "sintetico",
                                             tmp_path / "raw"))["adjudicacion_lineas"]
    assert [r.linea for r in lin.rechazos] == [3, 4]
    assert "Moneda" in lin.rechazos[0].motivo and "descuento" in lin.rechazos[1].motivo


def test_cli_importa_el_zip(db, tmp_path, capsys):
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "RAW_DATA_DIR": str(tmp_path / "raw")})
    codigo = main(["import", "--report", "adjudicaciones", "--path", str(armar_zip(tmp_path / "a.zip")),
                   "--origen", "sintetico"], settings=settings)
    salida = capsys.readouterr().out
    assert codigo == 0
    assert salida.count("Importación #") == 3 and "Reporte: adjudicacion_lineas" in salida


# --- Resumen de competencia -----------------------------------------------------------------------------------

def test_quien_gana_por_familia_con_montos_por_moneda(importada):
    db, _ = importada
    r, familias = _resumen(db)
    gps = familias["gps_flotas"]
    assert gps.carteles == {"00000000101", "00000000102"}
    uno, otra = gps.competidores
    assert (uno.clave, uno.veces, uno.cedulas) == ("Competidor Uno", 2, {"0101000001", "3101000003"})
    assert uno.montos == {"CRC": Decimal("2000.00"), "USD": Decimal("300")}  # nunca mezcladas
    assert uno.instituciones == {"Municipalidad Sintética A": 1, "Ministerio Sintético B": 1}
    assert uno.carteles_sin_lineas == 1  # el 102 no trae líneas
    # La cédula sin nombre en el YAML aparece igual; su línea con dos registros distintos no se suma.
    assert (otra.clave, otra.nombre, otra.veces, otra.montos, otra.lineas_en_conflicto) == (
        "cedula:3101000002", None, 1, {}, 2)
    assert r.sin_nombre == 1
    assert (r.cobertura.carteles_adjudicados, r.cobertura.con_cartel, r.cobertura.clasificados) == (4, 3, 2)


def test_filtro_por_periodo_y_prioridad(importada):
    db, _ = importada
    _, familias = _resumen(db, competencia.Filtro(desde=date(2026, 9, 1)))
    assert familias["gps_flotas"].carteles == {"00000000102"}
    _, familias = _resumen(db, competencia.Filtro(hasta=date(2026, 8, 18)))
    assert familias["gps_flotas"].carteles == {"00000000101"}  # el día del «hasta» cuenta completo
    _, familias = _resumen(db, competencia.Filtro(prioridad="alta"))
    assert familias["gps_flotas"].carteles == {"00000000101"}
    assert competencia.Filtro.desde_texto("2026-13-40", "", "inventada") == competencia.Filtro()


def test_registros_detras_de_una_cifra(importada):
    db, _ = importada
    nombres = {"0101000001": "Competidor Uno", "3101000003": "Competidor Uno"}
    with closing(connect(db)) as conn:
        version = conn.execute("SELECT rules_version FROM opportunity_assessments LIMIT 1").fetchone()[0]
        carteles = competencia.registros(conn, version, competencia.Filtro(), nombres, "gps_flotas", "Competidor Uno")
        otra = competencia.registros(conn, version, competencia.Filtro(), nombres, "gps_flotas", "cedula:3101000002")
    assert [c.nro_sicop for c in carteles] == ["00000000102", "00000000101"]
    lineas = carteles[1].lineas
    assert [(l.numero_linea, l.moneda, l.monto, l.registros) for l in lineas] == [
        ("1", "CRC", Decimal("2000.00"), 1), ("2", "USD", Decimal("300"), 1)]
    assert lineas[0].archivo == "Det Lineas Adjudicadas.csv" and lineas[0].import_id
    assert [l.registros for l in otra[0].lineas] == [2, 2]


# --- config/competidores.yaml -------------------------------------------------------------------------------

def test_competidores_yaml(tmp_path):
    ruta = tmp_path / "c.yaml"
    assert competencia.cargar_competidores(ruta) == {}  # sin archivo: todos por cédula
    ruta.write_text(COMPETIDORES, encoding="utf-8")
    assert competencia.cargar_competidores(ruta) == {"0101000001": "Competidor Uno", "3101000003": "Competidor Uno"}
    for contenido, mensaje in [
        ('competidores:\n  "X":\n    cedulas: [3101000000]\n', "entre comillas"),
        ('competidores:\n  "X":\n    cedulas: ["3-101-000000"]\n', "solo dígitos"),
        ('competidores:\n  "X":\n    cedulas: ["1"]\n  "Y":\n    cedulas: ["1"]\n', "en «X» y en «Y»"),
        ('competidores:\n  "X":\n    alias: ["1"]\n', "solo «cedulas:»"),
        ('competidores: [\n', "no se puede leer"),
    ]:
        ruta.write_text(contenido, encoding="utf-8")
        with pytest.raises(competencia.CompetidoresError, match=mensaje):
            competencia.cargar_competidores(ruta)


def test_el_yaml_del_repositorio_es_valido():
    competencia.cargar_competidores()


# --- Página «Competencia» ------------------------------------------------------------------------------------

@pytest.fixture
def cliente(importada, monkeypatch, tmp_path):
    db, _ = importada
    yaml = tmp_path / "competidores.yaml"
    yaml.write_text(COMPETIDORES, encoding="utf-8")
    monkeypatch.setattr(competencia, "COMPETIDORES_PATH", yaml)
    monkeypatch.setenv("DATABASE_PATH", str(db))
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", CONTRASENA)
    c = TestClient(app)
    assert iniciar_sesion(c).status_code == 303
    return c, yaml


def test_la_pagina_exige_sesion(importada, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(importada[0]))
    respuesta = TestClient(app).get("/competencia", follow_redirects=False)
    assert respuesta.status_code in (302, 303, 307) and "/login" in respuesta.headers["location"]


def test_pagina_competencia(cliente):
    c, _ = cliente
    html = c.get("/competencia").text
    assert "GPS y gestión de flotas" in html and "Competidor Uno" in html
    assert "2 000.00 CRC" in html and "300.00 USD" in html
    assert "Cédula 3101000002" in html and "2 registros sin sumar" in html
    assert "familia=gps_flotas" in html and "competidor=Competidor+Uno" in html
    assert "Competidor Uno" not in c.get("/competencia?desde=2026-10-01").text


def test_pagina_de_registros(cliente):
    c, _ = cliente
    html = c.get("/competencia/registros?familia=gps_flotas&competidor=cedula%3A3101000002").text
    assert "00000000101" in html and "no sumado: 2 registros distintos" in html and "registro #" in html


def test_yaml_con_error_no_tumba_la_pagina(cliente):
    c, yaml = cliente
    yaml.write_text('competidores:\n  "X":\n    cedulas: [3101000000]\n', encoding="utf-8")
    html = c.get("/competencia").text
    assert "entre comillas" in html and "Cédula 0101000001" in html


def test_sin_adjudicaciones_explica_como_importarlas(db, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(db))
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", CONTRASENA)
    c = TestClient(app)
    iniciar_sesion(c)
    assert "--report adjudicaciones" in c.get("/competencia").text
