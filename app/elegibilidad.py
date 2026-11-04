"""Resultado de elegibilidad (asistente, lección 4): ¿Hermatix puede participar en el cartel?

* La app compara, la IA solo explica (docs/DECISION_IA.md §7): cada requisito del recorrido del asistente
  (app/asistente.py) recibe un estado — cumple · no_cumple · falta · revisar — con reglas exactas: sí/no, número
  contra su mínimo, documento y su vencimiento contra el cierre del cartel. Lo que no se puede comparar
  (textos, fechas, cantidades de documentos, mínimos sin dirección clara) queda en «revisar»: lo decide una
  persona, y su decisión vale mientras no cambie la respuesta.
* Resultado global, en este orden (un excluyente no cumplido manda): no_cumple_excluyente → falta_informacion →
  puede_si_completa → puede_participar.
* Es una orientación, no una garantía: el aviso fijo (AVISO) va siempre con el resultado. La decisión de participar
  es del encargado.

Este módulo no toca la base ni la IA: recibe los pasos y devuelve la evaluación.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app import asistente, perfil
from app.ai import verificacion

ESTADOS = {"cumple": "Cumple", "no_cumple": "No cumple", "falta": "Falta", "revisar": "Revisar"}
RESULTADOS = {
    "puede_participar": "Sí, pueden participar",
    "puede_si_completa": "Pueden participar si completan lo que falta",
    "no_cumple_excluyente": "No cumplen un requisito excluyente",
    "falta_informacion": "Falta información",
}
AVISO = ("Esta evaluación se basa en las respuestas dadas. La admisión de la oferta depende de la institución. "
         "Revisa antes de ofertar.")

# Palabras del mínimo (normalizadas: sin tildes ni mayúsculas) que dicen hacia dónde se compara el número.
AL_MENOS = ("al menos", "minimo", "no menor", "por lo menos", "o mas")
COMO_MAXIMO = ("maximo", "no mayor", "a mas tardar", "hasta", "no superior", "o menos")


@dataclass(frozen=True)
class Revision:
    """La decisión de una persona sobre un requisito en «revisar». Vale solo para la respuesta que miró."""
    respuesta_id: int
    cumple: bool
    nota: str | None
    por: str
    en: str


@dataclass(frozen=True)
class Evaluacion:
    item: verificacion.Item
    respuesta: asistente.Respuesta | None
    estado: str
    motivo: str
    automatico: str                  # el estado que dio la regla, antes de la revisión de una persona
    revision: Revision | None = None

    @property
    def estado_texto(self) -> str:
        return ESTADOS[self.estado]


def direccion_minimo(minimo: str | None) -> str | None:
    """«>=» si el mínimo dice «al menos…», «<=» si dice «máximo…», None si no lo dice o dice las dos cosas."""
    texto = f" {verificacion.normalizar_texto(minimo or '')} "
    al_menos = any(f" {p} " in texto for p in AL_MENOS)
    maximo = any(f" {p} " in texto for p in COMO_MAXIMO)
    if al_menos == maximo:
        return None
    return ">=" if al_menos else "<="


def _numero(texto: str | None) -> Decimal | None:
    try:
        return Decimal(texto) if texto is not None else None
    except InvalidOperation:
        return None


def _con_unidad(valor: Decimal, unidad: str | None) -> str:
    return f"{valor.normalize():f} {unidad or ''}".strip()


def _automatico(item: verificacion.Item, r: asistente.Respuesta, cierre: date | None) -> tuple[str, str]:
    """(estado, motivo) según la regla del tipo de evidencia; solo para respuestas con un dato («respondido»)."""
    t = item.tipo_evidencia
    if t == "si_no":
        return ("cumple", "Respondió «Sí».") if r.valor_si_no else ("no_cumple", "Respondió «No».")
    if t == "numero":
        valor, minimo = _numero(r.valor_numero), _numero(item.minimo_numero)
        if valor is None or minimo is None:
            return "revisar", "El pliego no da un número para comparar: revísalo."
        direccion = direccion_minimo(item.minimo)
        if direccion is None:
            return "revisar", f"No se sabe si «{item.minimo}» es un mínimo o un máximo: revísalo."
        cumple = valor >= minimo if direccion == ">=" else valor <= minimo
        signo = {(">=", True): "≥", (">=", False): "<", ("<=", True): "≤", ("<=", False): ">"}[(direccion, cumple)]
        unidad = item.unidad or r.unidad
        return ("cumple" if cumple else "no_cumple",
                f"{_con_unidad(valor, unidad)} {signo} {_con_unidad(minimo, unidad)} («{item.minimo}»).")
    if t == "documento":
        if r.vence_el and cierre and date.fromisoformat(r.vence_el) < cierre:
            return "no_cumple", f"Vence el {perfil.dia(r.vence_el)}, antes del cierre ({cierre:%d/%m/%Y})."
        if item.minimo_numero:
            return "revisar", f"El pliego pide una cantidad («{item.minimo}»): revisa los documentos."
        vence = f", vence el {perfil.dia(r.vence_el)}" if r.vence_el else ""
        return "cumple", f"Documento presente{vence}. Su contenido lo revisa una persona."
    return "revisar", "Una persona compara la respuesta con lo que pide el pliego."     # texto y fecha


def evaluar_item(paso: asistente.Paso, cierre: date | None, revision: Revision | None = None) -> Evaluacion:
    item, r = paso.item, paso.respuesta
    if r is None:
        return Evaluacion(item, r, "falta", "Sin responder.", "falta")
    if r.estado == "no_se":
        return Evaluacion(item, r, "falta", "«Todavía no lo sé».", "falta")
    if r.estado == "archivo_pendiente":
        return Evaluacion(item, r, "falta", "Hermatix lo tiene, pero el archivo está pendiente.", "falta")
    if r.estado == "no_lo_tiene":
        return Evaluacion(item, r, "no_cumple", "Hermatix no lo tiene.", "no_cumple")
    estado, motivo = _automatico(item, r, cierre)
    if estado == "revisar" and revision is not None and revision.respuesta_id == r.id:
        decidido = "cumple" if revision.cumple else "no_cumple"
        nota = f": {revision.nota}" if revision.nota else "."
        return Evaluacion(item, r, decidido, f"Revisado por {revision.por}{nota}", estado, revision)
    return Evaluacion(item, r, estado, motivo, estado)


def evaluar(pasos: list[asistente.Paso], cierre: date | None,
            revisiones: dict[int, Revision] | None = None) -> list[Evaluacion]:
    """Un estado por requisito del recorrido. revisiones: {item_id: la última decisión de una persona}."""
    revisiones = revisiones or {}
    return [evaluar_item(p, cierre, revisiones.get(p.item.id)) for p in pasos]


def resultado_global(evaluaciones: list[Evaluacion]) -> str:
    if any(e.item.excluyente and e.estado == "no_cumple" for e in evaluaciones):
        return "no_cumple_excluyente"
    sin_respuesta = any(e.respuesta is None or e.respuesta.estado == "no_se" for e in evaluaciones)
    if not evaluaciones or sin_respuesta or any(e.item.excluyente and e.estado == "revisar" for e in evaluaciones):
        return "falta_informacion"
    if any(e.estado != "cumple" for e in evaluaciones):
        return "puede_si_completa"
    return "puede_participar"


def pendientes(evaluaciones: list[Evaluacion]) -> list[Evaluacion]:
    """Lo que impide «Sí, pueden participar»: excluyentes primero, como en el asistente."""
    return [e for e in evaluaciones if e.estado != "cumple"]
