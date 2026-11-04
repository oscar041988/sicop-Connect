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

Las reglas no tocan la base ni la IA (reciben los pasos y devuelven la evaluación); abajo, lo que se guarda
(migración 0033): la decisión de una persona sobre un «revisar» y cada resultado como constancia.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app import asistente, historial, perfil
from app.ai import verificacion
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

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


RAPIDOS = {
    "fuera": "Queda fuera: no cumple un requisito excluyente",
    "faltan": "Faltan excluyentes por confirmar",
    "cumplen": "Los excluyentes cumplen: vale la pena seguir",
}


def resultado_rapido(evaluaciones: list[Evaluacion]) -> str | None:
    """La revisión rápida (solo los excluyentes, sin guardar nada). Un excluyente que no cumple ya basta para
    «fuera»; si no, None mientras falte responder alguno."""
    excluyentes = [e for e in evaluaciones if e.item.excluyente]
    if any(e.estado == "no_cumple" for e in excluyentes):
        return "fuera"
    if not excluyentes or any(e.respuesta is None for e in excluyentes):
        return None
    return "cumplen" if all(e.estado == "cumple" for e in excluyentes) else "faltan"


def pendientes(evaluaciones: list[Evaluacion]) -> list[Evaluacion]:
    """Lo que impide «Sí, pueden participar»: excluyentes primero, como en el asistente."""
    return [e for e in evaluaciones if e.estado != "cumple"]


def explicacion_de_la_app(resultado: str, evaluaciones: list[Evaluacion]) -> str:
    """La explicación que arma la app cuando no la redacta la IA: el resultado y lo que falta, en orden."""
    faltan = pendientes(evaluaciones)
    if not faltan:
        return "Todos los requisitos que se preguntaron cumplen según las respuestas dadas."
    lineas = [f"{RESULTADOS[resultado]}. Esto es lo que falta o hay que revisar:"]
    for e in faltan:
        marca = " (excluyente)" if e.item.excluyente else ""
        lineas.append(f"- {e.estado_texto}{marca}: {e.item.requisito} — {e.motivo}")
    return "\n".join(lineas)


# --- Base: revisiones de una persona y constancias (migración 0033) -------------------------------------------

class ResultadoInvalido(ValueError):
    """Algo no se acepta; el mensaje es el que verá la persona."""


@dataclass(frozen=True)
class Constancia:
    id: int
    nro_sicop: str
    resultado: str
    cierre: str | None
    lista_generacion_id: int | None
    lista_huella: str
    detalle: list[dict]
    explicacion: str
    explicacion_origen: str
    explicacion_motivo: str | None
    calculado_por: str
    creado_en: str

    @property
    def resultado_texto(self) -> str:
        return RESULTADOS[self.resultado]


def _momento(ahora: datetime) -> str:
    return ahora.astimezone(HORA_CR).isoformat(timespec="seconds")


def cierre_de(conn: sqlite3.Connection, nro_sicop: str) -> date | None:
    """La fecha de cierre de recepción del cartel (la que muestra el panel), o None si no se sabe."""
    fila = conn.execute("SELECT fecha_cierre_recepcion FROM tenders WHERE nro_sicop = ?", (nro_sicop,)).fetchone()
    try:
        return date.fromisoformat(fila[0][:10]) if fila and fila[0] else None
    except ValueError:
        return None


def revisiones(conn: sqlite3.Connection, session_id: int) -> dict[int, Revision]:
    """La última decisión de una persona por requisito."""
    filas = conn.execute(
        "SELECT item_id, answer_id, cumple, nota, revisado_por_nombre, creado_en FROM eligibility_item_reviews"
        " WHERE id IN (SELECT MAX(id) FROM eligibility_item_reviews WHERE session_id = ? GROUP BY item_id)",
        (session_id,)).fetchall()
    return {f[0]: Revision(f[1], bool(f[2]), f[3], f[4], f[5]) for f in filas}


def evaluacion_actual(conn: sqlite3.Connection, nro_sicop: str, dia: date) -> tuple[list[Evaluacion], str]:
    """(evaluación por requisito, resultado global) con las respuestas y revisiones de hoy, sin guardar nada."""
    actual = asistente.sesion(conn, nro_sicop)
    if actual is None:
        raise ResultadoInvalido("El asistente de este cartel no se ha empezado.")
    evaluaciones = evaluar(asistente.recorrido(conn, nro_sicop, dia), cierre_de(conn, nro_sicop),
                           revisiones(conn, actual.id))
    return evaluaciones, resultado_global(evaluaciones)


def revisar(conn: sqlite3.Connection, nro_sicop: str, item_id: int, cumple: bool, nota: str, quien: Quien,
            ahora: datetime) -> int:
    """Una persona decide un requisito en «revisar». Queda atada a la respuesta que miró."""
    evaluaciones, _ = evaluacion_actual(conn, nro_sicop, ahora.astimezone(HORA_CR).date())
    e = next((x for x in evaluaciones if x.item.id == item_id), None)
    if e is None:
        raise ResultadoInvalido("Ese requisito no está en el asistente de este cartel.")
    if e.automatico != "revisar":
        raise ResultadoInvalido("Este requisito lo compara la app: no necesita la decisión de una persona.")
    nota = " ".join(nota.split())[:asistente.LARGO_TEXTO] or None
    sesion = asistente.sesion(conn, nro_sicop)
    with transaccion(conn):
        revision_id = conn.execute(
            "INSERT INTO eligibility_item_reviews (session_id, item_id, answer_id, cumple, nota, revisado_por,"
            " revisado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sesion.id, item_id, e.respuesta.id, int(cumple), nota, quien.user_id, quien.nombre,
             _momento(ahora))).lastrowid
        historial.registrar(conn, quien, "revisar_resultado", f"{nro_sicop}: requisito #{item_id}")
    return revision_id


def huella_lista(evaluaciones: list[Evaluacion]) -> str:
    """Huella de la versión de la lista que se evaluó: si alguien corrige un requisito, cambia."""
    partes = [(e.item.id, e.item.requisito, e.item.tipo_evidencia, e.item.minimo, e.item.minimo_numero,
               e.item.excluyente) for e in evaluaciones]
    return hashlib.sha256(json.dumps(partes, ensure_ascii=False).encode("utf-8")).hexdigest()


def detalle(evaluaciones: list[Evaluacion]) -> list[dict]:
    """Lo que guarda la constancia por requisito: el requisito, su estado, su respuesta y quién la dio."""
    filas = []
    for e in evaluaciones:
        r = e.respuesta
        filas.append({
            "item_id": e.item.id, "requisito": e.item.requisito, "excluyente": e.item.excluyente,
            "evidencia": e.item.evidencia_texto, "minimo": e.item.minimo, "citas": e.item.citas,
            "estado": e.estado, "automatico": e.automatico, "motivo": e.motivo,
            "respuesta": r.resumen if r else None, "respuesta_id": r.id if r else None,
            "nota": r.nota if r else None, "respondido_por": r.respondido_por if r else None,
            "respondido_en": r.creado_en if r else None,
            "revision": ({"cumple": e.revision.cumple, "nota": e.revision.nota, "por": e.revision.por,
                          "en": e.revision.en} if e.revision else None)})
    return filas


def guardar(conn: sqlite3.Connection, nro_sicop: str, evaluaciones: list[Evaluacion], resultado: str,
            explicacion: str, origen: str, motivo: str | None, uso_id: int | None, quien: Quien,
            ahora: datetime) -> int:
    """Guarda el resultado como constancia (nunca se borra ni se modifica)."""
    sesion = asistente.sesion(conn, nro_sicop)
    generacion = verificacion.ultima_generacion(conn, nro_sicop)
    cierre = cierre_de(conn, nro_sicop)
    with transaccion(conn):
        constancia_id = conn.execute(
            "INSERT INTO eligibility_results (session_id, nro_sicop, resultado, cierre, lista_generacion_id,"
            " lista_huella, detalle, explicacion, explicacion_origen, explicacion_motivo, ia_usage_id, calculado_por,"
            " calculado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sesion.id, nro_sicop, resultado, cierre.isoformat() if cierre else None,
             generacion.id if generacion else None, huella_lista(evaluaciones),
             json.dumps(detalle(evaluaciones), ensure_ascii=False), explicacion, origen, motivo, uso_id,
             quien.user_id, quien.nombre, _momento(ahora))).lastrowid
        historial.registrar(conn, quien, "calcular_resultado", f"{nro_sicop}: {resultado}")
    return constancia_id


def calcular(conn: sqlite3.Connection, nro_sicop: str, quien: Quien, ahora: datetime) -> int:
    """Calcula el resultado de hoy y lo guarda con la explicación de la app (la de la IA llega en el paso 4)."""
    evaluaciones, resultado = evaluacion_actual(conn, nro_sicop, ahora.astimezone(HORA_CR).date())
    return guardar(conn, nro_sicop, evaluaciones, resultado, explicacion_de_la_app(resultado, evaluaciones), "app",
                   None, None, quien, ahora)


_CONSTANCIA = ("SELECT id, nro_sicop, resultado, cierre, lista_generacion_id, lista_huella, detalle, explicacion,"
               " explicacion_origen, explicacion_motivo, calculado_por_nombre, creado_en FROM eligibility_results")


def _constancia(fila) -> Constancia:
    return Constancia(*fila[:6], json.loads(fila[6]), *fila[7:])


def constancias(conn: sqlite3.Connection, nro_sicop: str) -> list[Constancia]:
    """Los resultados calculados del cartel, el más reciente primero."""
    return [_constancia(f) for f in conn.execute(f"{_CONSTANCIA} WHERE nro_sicop = ? ORDER BY id DESC",
                                                 (nro_sicop,))]


def constancia(conn: sqlite3.Connection, nro_sicop: str, constancia_id: int) -> Constancia | None:
    fila = conn.execute(f"{_CONSTANCIA} WHERE id = ? AND nro_sicop = ?", (constancia_id, nro_sicop)).fetchone()
    return _constancia(fila) if fila else None
