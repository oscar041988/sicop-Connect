"""«¿Cumple?» en el resumen con IA y en el Reporte de cartel (pedido de Ivania, 2026-11-05; migración 0038).

Base, lista y usuarios SINTÉTICOS de tests/test_asistente.py; resumen INVENTADO guardado directo en ia_summaries.
Nunca se llama a OpenAI (la página del resumen solo necesita AI_MODE=openai para mostrarse).
"""

import json
import sqlite3
from contextlib import closing
from datetime import timedelta

import pytest

from app import asistente, cumplimiento, seguimiento
from app.ai import reporte, verificacion
from app.config import load_settings
from app.database import connect
from app.historial import Quien
from tests.test_asistente import AHORA, ANA, NRO, _empezar, _post, _responder, lista, web  # noqa: F401
from tests.test_panel import db  # noqa: F401 (fixture)
from tests.test_reporte import _resumen

LINEAS = [{"linea": "1", "bien_o_servicio": "Rastreador GPS SINTÉTICO", "cantidad": "50",
           "especificaciones_clave": ["Batería de 8 h"], "cita": "[DOC 1 · pág. 3]"},
          {"linea": "2", "bien_o_servicio": "Plataforma <script>alert(1)</script>", "cantidad": "1",
           "especificaciones_clave": [], "cita": "[DOC 1 · pág. 4]"}]


def _requisitos(db_path):
    with closing(connect(db_path)) as conn:
        return {i.id: i.requisito for i in verificacion.listar(conn, NRO)}


def _guardar_resumen(db_path, ids, extra=None, que_piden=LINEAS):
    textos = _requisitos(db_path)
    reqs = [{"requisito": textos[ids[k]], "tipo": "legal", "excluyente": k in ("sicop", "anos"),
             "cita": "[DOC 1 · pág. 1]"} for k in ("sicop", "anos", "patente", "cond")]
    reqs += extra or []
    datos = {**_resumen(), "que_piden": que_piden, "requerimientos": reqs}
    with closing(connect(db_path)) as conn:
        conn.execute("INSERT INTO ia_summaries (nro_sicop, prompt_version, modelo, huella, resumen_json, estado,"
                     " creado_en) VALUES (?, 'v2', 'modelo-simulado', ?, ?, 'ok', '2026-11-03T09:00:00-06:00')",
                     (NRO, "a" * 64, json.dumps(datos, ensure_ascii=False)))
        conn.commit()
    return datos


def test_sin_asistente_todo_queda_sin_evaluar(lista):
    db_path, ids, _ = lista
    datos = _guardar_resumen(db_path, ids)
    with closing(connect(db_path)) as conn:
        reqs = cumplimiento.de_requerimientos(conn, NRO, AHORA.date())
        lineas = cumplimiento.de_lineas(conn, NRO)
    assert reqs == {} and lineas == {}
    assert {cumplimiento.requerimiento(reqs, q).texto for q in datos["requerimientos"]} == {"Sin evaluar"}
    assert cumplimiento.linea(reqs, lineas, LINEAS[0]).texto == "Sin evaluar"


def test_requerimientos_con_el_estado_del_asistente(lista):
    db_path, ids, settings = lista
    datos = _guardar_resumen(db_path, ids, extra=[{"requisito": "Un requisito que no está en la lista",
                                                   "tipo": "legal", "excluyente": False, "cita": ""}])
    _empezar(db_path)
    _responder(db_path, settings, ids["sicop"], valor_si_no="1")
    _responder(db_path, settings, ids["anos"], valor_numero="2")          # pide al menos 3
    with closing(connect(db_path)) as conn:
        reqs = cumplimiento.de_requerimientos(conn, NRO, AHORA.date())
    estado = [cumplimiento.requerimiento(reqs, q) for q in datos["requerimientos"]]
    assert [e.texto for e in estado] == ["Cumple", "No cumple", "Falta", "Informativo", "Sin evaluar"]
    assert estado[1].detalle.startswith("2 años < 3 años")


def test_marcar_una_linea_guarda_historial_y_vale_la_ultima(lista):
    db_path, ids, _ = lista
    datos = _guardar_resumen(db_path, ids)
    clave = cumplimiento.clave_linea(LINEAS[0])
    with closing(connect(db_path)) as conn:
        cumplimiento.marcar(conn, NRO, datos, clave, "revisar", "falta la ficha", ANA, AHORA)
        cumplimiento.marcar(conn, NRO, datos, clave, "cumple", "", Quien(None, "Luis Sintético"), AHORA)
        e = cumplimiento.linea({}, cumplimiento.de_lineas(conn, NRO), LINEAS[0])
        assert (e.texto, e.detalle) == ("Cumple", "Marcado por Luis Sintético el 03/11/2026.")
        assert cumplimiento.linea({}, cumplimiento.de_lineas(conn, NRO), LINEAS[1]).texto == "Sin evaluar"
        for estado, clave_mala, msj in (("talvez", clave, "Elige"), ("cumple", "otra-fila", "ya no está")):
            with pytest.raises(cumplimiento.MarcaInvalida, match=msj):
                cumplimiento.marcar(conn, NRO, datos, clave_mala, estado, "", ANA, AHORA)
        with pytest.raises(cumplimiento.MarcaInvalida, match="500"):
            cumplimiento.marcar(conn, NRO, datos, clave, "cumple", "x" * 501, ANA, AHORA)
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM resumen_lineas_cumple")
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE resumen_lineas_cumple SET estado = 'no_cumple'")
        assert conn.execute("SELECT COUNT(*) FROM resumen_lineas_cumple").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM audit_log WHERE accion = 'marcar_cumple_linea'").fetchone()[0] == 2


def test_el_reporte_lleva_la_columna_en_las_dos_tablas(lista):
    db_path, ids, _ = lista
    datos = _guardar_resumen(db_path, ids)
    with closing(connect(db_path)) as conn:
        d = reporte.datos(conn, NRO, AHORA)
        assert [i["cumple"].texto for i in d["piden"]] == ["Sin evaluar", "Sin evaluar"]
        assert all(q["cumple"].texto == "Sin evaluar" for q in d["reqs"])
        cumplimiento.marcar(conn, NRO, datos, cumplimiento.clave_linea(LINEAS[0]), "no_cumple", "", ANA, AHORA)
        html = reporte.html(reporte.datos(conn, NRO, AHORA))
    assert html.count("<th class=\"col-cumple\">¿Cumple?</th>") == 2 and 'class="cumple cumple-no_cumple">No cumple' in html
    assert "&lt;script&gt;" in html and "<script>alert(1)" not in html


def test_reporte_se_reutiliza_solo_si_no_cambian_los_estados(lista, monkeypatch, tmp_path):
    db_path, ids, settings = lista
    datos = _guardar_resumen(db_path, ids)
    monkeypatch.setattr(reporte, "pdf", lambda contenido, nro: b"%PDF /Type /Page " + contenido.encode()[:50])
    settings = load_settings(env_file=None, environ={**settings.raw, "REPORTS_DIR": str(tmp_path / "reportes")})
    with closing(connect(db_path)) as conn:
        primero = reporte.generar(conn, settings, NRO, ANA, AHORA)
        assert reporte.generar(conn, settings, NRO, ANA, AHORA).reutilizado
        cumplimiento.marcar(conn, NRO, datos, cumplimiento.clave_linea(LINEAS[1]), "cumple", "", ANA, AHORA)
        nuevo = reporte.generar(conn, settings, NRO, ANA, AHORA)
        assert not nuevo.reutilizado and nuevo.id != primero.id and nuevo.cumple_huella != primero.cumple_huella


def test_pagina_del_resumen_muestra_las_columnas_y_solo_el_encargado_marca(web, monkeypatch):
    db_path, ids, _, c, u = web
    monkeypatch.setenv("AI_MODE", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "clave-simulada")
    monkeypatch.setenv("OPENAI_MODEL", "modelo-simulado")
    _guardar_resumen(db_path, ids)
    ruta = f"/oportunidades/{NRO}/resumen"
    pagina = " ".join(c["ana"].get(ruta).text.split())
    assert pagina.count("<th>¿Cumple?</th>") == 2 and "Marcar</summary>" not in pagina
    assert "primero «Dar seguimiento»" in pagina and "todavía no tiene el asistente empezado" in pagina
    with closing(connect(db_path)) as conn:
        seguimiento.abrir(conn, NRO, Quien(u["oscar"], "Oscar Sintético"), AHORA)
        seguimiento.asignar(conn, NRO, u["ivania"], Quien(u["oscar"], "Oscar Sintético"), AHORA)
    clave = cumplimiento.clave_linea(LINEAS[0])
    r = _post(c["ana"], f"{ruta}/cumple", {"clave": clave, "estado": "cumple"})
    assert r.status_code == 403                                                     # encargada de otro cartel
    assert "Marcar</summary>" in c["ivania"].get(ruta).text
    r = _post(c["ivania"], f"{ruta}/cumple", {"clave": clave, "estado": "no_cumple", "nota": "Batería de 6 h"})
    assert r.status_code == 303 and r.headers["location"] == f"{ruta}#que-piden"
    pagina = " ".join(c["ivania"].get(ruta).text.split())
    assert "Guardado: No cumple." in pagina and "Marcado por Ivania Sintética" in pagina and "Batería de 6 h" in pagina
    assert "Marcar</summary>" not in c["ivania"].get(f"{ruta}?imprimir=1").text      # al imprimir, sin formulario
    r = _post(c["ivania"], f"{ruta}/cumple", {"clave": clave, "estado": "quizas"})
    assert "Elige «Cumple», «No cumple» o «Revisar»." in c["ivania"].get(ruta).text


# --- Filas de «Qué piden» como preguntas del asistente -------------------------------------------------------------

def _filas(db_path):
    with closing(connect(db_path)) as conn:
        return {i.clave: i for i in verificacion.listar(conn, NRO) if verificacion.es_fila(i)}


def test_las_filas_de_que_piden_entran_al_asistente_sin_duplicarse(lista):
    db_path, ids, _ = lista
    _guardar_resumen(db_path, ids)
    _empezar(db_path)
    filas = _filas(db_path)
    assert len(filas) == 2
    fila = filas[verificacion.PREFIJO_FILA + cumplimiento.clave_linea(LINEAS[0])]
    assert (fila.requisito, fila.tipo_evidencia, fila.excluyente) == (
        "Qué piden · Línea 1: Rastreador GPS SINTÉTICO (50) — Batería de 8 h", "si_no", False)
    with closing(connect(db_path)) as conn:
        paso = next(p for p in asistente.recorrido(conn, NRO, AHORA.date()) if p.item.id == fila.id)
        assert paso.pregunta.endswith("[DOC 1 · pág. 3] ¿Hermatix lo puede ofrecer?")
        antes = conn.total_changes
        assert verificacion.sincronizar_filas(conn, NRO) == 0 and conn.total_changes == antes   # nada cambió: no escribe
        # Una persona quita la fila 1; llega un resumen nuevo sin la fila 2: la 1 sigue quitada y la 2 se retira.
        verificacion.quitar(conn, NRO, fila.id, ANA)
    _guardar_resumen(db_path, ids, que_piden=LINEAS[:1])
    with closing(connect(db_path)) as conn:
        verificacion.sincronizar_filas(conn, NRO)
    assert _filas(db_path) == {}


def test_vale_lo_mas_reciente_entre_el_asistente_y_la_marca(lista):
    db_path, ids, settings = lista
    datos = _guardar_resumen(db_path, ids)
    _empezar(db_path)
    clave = cumplimiento.clave_linea(LINEAS[0])
    fila = _filas(db_path)[verificacion.PREFIJO_FILA + clave]

    def estado():
        with closing(connect(db_path)) as conn:
            return cumplimiento.linea(cumplimiento.de_requerimientos(conn, NRO, AHORA.date()),
                                      cumplimiento.de_lineas(conn, NRO), LINEAS[0])

    assert estado().texto == "Falta"                                         # sin responder ni marcar
    _responder(db_path, settings, fila.id, valor_si_no="1")                  # 15:00 · asistente: Sí
    assert (estado().texto, estado().detalle) == ("Cumple", "Asistente: Respondió «Sí».")
    with closing(connect(db_path)) as conn:                                   # 16:00 · marca: No cumple
        cumplimiento.marcar(conn, NRO, datos, clave, "no_cumple", "otra batería", ANA, AHORA + timedelta(hours=1))
    assert estado().texto == "No cumple" and "otra batería" in estado().detalle
    with closing(connect(db_path)) as conn:                                   # 17:00 · asistente otra vez: Sí
        asistente.responder(conn, settings, NRO, fila.id, asistente.Entrada(valor_si_no="1"), None, ANA,
                            AHORA + timedelta(hours=2))
    assert estado().texto == "Cumple"
    with closing(connect(db_path)) as conn:                                   # el reporte lo lleva
        assert reporte.datos(conn, NRO, AHORA)["piden"][0]["cumple"].texto == "Cumple"


def test_marca_sin_respuesta_del_asistente_gana(lista):
    db_path, ids, _ = lista
    datos = _guardar_resumen(db_path, ids)
    _empezar(db_path)
    with closing(connect(db_path)) as conn:
        cumplimiento.marcar(conn, NRO, datos, cumplimiento.clave_linea(LINEAS[1]), "revisar", "", ANA, AHORA)
        e = cumplimiento.linea(cumplimiento.de_requerimientos(conn, NRO, AHORA.date()),
                               cumplimiento.de_lineas(conn, NRO), LINEAS[1])
    assert e.texto == "Revisar"
