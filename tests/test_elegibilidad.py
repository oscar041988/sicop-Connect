"""Resultado de elegibilidad (asistente, lección 4): la app compara cada respuesta con su mínimo.

Requisitos y respuestas INVENTADOS: primero en memoria (sin base ni IA), después con la base SINTÉTICA de
tests/test_asistente.py. Nunca se llama a OpenAI.
"""

import shutil
import sqlite3
from contextlib import closing
from datetime import date
from itertools import count

import pytest

from app import asistente, elegibilidad
from app.ai import verificacion
from app.database import MIGRATIONS_DIR, apply_migrations, connect
from tests.test_asistente import AHORA, ANA, LUIS, NRO, PDF, _empezar, _responder, lista  # noqa: F401 (fixture)
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
        asistente.empezar(conn, NRO, ANA, AHORA)
        conn.execute("INSERT INTO eligibility_answers (session_id, item_id, requisito, pregunta, tipo_evidencia,"
                     " estado, fuente, valor_si_no, respondido_por_nombre, creado_en) VALUES (1, ?, 'r', 'p',"
                     " 'si_no', 'respondido', 'usuario', 1, 'Ana', 't')", (item,))
        conn.commit()
    assert apply_migrations(base) == ["0033_resultado_elegibilidad.sql"]
    with closing(connect(base)) as conn:
        assert conn.execute("SELECT count(*) FROM eligibility_answers").fetchone() == (1,)
        assert elegibilidad.calcular(conn, NRO, ANA, AHORA) == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
