"""Resultado de elegibilidad (asistente, lección 4): la app compara cada respuesta con su mínimo.

Requisitos y respuestas INVENTADOS, armados en memoria (sin base ni IA).
"""

from datetime import date
from itertools import count

import pytest

from app import asistente, elegibilidad
from app.ai import verificacion

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
