"""Reporte de cartel Hermatix en PDF, máximo 3 páginas (Reporte con IA, lección 4; explicación al final, prompt v6).

Base SINTÉTICA de tests/test_panel.py; resúmenes INVENTADOS guardados directo en ia_summaries (nunca se llama a
OpenAI). El PDF se hace con el Chromium de Playwright, como en la app.
"""

import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import panel, respaldo, usuarios
from app.ai import reporte
from app.config import load_settings
from app.database import apply_migrations, connect
from app.historial import Quien
from app.main import app
from tests.test_panel import CONTRASENA, db, iniciar_sesion  # noqa: F401 (db es una fixture)

NRO = "00000000001"
ANA = Quien(None, "Ana Sintética")
AHORA = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)
NO = "no encontrado"
EXPLICACION = ("Piden el monitoreo GPS de la flotilla municipal, que es lo que hace FleetMatix [DOC 1 · pág. 3]. "
               "SINTÉTICO. " * 12 + "\n\n" + "El plazo de entrega es de 30 días hábiles [DOC 1 · pág. 2]. "
               + "Texto SINTÉTICO de la explicación. " * 15)


def _dato(valor, cita="[DOC 1 · pág. 2]"):
    return {"valor": valor, "cita": cita}


def _resumen(n_reqs=5, n_lineas=2, texto="Compra SINTÉTICA de monitoreo GPS para la flotilla municipal.",
             explicacion=EXPLICACION, recomendacion="dar_seguimiento"):
    datos = {
        "de_que_trata": texto,
        "que_piden": [{"linea": str(i + 1), "bien_o_servicio": f"Servicio SINTÉTICO {i + 1} con ñ y tildes: camión",
                       "cantidad": "10", "especificaciones_clave": [f"Especificación {j}" for j in range(5)],
                       "cita": "[DOC 1 · pág. 3]"} for i in range(n_lineas)],
        "requerimientos": [{"requisito": f"Requisito SINTÉTICO número {i} <script>alert(1)</script>",
                            "tipo": "legal", "excluyente": i % 3 == 0, "cita": f"[DOC 1 · pág. {i + 1}]"}
                           for i in range(n_reqs)],
        "kpi_pliego": {"plazo_entrega": _dato("30 días hábiles"), "vigencia_contrato": _dato(NO, NO),
                       "garantia_participacion_pct": _dato(NO, NO), "garantia_cumplimiento_pct": _dato("5 %"),
                       "peso_precio_pct": _dato("100 %"), "nivel_riesgo": _dato("bajo")},
        "plazos": {"cierre_recepcion": _dato("2026-10-04 10:00", "SICOP"), "apertura_ofertas": _dato(NO, NO),
                   "otros": [{"plazo": f"Plazo {i}", "valor": f"{i} días", "cita": "[DOC 1 · pág. 4]"}
                             for i in range(6)]},
        "monto_estimado": {"valor": "999999999.00", "moneda": "CRC", "cita": "[DOC 1 · pág. 1]"},  # NO se usa
        "criterios_de_evaluacion": [{"criterio": "Precio", "peso": "100 %", "cita": "[DOC 1 · pág. 5]"}],
        "encaje_hermatix": {"familia": "gps_flotas", "producto": "FleetMatix", "por_que": "Pide rastreo GPS."},
        "riesgos_y_dudas": [{"riesgo": "Ninguno sintético", "cita": NO}],
        "recomendacion": recomendacion,
        "justificacion": "Pide exactamente lo que ofrece Hermatix (SINTÉTICO).",
    }
    if explicacion is not None:                       # None: resumen anterior al prompt v6, sin el campo
        datos["explicacion_recomendacion"] = explicacion
    return datos


def _guardar_resumen(conn, datos, nro=NRO):
    rid = conn.execute(
        "INSERT INTO ia_summaries (nro_sicop, prompt_version, modelo, huella, resumen_json, estado, creado_en)"
        " VALUES (?, 'v5', 'modelo-simulado', ?, ?, 'ok', '2026-10-01T09:00:00-06:00')",
        (nro, "a" * 64, json.dumps(datos, ensure_ascii=False))).lastrowid
    conn.commit()
    return rid


@pytest.fixture
def base(db, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reportes"))
    with closing(connect(db)) as conn:
        conn.execute("INSERT INTO tender_lines (nro_sicop, numero_linea, codigo_identificacion, cantidad_solicitada,"
                     " precio_unitario_estimado, moneda, estimado_linea, content_hash, first_seen, last_seen)"
                     " VALUES (?, '1', '4321', '3', '1500.50', 'CRC', '4501.50', 'h', 't', 't')", (NRO,))
        conn.commit()
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "REPORTS_DIR": str(tmp_path / "reportes")})
    return db, settings


def _texto_pdf(contenido: bytes) -> bytes:
    return contenido


def test_cartel_corto_y_cartel_largo_caben_en_3_paginas(base):
    db, settings = base
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen(n_reqs=3, n_lineas=1))
        corto = reporte.generar(conn, settings, NRO, ANA, AHORA)
        largo_texto = "Texto SINTÉTICO muy largo. " * 200
        _guardar_resumen(conn, _resumen(n_reqs=120, n_lineas=40, texto=largo_texto, explicacion="Muy larga. " * 400))
        largo = reporte.generar(conn, settings, NRO, ANA, AHORA)
    assert reporte.MAX_PAGINAS == 3
    assert 1 <= corto.paginas <= 3 and 1 <= largo.paginas <= 3
    assert reporte.contar_paginas(largo.ruta.read_bytes()) == largo.paginas
    assert corto.ruta.is_file() and largo.ruta.is_file() and corto.ruta != largo.ruta   # el anterior no se borra


def test_los_kpi_de_sicop_salen_de_la_base_no_del_modelo(base):
    db, settings = base
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen())
        kpis = dict(reporte.kpis_sicop(conn, NRO, AHORA))
        det = panel.detalle(conn, NRO, panel.version_vigente(conn), AHORA)
        d = reporte.datos(conn, NRO, AHORA)
    monto_panel = " · ".join(panel.monto(m.valor, mon) for mon, m in det.compra.estimado_por_moneda.items())
    assert kpis["Monto estimado"] == monto_panel and "999999999" not in kpis["Monto estimado"]
    assert kpis["Líneas · unidades"] == "1 · 3"
    assert panel.cuenta_regresiva(det.compra.fecha_cierre_recepcion, AHORA) in kpis["Cierre de recepción"]
    assert kpis["Tipo de procedimiento"] == "Licitación Reducida" and kpis["Encaje con Hermatix (reglas)"].startswith("Alta")
    html = reporte.html(d)
    assert "999999999" not in html and monto_panel in html


def test_no_encontrado_escapado_y_limites(base):
    db, settings = base
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen(n_reqs=25, n_lineas=12))
        d = reporte.datos(conn, NRO, AHORA)
    html = reporte.html(d)
    assert "<dt>Vigencia del contrato</dt><dd>no encontrado" in html              # se ve, no queda vacío
    assert "&lt;script&gt;" in html and "<script>alert(1)" not in html            # texto, no código
    assert "con ñ y tildes: camión" in html and 'charset="utf-8"' in html
    assert len(d["reqs"]) == 10 and d["mas_reqs"] == 15 and "y 15 más en el panel" in html
    assert d["reqs"][0]["excluyente"] and len(d["piden"]) == 8 and "y 4 más en el panel" in html
    assert reporte.PIE in reporte._pie_pdf(NRO)


def test_reutiliza_si_el_resumen_no_cambio_y_la_tabla_no_se_toca(base):
    db, settings = base
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen())
        primero = reporte.generar(conn, settings, NRO, ANA, AHORA)
        otra_vez = reporte.generar(conn, settings, NRO, ANA, AHORA)
        assert otra_vez.reutilizado and otra_vez.id == primero.id
        forzado = reporte.generar(conn, settings, NRO, ANA, datetime(2026, 10, 1, 16, 0, tzinfo=timezone.utc),
                                  forzar=True)
        assert forzado.id != primero.id and primero.ruta.is_file()
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM ia_reports")
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE ia_reports SET paginas = 1")
        with pytest.raises(reporte.ReporteError, match="todavía no tiene resumen"):
            reporte.generar(conn, settings, "00000000002", ANA, AHORA)


def test_migrate_dos_veces_y_el_respaldo_trae_los_reportes(base, tmp_path):
    db, settings = base
    assert apply_migrations(db) == []
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen())
        reporte.generar(conn, settings, NRO, ANA, AHORA)
    r = respaldo.respaldar(db, tmp_path / "respaldos", AHORA, reportes=settings.reports_dir)
    assert r.datos["reportes"]["archivos"] == 1


def test_en_el_panel_reporte_pdf_descarga_el_archivo(base):
    db, settings = base
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "ana@ejemplo.test", "Ana Sintética", CONTRASENA)
        _guardar_resumen(conn, _resumen())
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, "ana@ejemplo.test").status_code == 303
    r = cliente.get(f"/oportunidades/{NRO}/reporte")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and 1 <= reporte.contar_paginas(r.content) <= reporte.MAX_PAGINAS
    assert re.search(r'filename="reporte_00000000001_\d{8}-\d{6}\.pdf"', r.headers["content-disposition"])
    assert cliente.get("/oportunidades/00000000002/reporte").status_code == 404     # sin resumen


@pytest.mark.parametrize("descripcion, esperado", [
    ("cOMPRA\xa0DE\xa0CAMARAS\xa0Y\xa0ACCESORIOS", "COMPRA\xa0DE\xa0CAMARAS\xa0Y\xa0ACCESORIOS"),  # mayúsculas invertidas
    ("COMPRA DE GPS", "COMPRA DE GPS"),
    ("Compra de monitoreo GPS para la CCSS", "Compra de monitoreo GPS para la CCSS"),          # bien escrito: igual
    (None, "(sin título)")])
def test_el_titulo_casi_todo_en_mayusculas_sale_todo_en_mayusculas(descripcion, esperado):
    assert reporte.titulo(descripcion) == esperado


@pytest.mark.parametrize("clave, titulo", [("dar_seguimiento", "Dar seguimiento"),
                                           ("revisar_requisitos", "Revisar requisitos"), ("descartar", "Descartar")])
def test_al_final_explica_por_que_se_recomienda(base, clave, titulo):
    """Oscar (2026-11-09): media página al final con el porqué de la recomendación, para las tres."""
    db, _ = base
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen(recomendacion=clave))
        d = reporte.datos(conn, NRO, AHORA)
    html = reporte.html(d)
    assert len(d["explicacion"]) == 2                                   # los dos párrafos se conservan
    assert d["explicacion"][0].startswith("Piden el monitoreo GPS")
    assert f"<h2>Por qué se recomienda: {titulo}</h2>" in html and f'class="explicacion rec-{clave}"' in html
    assert html.index("Por qué se recomienda") > html.index("Riesgos y dudas")          # al final del reporte
    assert "La decisión es del encargado." in html and "anterior a la explicación" not in html


def test_resumen_anterior_a_v6_sin_explicacion(base):
    db, _ = base
    with closing(connect(db)) as conn:
        _guardar_resumen(conn, _resumen(explicacion=None))
        d = reporte.datos(conn, NRO, AHORA)
    html = reporte.html(d)
    assert d["explicacion"] == []
    assert "Pide exactamente lo que ofrece Hermatix (SINTÉTICO)." in html.split("Por qué se recomienda")[1]
    assert "anterior a la explicación detallada" in html


def test_la_explicacion_tiene_tope():
    assert reporte._explicacion(NO) == [] and reporte._explicacion(None) == []
    larga = reporte._explicacion("palabra " * 1000)
    assert len(larga) == 1 and len(larga[0]) <= reporte.MAX_EXPLICACION and larga[0].endswith("…")
