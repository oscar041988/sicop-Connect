"""Resultado de elegibilidad (asistente, lección 4): la app compara cada respuesta con su mínimo.

Requisitos y respuestas INVENTADOS: primero en memoria (sin base ni IA), después con la base SINTÉTICA de
tests/test_asistente.py. Nunca se llama a OpenAI.
"""

import json
import re
import shutil
import sqlite3
from contextlib import closing
from datetime import date
from itertools import count
from types import SimpleNamespace

import pytest

from app import asistente, elegibilidad, seguimiento
from app.ai import explicacion as ia_explicacion
from app.ai import verificacion
from app.database import MIGRATIONS_DIR, apply_migrations, connect
from app.historial import Quien
from tests.test_asistente import (AHORA, ANA, LUIS, NRO, PDF, _con_ia, _empezar, _post, _responder,  # noqa: F401
                                  lista, web)
from tests.test_panel import db  # noqa: F401 (fixture)

CIERRE = date(2026, 11, 20)
_ids = count(1)


def _item(evidencia="si_no", excluyente=False, minimo="no indicado", numero=None, unidad=None):
    n = next(_ids)
    return verificacion.Item(n, n, f"r{n}", f"Requisito SINTÉTICO {n}", "legal", evidencia, minimo, numero, None,
                             unidad, excluyente, [f"[DOC 1 · pág. {n}]"], None, None, False, "usuario", False, True,
                             None, None)


def _resp(item, estado="respondido", **valores):
    campos = {"valor_texto": None, "valor_numero": None, "valor_fecha": None, "valor_si_no": None, "unidad": None,
              "vence_el": None, "nota": None, "archivo_nombre": None, "archivo_extension": None,
              "archivo_tamano": None, **valores}
    return asistente.Respuesta(next(_ids), item.id, item.requisito, "¿pregunta?", item.tipo_evidencia, estado,
                               "usuario", None, **campos, respondido_por="Ana Sintética", creado_en="t")


def _paso(item, respuesta=None):
    return asistente.Paso(item, "¿pregunta?", "app", respuesta, None)


def _estado(item, respuesta, revision=None):
    return elegibilidad.evaluar_item(_paso(item, respuesta), CIERRE, revision)


@pytest.mark.parametrize("minimo, esperado", [
    ("al menos 3 años", ">="), ("mínimo 5 técnicos", ">="), ("3 años o más", ">="),
    ("máximo 5 días hábiles", "<="), ("no mayor al 50 %", "<="), ("a más tardar 10 días", "<="),
    ("30 días naturales", None), ("no indicado", None), ("al menos 2 y máximo 5", None), (None, None)])
def test_la_direccion_del_minimo_sale_del_texto(minimo, esperado):
    assert elegibilidad.direccion_minimo(minimo) == esperado


def test_numero_contra_su_minimo_en_las_dos_direcciones():
    anos = _item("numero", minimo="al menos 3 años", numero="3", unidad="años")
    plazo = _item("numero", minimo="máximo 5 días hábiles", numero="5", unidad="días hábiles")
    sin_direccion = _item("numero", minimo="30 días naturales", numero="30")
    sin_numero = _item("numero")
    assert _estado(anos, _resp(anos, valor_numero="8")).motivo.startswith("8 años ≥ 3 años")
    assert _estado(anos, _resp(anos, valor_numero="2")).estado == "no_cumple"
    assert _estado(plazo, _resp(plazo, valor_numero="3")).estado == "cumple"
    e = _estado(plazo, _resp(plazo, valor_numero="7"))
    assert e.estado == "no_cumple" and e.motivo.startswith("7 días hábiles > 5 días hábiles")
    assert _estado(sin_direccion, _resp(sin_direccion, valor_numero="30")).estado == "revisar"
    assert _estado(sin_numero, _resp(sin_numero, valor_numero="30")).estado == "revisar"


def test_documento_vencido_al_cierre_no_cumple():
    patente = _item("documento")
    assert _estado(patente, _resp(patente, vence_el="2026-11-19", archivo_nombre="p.pdf")).estado == "no_cumple"
    vigente = _estado(patente, _resp(patente, vence_el="2026-11-20", archivo_nombre="p.pdf"))
    assert vigente.estado == "cumple" and "contenido lo revisa una persona" in vigente.motivo
    constancias = _item("documento", minimo="al menos dos constancias", numero="2")
    assert _estado(constancias, _resp(constancias, archivo_nombre="c.pdf")).estado == "revisar"


def test_respuestas_que_no_son_un_dato():
    doc = _item("documento")
    assert _estado(doc, None).estado == "falta"
    assert _estado(doc, _resp(doc, "no_se")).estado == "falta"
    assert _estado(doc, _resp(doc, "archivo_pendiente")).motivo == "Hermatix lo tiene, pero el archivo está pendiente."
    assert _estado(doc, _resp(doc, "no_lo_tiene")).estado == "no_cumple"
    sicop = _item()
    assert _estado(sicop, _resp(sicop, valor_si_no=True)).estado == "cumple"
    assert _estado(sicop, _resp(sicop, valor_si_no=False)).estado == "no_cumple"
    texto = _item("texto")
    assert _estado(texto, _resp(texto, valor_texto="24/7")).estado == "revisar"


def test_la_revision_de_una_persona_vale_solo_para_la_respuesta_que_miro():
    soporte = _item("texto")
    r = _resp(soporte, valor_texto="24/7")
    e = _estado(soporte, r, elegibilidad.Revision(r.id, True, "coincide con el pliego", "Oscar Sintético", "t"))
    assert (e.estado, e.automatico) == ("cumple", "revisar") and e.motivo == "Revisado por Oscar Sintético: coincide con el pliego"
    otra = _resp(soporte, valor_texto="lunes a viernes")                 # cambió la respuesta: vuelve a «revisar»
    assert _estado(soporte, otra, elegibilidad.Revision(r.id, True, None, "Oscar", "t")).estado == "revisar"


def _global(*pares):
    return elegibilidad.resultado_global(elegibilidad.evaluar([_paso(i, r) for i, r in pares], CIERRE))


def test_los_cuatro_resultados():
    exc, doc, texto = _item(excluyente=True), _item("documento"), _item("texto")
    si = _resp(exc, valor_si_no=True)
    assert _global((exc, si), (doc, _resp(doc, archivo_nombre="p.pdf"))) == "puede_participar"
    assert _global((exc, si), (doc, _resp(doc, "archivo_pendiente"))) == "puede_si_completa"
    assert _global((exc, si), (texto, _resp(texto, valor_texto="x"))) == "puede_si_completa"     # revisar no excluyente
    assert _global((exc, si), (doc, None)) == "falta_informacion"
    assert _global((exc, si), (doc, _resp(doc, "no_se"))) == "falta_informacion"
    assert _global((exc, _resp(exc, valor_si_no=False)), (doc, None)) == "no_cumple_excluyente"   # el excluyente manda
    exc_texto = _item("texto", excluyente=True)
    assert _global((exc_texto, _resp(exc_texto, valor_texto="x"))) == "falta_informacion"
    assert elegibilidad.resultado_global([]) == "falta_informacion"


# --- Con base SINTÉTICA (la de tests/test_asistente.py): revisiones y constancias -----------------------------

def _calcular(db_path, quien=ANA):
    with closing(connect(db_path)) as conn:
        cid = elegibilidad.calcular(conn, NRO, quien, AHORA)
        return elegibilidad.constancia(conn, NRO, cid)


def test_la_constancia_guarda_todas_las_respuestas_y_la_version_de_la_lista(lista):
    db_path, ids, settings = lista
    _empezar(db_path)
    _responder(db_path, settings, ids["sicop"], valor_si_no="1")
    _responder(db_path, settings, ids["anos"], valor_numero="8")
    _responder(db_path, settings, ids["patente"], archivo=PDF, vence_el="2099-01-15")
    _responder(db_path, settings, ids["cierre"], estado="no_se")
    c = _calcular(db_path)
    assert c.resultado == "falta_informacion" and c.calculado_por == ANA.nombre and len(c.lista_huella) == 64
    por_item = {d["item_id"]: d for d in c.detalle}
    assert set(por_item) == {ids["sicop"], ids["anos"], ids["patente"], ids["cierre"], ids["soporte"]}   # sin multas
    assert por_item[ids["anos"]]["respuesta"] == "8 años" and por_item[ids["anos"]]["estado"] == "cumple"
    assert por_item[ids["patente"]]["respuesta"] == "permiso.pdf · vence 15/01/2099"
    assert por_item[ids["cierre"]]["estado"] == "falta" and por_item[ids["soporte"]]["respuesta"] is None
    assert "Esto es lo que falta" in c.explicacion and c.explicacion_origen == "app"
    with closing(connect(db_path)) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE eligibility_results SET resultado = 'puede_participar'")
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM eligibility_results")
        assert "calcular_resultado" in [a for (a,) in conn.execute("SELECT accion FROM audit_log")]


def test_revisar_cambia_el_resultado_y_deja_de_valer_si_cambia_la_respuesta(lista):
    db_path, ids, settings = lista
    _empezar(db_path)
    _responder(db_path, settings, ids["sicop"], valor_si_no="1")
    _responder(db_path, settings, ids["anos"], valor_numero="8")
    _responder(db_path, settings, ids["patente"], archivo=PDF)
    _responder(db_path, settings, ids["cierre"], valor_fecha="2026-12-01")
    _responder(db_path, settings, ids["soporte"], valor_texto="24/7")
    assert _calcular(db_path).resultado == "puede_si_completa"           # fecha y texto en «revisar»
    with closing(connect(db_path)) as conn:
        with pytest.raises(elegibilidad.ResultadoInvalido, match="lo compara la app"):
            elegibilidad.revisar(conn, NRO, ids["anos"], True, "", ANA, AHORA)
        elegibilidad.revisar(conn, NRO, ids["cierre"], True, "inicia a tiempo", LUIS, AHORA)
        elegibilidad.revisar(conn, NRO, ids["soporte"], True, "", LUIS, AHORA)
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM eligibility_item_reviews")
    c = _calcular(db_path)
    assert c.resultado == "puede_participar"
    assert {d["item_id"]: d for d in c.detalle}[ids["cierre"]]["revision"]["por"] == LUIS.nombre
    _responder(db_path, settings, ids["soporte"], valor_texto="lunes a viernes")   # cambió: vuelve a «revisar»
    assert _calcular(db_path).resultado == "puede_si_completa"
    with closing(connect(db_path)) as conn:
        assert len(elegibilidad.constancias(conn, NRO)) == 3                       # recalcular agrega otra


def test_documento_vencido_al_cierre_del_cartel(lista):
    db_path, ids, settings = lista
    with closing(connect(db_path)) as conn:
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = '2026-11-20T09:00:00-06:00' WHERE nro_sicop = ?",
                     (NRO,))
        conn.commit()
        assert elegibilidad.cierre_de(conn, NRO) == date(2026, 11, 20)
    _empezar(db_path)
    _responder(db_path, settings, ids["patente"], archivo=PDF, vence_el="2026-11-19")
    e = next(d for d in _calcular(db_path).detalle if d["item_id"] == ids["patente"])
    assert e["estado"] == "no_cumple" and "antes del cierre (20/11/2026)" in e["motivo"]


def test_0033_se_aplica_sobre_una_base_con_respuestas(tmp_path):
    hasta_0032 = tmp_path / "hasta_0032"
    hasta_0032.mkdir()
    for archivo in MIGRATIONS_DIR.glob("*.sql"):
        if archivo.name < "0033":
            shutil.copy(archivo, hasta_0032)
    base = tmp_path / "sicop.db"
    apply_migrations(base, hasta_0032)
    with closing(connect(base)) as conn:
        conn.execute("INSERT INTO tenders (nro_sicop, descripcion, content_hash, first_seen, last_seen)"
                     " VALUES (?, 'x', 'h', 't', 't')", (NRO,))
        conn.commit()
        item = verificacion.agregar(conn, NRO, verificacion.Cambios("Ofertar por SICOP.", "legal", "si_no", "", "",
                                                                    "", "", True), ANA)
        conn.execute("INSERT INTO eligibility_sessions (nro_sicop, iniciada_por_nombre, creado_en)"
                     " VALUES (?, 'Ana', 't')", (NRO,))       # SQL: asistente.sesion() ya lee la 0034
        conn.execute("INSERT INTO eligibility_answers (session_id, item_id, requisito, pregunta, tipo_evidencia,"
                     " estado, fuente, valor_si_no, respondido_por_nombre, creado_en) VALUES (1, ?, 'r', 'p',"
                     " 'si_no', 'respondido', 'usuario', 1, 'Ana', 't')", (item,))
        conn.commit()
    assert apply_migrations(base) == ["0033_resultado_elegibilidad.sql", "0034_revision_rapida.sql", "0035_perfil_tipos_nuevos.sql"]
    with closing(connect(base)) as conn:
        assert conn.execute("SELECT count(*) FROM eligibility_answers").fetchone() == (1,)
        assert elegibilidad.calcular(conn, NRO, ANA, AHORA) == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


# --- En la página del cartel (el «web» de tests/test_asistente.py: Oscar admin, Ana encargada de otro) --------

def test_calcular_revisar_y_descargar_la_constancia_en_la_pagina(web):
    db_path, ids, _, c, u = web
    with closing(connect(db_path)) as conn:
        seguimiento.abrir(conn, NRO, Quien(u["oscar"], "Oscar Sintético"), AHORA)
    oscar = c["oscar"]
    _post(oscar, f"/oportunidades/{NRO}/asistente/empezar")
    _post(oscar, f"/oportunidades/{NRO}/asistente/ampliar")              # después de la revisión rápida
    for item, datos in ((ids["sicop"], {"valor_si_no": "1"}), (ids["anos"], {"valor_numero": "8"}),
                        (ids["patente"], {"estado": "archivo_pendiente"}),
                        (ids["cierre"], {"valor_fecha": "2026-12-01"}), (ids["soporte"], {"valor_texto": "24/7"})):
        assert _post(oscar, f"/oportunidades/{NRO}/asistente/{item}/responder", datos).status_code == 303
    pagina = " ".join(oscar.get(f"/oportunidades/{NRO}").text.split())
    assert "Todavía no se ha calculado" in pagina and "Calcular el resultado" in pagina
    assert pagina.count('class="revisar-requisito"') == 2                  # la fecha y el texto
    r = _post(oscar, f"/oportunidades/{NRO}/asistente/resultado")
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}#resultado"
    pagina = " ".join(oscar.get(f"/oportunidades/{NRO}").text.split())
    assert "Pueden participar si completan lo que falta" in pagina and elegibilidad.AVISO in pagina
    assert "&lt;script&gt;" in pagina and "<script>alert(1)" not in pagina   # todo escapado
    r = _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['soporte']}/revisar", {"cumple": "2"})
    assert r.status_code == 400 and "Elige «Cumple» o «No cumple»" in r.text
    _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['soporte']}/revisar", {"cumple": "1", "nota": "ok"})
    rid = re.search(r'/asistente/resultados/(\d+)"', oscar.get(f"/oportunidades/{NRO}").text).group(1)
    constancia = " ".join(oscar.get(f"/oportunidades/{NRO}/asistente/resultados/{rid}").text.split())
    assert "Constancia del resultado de elegibilidad" in constancia and elegibilidad.AVISO in constancia
    assert "8 años" in constancia and "Lo tiene · archivo pendiente" in constancia
    assert 'addEventListener("load"' not in constancia                    # «Ver» no abre la ventana de imprimir
    assert 'addEventListener("load"' in oscar.get(f"/oportunidades/{NRO}/asistente/resultados/{rid}?imprimir=1").text
    assert c["ana"].get(f"/oportunidades/{NRO}/asistente/resultados/{rid}").status_code == 403
    assert oscar.get(f"/oportunidades/{NRO}/asistente/resultados/999").status_code == 404


# --- Explicación con IA (OpenAI SIMULADO): explica el resultado de la app, nunca lo cambia ----------------------

class OpenAIExplica:
    """Imita client.responses.create con una explicación fija; anota lo que se le mandó."""

    def __init__(self, explicacion, que_falta=(), falla=False):
        self.llamadas, self.falla = [], falla
        self.datos = {"explicacion": explicacion, "que_falta": list(que_falta)}
        self.responses = SimpleNamespace(create=self._crear)

    def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        if self.falla:
            raise RuntimeError("simulado")
        return SimpleNamespace(status="completed", output_text=json.dumps(self.datos), output=[],
                               model="modelo-simulado", usage=SimpleNamespace(input_tokens=400, output_tokens=80),
                               incomplete_details=None)


def _calcular_con(db_path, settings, simulado):
    with closing(connect(db_path)) as conn:
        cid = ia_explicacion.calcular(conn, settings, NRO, ANA, AHORA, cliente=simulado, dormir=lambda s: None)
        return elegibilidad.constancia(conn, NRO, cid)


def _con_respuestas(lista_fixture):
    db_path, ids, settings = lista_fixture
    _empezar(db_path)
    _responder(db_path, settings, ids["sicop"], valor_si_no="1")
    _responder(db_path, settings, ids["anos"], valor_numero="8", nota="NOTA-INTERNA")
    _responder(db_path, settings, ids["patente"], archivo=PDF)
    _responder(db_path, settings, ids["cierre"], estado="no_se")
    return db_path, ids, settings


@pytest.mark.parametrize("texto, resultado, contradice", [
    ("Sí, pueden participar.", "falta_informacion", True),
    ("Falta información sobre el soporte.", "puede_participar", True),
    ("Sí, pueden participar si completan la patente.", "puede_si_completa", False),
    ("Hermatix cumple el excluyente y falta subir un archivo.", "puede_si_completa", False),
    ("No cumplen un requisito excluyente: la patente.", "no_cumple_excluyente", False)])
def test_contradice_detecta_otro_resultado(texto, resultado, contradice):
    assert ia_explicacion.contradice(texto, resultado) is contradice


def test_la_ia_explica_sin_recibir_archivos_ni_notas(lista):
    db_path, ids, settings = _con_respuestas(lista)
    simulado = OpenAIExplica("Falta responder la fecha de inicio; lo demás cumple.", ["Responder la fecha."])
    c = _calcular_con(db_path, _con_ia(settings), simulado)
    assert c.resultado == "falta_informacion" and c.explicacion_origen == "ia" and c.explicacion_motivo is None
    assert c.explicacion == "Falta responder la fecha de inicio; lo demás cumple.\n- Responder la fecha."
    enviado = simulado.llamadas[0]["input"] + simulado.llamadas[0]["instructions"]
    assert "RESULTADO (calculado por la app; no se cambia): Falta información" in enviado
    assert "permiso.pdf" not in enviado and "TEXTO-UNICO-DEL-ARCHIVO" not in enviado and "NOTA-INTERNA" not in enviado
    assert "documento entregado" in enviado and "Multa" not in enviado and "El resultado NO se cambia" in enviado
    with closing(connect(db_path)) as conn:
        assert {p for (p,) in conn.execute("SELECT proposito FROM ia_usage")} == {"explicacion"}


def test_si_la_ia_contradice_el_resultado_queda_la_explicacion_de_la_app(lista):
    db_path, _, settings = _con_respuestas(lista)
    c = _calcular_con(db_path, _con_ia(settings), OpenAIExplica("Sí, pueden participar sin problema."))
    assert c.resultado == "falta_informacion" and c.explicacion_origen == "app"
    assert "no coincidía con el resultado calculado" in c.explicacion_motivo
    assert c.explicacion.startswith("Falta información. Esto es lo que falta")


@pytest.mark.parametrize("caso", ["ia_apagada", "sin_presupuesto", "fallo"])
def test_sin_ia_la_constancia_lleva_la_explicacion_de_la_app(lista, caso):
    db_path, _, settings = _con_respuestas(lista)
    usar = {"ia_apagada": settings, "sin_presupuesto": _con_ia(settings, IA_MAX_DAILY_COST="0"),
            "fallo": _con_ia(settings)}[caso]
    simulado = OpenAIExplica("x", falla=caso == "fallo")
    c = _calcular_con(db_path, usar, simulado)
    assert c.explicacion_origen == "app" and c.resultado == "falta_informacion"
    assert {"ia_apagada": "apagada", "sin_presupuesto": "presupuesto", "fallo": "OpenAI no respondió"}[caso] in \
        c.explicacion_motivo
    assert (len(simulado.llamadas) > 0) is (caso == "fallo")


@pytest.mark.parametrize("texto, limpio", [
    ("R4: Confirmar la experiencia.", "Confirmar la experiencia."),
    ("R12 · Presentar la oferta en español.", "Presentar la oferta en español."),
    ("Subir la patente (R2).", "Subir la patente."),
    ("Revisar las marcas (R3, R5) del pliego.", "Revisar las marcas del pliego."),
    ("La línea 10 pide 24 meses.", "La línea 10 pide 24 meses.")])
def test_sin_referencias_quita_las_etiquetas_internas(texto, limpio):
    assert ia_explicacion.sin_referencias(texto) == limpio


def test_la_constancia_no_trae_las_etiquetas_r(lista):
    db_path, _, settings = _con_respuestas(lista)
    simulado = OpenAIExplica("Falta responder la fecha (R4).", ["R4: Responder la fecha de inicio.",
                                                                "R5 · Revisar el horario de soporte."])
    c = _calcular_con(db_path, _con_ia(settings), simulado)
    assert c.explicacion_origen == "ia"
    assert c.explicacion == "Falta responder la fecha.\n- Responder la fecha de inicio.\n- Revisar el horario de soporte."
    assert "No uses las etiquetas R1, R2" in simulado.llamadas[0]["instructions"]



@pytest.mark.parametrize("respuestas, esperado", [
    ((True, True), "cumplen"), ((True, False), "fuera"), ((True, None), None), ((False, None), "fuera")])
def test_resultado_rapido_solo_mira_los_excluyentes(respuestas, esperado):
    pares = []
    for valor in respuestas:
        i = _item(excluyente=True)
        pares.append((i, None if valor is None else _resp(i, valor_si_no=valor)))
    otro = _item("texto")
    pares.append((otro, None))                                            # el resto no cuenta
    evals = elegibilidad.evaluar([_paso(i, r) for i, r in pares], CIERRE)
    assert elegibilidad.resultado_rapido(evals) == esperado


def test_resultado_rapido_faltan_si_un_excluyente_queda_pendiente():
    doc = _item("documento", excluyente=True)
    evals = elegibilidad.evaluar([_paso(doc, _resp(doc, "archivo_pendiente"))], CIERRE)
    assert elegibilidad.resultado_rapido(evals) == "faltan"
