"""Calidad de las reglas (A3): precisión y cobertura por familia, errores y mediciones guardadas.

Datos SINTÉTICOS: reglas y golden set escritos en una carpeta temporal (los resultados se calculan a mano) y los
carteles de tests/test_panel.py. La prueba del comando usa además el golden set REAL de tests/golden.
"""

import sqlite3
from contextlib import closing
from decimal import Decimal

import pytest

from app import calidad
from app.cli import main
from app.config import load_settings
from app.database import connect
from app.matching.reglas import cargar_reglas
from tests.test_avisos import admin_y_encargada, base  # noqa: F401
from tests.test_panel import AHORA, CR, db  # noqa: F401

REGLAS = """\
familias:
  gps_flotas:
    producto: fleetmatix
    senales_alta: ["monitoreo gps"]
    senales_media: ["gps"]
    contexto: ["flotilla"]
"""
ENCABEZADO = "nro_sicop;titulo;etiqueta;familia_esperada;confirmada;nota;fuente;actualizado"
GOLDEN = [
    "00000000901;Servicio de monitoreo GPS;interesa;gps_flotas;sí;;sintético;2026-10-23",           # alertado: bien
    "00000000902;Alquiler de GPS para la flotilla;no_interesa;;sí;;sintético;2026-10-23",           # falsa alerta
    "00000000903;Rastreo satelital de vehículos;interesa;gps_flotas;sí;;sintético;2026-10-23",       # no alertado
    "00000000904;Compra de sillas;no_interesa;;sí;;sintético;2026-10-23",                            # bien: nada
    "00000000905;Monitoreo GPS provisional;interesa;gps_flotas;no;;sintético;2026-10-23",            # no cuenta
]


def _golden(carpeta, filas=GOLDEN):
    carpeta.mkdir(exist_ok=True)
    (carpeta / "golden_set.csv").write_text("\n".join([ENCABEZADO, *filas]) + "\n", encoding="utf-8-sig")
    return carpeta


@pytest.fixture
def reglas(tmp_path):
    archivo = tmp_path / "reglas.yaml"
    archivo.write_text(REGLAS, encoding="utf-8")
    return archivo


def test_precision_cobertura_y_errores_por_familia(reglas, tmp_path):
    m = calidad.medir(cargar_reglas(reglas), golden_dir=_golden(tmp_path / "golden"))

    gps = m.por_familia["gps_flotas"]
    assert (gps.alertas, gps.verdaderos, gps.relevantes, gps.cubiertos) == (2, 1, 2, 1)
    assert gps.precision == gps.cobertura == Decimal("50.0")
    assert m.contar("golden") == 4  # la provisional no cuenta
    assert [(e.tipo, e.caso.nro_sicop) for e in m.errores] == [("falsa_alerta", "00000000902"),
                                                                ("no_alertado", "00000000903")]
    # Cada error trae su evidencia: qué regla alertó y con qué frase.
    falsa = m.errores[0].caso.evaluaciones[0]
    assert (falsa.encaje, falsa.regla) == ("media", "senales_media: gps + contexto: flotilla")


def test_un_cambio_en_el_yaml_se_ve_en_la_siguiente_medicion(reglas, tmp_path, db):
    golden = _golden(tmp_path / "golden")
    with closing(connect(db)) as conn:
        antes = calidad.medir(cargar_reglas(reglas), golden_dir=golden)
        assert calidad.guardar(conn, antes, AHORA)[1]
        reglas.write_text(REGLAS.replace('["monitoreo gps"]', '["monitoreo gps", "rastreo satelital"]'),
                          encoding="utf-8")
        despues = calidad.medir(cargar_reglas(reglas), golden_dir=golden)
        assert calidad.guardar(conn, despues, AHORA)[1]
        evolucion = calidad.historial(conn)

    assert despues.version != antes.version
    assert despues.por_familia["gps_flotas"].cobertura == Decimal("100.0")
    assert [(h.version, h.total.cobertura) for h in evolucion] == [(despues.version, Decimal("100.0")),
                                                                    (antes.version, Decimal("50.0"))]


def _revisar(conn, nro, decision, motivo=None):
    conn.execute("INSERT INTO reviews (nro_sicop, responsable, decision, motivo, created_at)"
                 " VALUES (?, 'Prueba', ?, ?, '2026-10-23T10:00:00-06:00')", (nro, decision, motivo))


def test_las_revisiones_cuentan_solo_si_dicen_si_encaja(db, tmp_path):
    """Carteles de tests/test_panel.py con las reglas reales: 1 Alta, 2 Media, 3 Baja, 4 Alta, 5 nada."""
    with closing(connect(db)) as conn:
        _revisar(conn, "00000000001", "interesa")                     # encaja y alertado: bien
        _revisar(conn, "00000000002", "no_interesa", "no_encaja")     # no encaja y alertado: falsa alerta
        _revisar(conn, "00000000003", "revisar_requisitos")           # encaja, solo Baja: no alertado
        _revisar(conn, "00000000004", "interesa")
        _revisar(conn, "00000000004", "no_interesa", "plazo")         # la última manda: por plazo, no cuenta
        _revisar(conn, "00000000005", "no_se_oferta")                 # decisión de negocio: no cuenta
        m = calidad.medir(cargar_reglas(), conn, golden_dir=_golden(tmp_path / "golden", filas=[]))

    assert [c.nro_sicop for c in m.casos] == ["00000000001", "00000000002", "00000000003"]
    total = m.por_familia[calidad.TOTAL]
    assert (total.alertas, total.verdaderos, total.relevantes, total.cubiertos) == (2, 1, 2, 1)
    assert {(e.tipo, e.caso.nro_sicop) for e in m.errores} == {("falsa_alerta", "00000000002"),
                                                              ("no_alertado", "00000000003")}


def test_un_cartel_del_golden_set_no_se_cuenta_dos_veces(db, tmp_path):
    with closing(connect(db)) as conn:
        _revisar(conn, "00000000001", "interesa")
        golden = _golden(tmp_path / "golden", ["00000000001;Servicio de monitoreo GPS de vehículos;interesa;gps_flotas;"
                                               "sí;;sintético;2026-10-23"])
        m = calidad.medir(cargar_reglas(), conn, golden_dir=golden)
    assert [(c.nro_sicop, c.fuente) for c in m.casos] == [("00000000001", "golden")]


def test_con_varias_familias_esperadas_cualquiera_cuenta(tmp_path):
    archivo = tmp_path / "reglas.yaml"
    archivo.write_text(REGLAS + '  iot_frio:\n    producto: osmia_iot\n    senales_alta: ["data logger"]\n',
                       encoding="utf-8")
    golden = _golden(tmp_path / "golden",
                     ['00000000906;Data logger de temperatura;interesa;"iot_frio;gps_flotas";sí;;sintético;2026-10-23'])
    m = calidad.medir(cargar_reglas(archivo), golden_dir=golden)
    assert m.errores == []  # se alertó en iot_frio: no falta en gps_flotas
    assert m.por_familia["iot_frio"].cobertura == Decimal("100.0")
    assert m.por_familia["gps_flotas"].relevantes == 0


def test_guardar_no_repite_una_medicion_igual_y_no_se_borra(reglas, tmp_path, db):
    m = calidad.medir(cargar_reglas(reglas), golden_dir=_golden(tmp_path / "golden"))
    with closing(connect(db)) as conn:
        primera, nueva = calidad.guardar(conn, m, AHORA)
        assert nueva and calidad.guardar(conn, m, AHORA) == (primera, False)
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM rule_score_runs")
        assert conn.execute("SELECT count(*) FROM rule_scores WHERE run_id = ?", (primera,)).fetchone()[0] == 2


def test_comando_score_rules_con_el_golden_set_real(db, capsys):
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})
    assert main(["score-rules"], settings) == 0
    salida = capsys.readouterr().out
    assert "Casos: 35 del golden set" in salida and "TOTAL (por cartel)" in salida
    assert "Medición #1 guardada." in salida

    assert main(["score-rules"], settings) == 0
    assert "Sin cambios desde la medición #1" in capsys.readouterr().out


def test_la_pagina_es_solo_para_administradores(admin_y_encargada):
    ivania, encargada = admin_y_encargada
    pagina = ivania.get("/calidad")
    assert pagina.status_code == 200 and "Precisión" in pagina.text and "Cobertura" in pagina.text
    assert 'href="/calidad"' in ivania.get("/oportunidades").text
    assert encargada.get("/calidad").status_code == 403
    assert 'href="/calidad"' not in encargada.get("/oportunidades").text
