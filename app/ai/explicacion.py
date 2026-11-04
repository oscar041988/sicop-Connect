"""Explicación del resultado de elegibilidad con IA (asistente, lección 4; DECISION_IA.md §7).

* La app ya calculó el resultado (app/elegibilidad.py): la IA solo lo explica en palabras sencillas y lista lo que
  falta. NO puede cambiarlo: la app pone siempre el titular y el aviso fijo, y si el texto de la IA nombra otro
  resultado, se descarta y se usa la explicación de la app.
* Se envían el resultado, y por requisito su texto, si es excluyente, su estado, el motivo y la respuesta escrita
  (número, sí/no, fecha o texto). NUNCA archivos, su texto ni sus nombres, ni notas, ni datos del perfil que no
  sean la respuesta confirmada.
* Si la IA está apagada, falla, no responde bien o se acabó el presupuesto del día, la constancia lleva la
  explicación de la app y el motivo.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app import elegibilidad
from app.ai import cliente as ia_cliente
from app.ai import verificacion
from app.ai.cola import costo_de_hoy
from app.ai.resumen import PROMPTS_DIR, _lista, _objeto, _texto, normalizar
from app.config import Settings
from app.historial import Quien
from app.importers.comun import HORA_CR

VERSION = "v2"          # v2 (2026-11-04): sin las etiquetas internas R1, R2… (constancia #1)

ESQUEMA = _objeto(
    explicacion=_texto("Dos a cuatro oraciones que explican el resultado ya calculado, sin cambiarlo"),
    que_falta=_lista(_texto("Una cosa concreta que falta o hay que revisar, con su requisito")))
FORMATO = {"type": "json_schema", "name": "explicacion_resultado", "schema": ESQUEMA, "strict": True}

# Frases que nombran cada resultado (normalizadas: sin tildes, mayúsculas ni signos): si el texto de la IA nombra
# uno que no es el calculado, la explicación se descarta (la IA no decide el resultado).
_FRASES = {"puede_participar": "si pueden participar", "puede_si_completa": "pueden participar si complet",
           "no_cumple_excluyente": "no cumplen un requisito excluyente", "falta_informacion": "falta informacion"}


@dataclass(frozen=True)
class Explicacion:
    texto: str
    origen: str                 # «ia» o «app»
    motivo: str | None          # por qué no la redactó la IA
    uso_id: int | None


def cargar_prompt() -> str:
    return (PROMPTS_DIR / f"explicacion_elegibilidad_{VERSION}.md").read_text(encoding="utf-8")


def _respuesta_escrita(e: elegibilidad.Evaluacion) -> str:
    """La respuesta como la escribió la persona; de un documento solo si está, nunca su nombre ni su texto."""
    r = e.respuesta
    if r is None:
        return "sin responder"
    if r.estado != "respondido":
        return r.estado_texto
    if r.tipo_evidencia == "documento":
        return "documento entregado" + (f", vence {r.vence_el}" if r.vence_el else "")
    if r.valor_numero is not None:
        return f"{r.valor_numero} {r.unidad or ''}".strip()
    if r.valor_si_no is not None:
        return "Sí" if r.valor_si_no else "No"
    return r.valor_fecha or r.valor_texto or "—"


def texto_para_ia(resultado: str, evaluaciones: list[elegibilidad.Evaluacion]) -> str:
    lineas = [f"RESULTADO (calculado por la app; no se cambia): {elegibilidad.RESULTADOS[resultado]}",
              "REQUISITOS:"]
    for n, e in enumerate(evaluaciones, start=1):
        lineas.append(f"R{n} · excluyente: {'sí' if e.item.excluyente else 'no'} · estado: {e.estado_texto} · "
                      f"motivo: {e.motivo} · respuesta: {_respuesta_escrita(e)} · requisito: «{e.item.requisito}»")
    return "\n".join(lineas)


# «R4: …», «R4 · …», «R4 - …» al inicio y «(R2)» en cualquier parte: las etiquetas internas de texto_para_ia.
_REFERENCIA = re.compile(r"^\s*R\d+\s*[:·.\-–—]\s*|\s*\(R\d+(?:\s*,\s*R\d+)*\)")


def sin_referencias(texto: str) -> str:
    """Quita las etiquetas internas R1, R2… que la IA a veces copia de la lista: la persona no las ve."""
    return " ".join(_REFERENCIA.sub("", texto).split())


def contradice(texto: str, resultado: str) -> bool:
    """True si el texto nombra el titular de otro resultado («Sí, pueden participar» cuando falta información…)."""
    normal = f" {verificacion.normalizar_texto(texto)} "
    nombrados = {clave for clave, frase in _FRASES.items() if f" {frase}" in normal}
    # «Sí, pueden participar si completan…» nombra «si completan», no «Sí, pueden participar» sin condiciones.
    if "puede_participar" in nombrados and normal.count(" si pueden participar si complet") == normal.count(
            " si pueden participar"):
        nombrados.discard("puede_participar")
    return bool(nombrados - {resultado})


def explicar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, resultado: str,
             evaluaciones: list[elegibilidad.Evaluacion], cliente=None, dormir=None) -> Explicacion:
    """La explicación de la IA, o la de la app con el motivo. Nunca lanza por la IA."""
    de_la_app = elegibilidad.explicacion_de_la_app(resultado, evaluaciones)
    if settings.ai_mode != "openai":
        return Explicacion(de_la_app, "app", "la IA está apagada (AI_MODE=none)", None)
    if costo_de_hoy(conn, datetime.now(HORA_CR).date()) >= settings.ia_max_daily_cost:
        return Explicacion(de_la_app, "app", f"ya se usó el presupuesto de IA de hoy ({settings.ia_max_daily_cost}"
                                             " USD, IA_MAX_DAILY_COST)", None)
    extra = {"dormir": dormir} if dormir is not None else {}
    try:
        r = ia_cliente.pedir(conn, settings, cargar_prompt(), texto_para_ia(resultado, evaluaciones), "explicacion",
                             nro_sicop, cliente=cliente, formato=FORMATO, **extra)
    except (ia_cliente.IaApagada, ia_cliente.IaConfiguracion) as exc:
        return Explicacion(de_la_app, "app", str(exc), None)
    except ia_cliente.IaFallo as exc:
        return Explicacion(de_la_app, "app", f"OpenAI no respondió bien ({exc.motivo})", exc.uso_id)
    try:
        datos = normalizar(json.loads(r.texto), ESQUEMA) if r.resultado == "ok" else None
    except ValueError:
        datos = None
    explicacion = sin_referencias(str((datos or {}).get("explicacion", "")))
    if not explicacion:
        return Explicacion(de_la_app, "app", f"la respuesta de la IA no sirvió ({r.motivo or 'no es JSON válido'})",
                           r.uso_id)
    faltan = [x for x in (sin_referencias(str(y)) for y in datos.get("que_falta", [])) if x]
    texto = "\n".join([explicacion, *(f"- {x}" for x in faltan)])
    if contradice(texto, resultado):
        return Explicacion(de_la_app, "app", "la explicación de la IA no coincidía con el resultado calculado: se"
                                             " usó la de la app", r.uso_id)
    return Explicacion(texto, "ia", None, r.uso_id)


def calcular(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, ahora: datetime,
             cliente=None, dormir=None) -> int:
    """Calcula el resultado (la app), pide la explicación (la IA, si se puede) y guarda la constancia."""
    evaluaciones, resultado = elegibilidad.evaluacion_actual(conn, nro_sicop, ahora.astimezone(HORA_CR).date())
    e = explicar(conn, settings, nro_sicop, resultado, evaluaciones, cliente=cliente, dormir=dormir)
    return elegibilidad.guardar(conn, nro_sicop, evaluaciones, resultado, e.texto, e.origen, e.motivo, e.uso_id,
                                quien, ahora)
