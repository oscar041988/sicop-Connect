"""Preguntas del asistente de elegibilidad redactadas con IA (lección 3; DECISION_IA.md §7).

* Una vez por cartel: al empezar el asistente (y con «Redactar con IA las preguntas que faltan» para los requisitos
  agregados o corregidos después). En tandas de TANDA requisitos, para no pasar IA_MAX_OUTPUT_TOKENS.
* Se envía SOLO la lista de verificación (requisito, tipo de respuesta, mínimo, excluyente, cita), con el prompt
  config/prompts/asistente_elegibilidad_<VERSION>.md. NUNCA datos del perfil, respuestas, archivos ni su texto.
* Si la IA está apagada, falla, no responde bien o se acabó el presupuesto del día, no pasa nada grave: el asistente
  usa las preguntas de la app (app/asistente.py) y se muestra el motivo.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app import asistente, historial
from app.ai import cliente as ia_cliente
from app.ai import verificacion
from app.ai.cola import costo_de_hoy
from app.ai.resumen import PROMPTS_DIR, _lista, _objeto, _texto, normalizar
from app.config import Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

VERSION = "v2"                  # v2 (2026-11-12, decisión de Ivania): siempre de usted (con v1 salían vos y tú)
TANDA = 30

ESQUEMA = _objeto(preguntas=_lista(_objeto(
    ref=_texto("El número del requisito: R1, R2…"),
    pregunta=_texto("La pregunta para el encargado, con la cita del pliego"))))
FORMATO = {"type": "json_schema", "name": "preguntas_asistente", "schema": ESQUEMA, "strict": True}


@dataclass(frozen=True)
class Redaccion:
    redactadas: int
    motivo: str | None          # por qué no se redactaron todas (se usan las de la app)


def cargar_prompt() -> str:
    return (PROMPTS_DIR / f"asistente_elegibilidad_{VERSION}.md").read_text(encoding="utf-8")


def texto_para_ia(pasos: list[asistente.Paso]) -> str:
    lineas = ["LISTA DE VERIFICACIÓN (del cartel):"]
    for n, p in enumerate(pasos, start=1):
        i = p.item
        respuesta = verificacion.EVIDENCIAS[i.tipo_evidencia] + (f" ({i.unidad})" if i.unidad else "")
        lineas.append(f"R{n} · excluyente: {'sí' if i.excluyente else 'no'} · respuesta: {respuesta}"
                      f" · mínimo: {i.minimo} · cita: {'; '.join(i.citas) or 'sin cita'} · requisito: «{i.requisito}»")
    return "\n".join(lineas)


def _sin_presupuesto(conn: sqlite3.Connection, settings: Settings) -> str | None:
    if costo_de_hoy(conn, datetime.now(HORA_CR).date()) >= settings.ia_max_daily_cost:
        return (f"ya se usó el presupuesto de IA de hoy ({settings.ia_max_daily_cost} USD, IA_MAX_DAILY_COST):"
                " se usan las preguntas de la app")
    return None


def redactar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, ahora: datetime,
             cliente=None, dormir=None, viejas: bool = False) -> Redaccion:
    """Pide a la IA las preguntas que faltan (las que hoy arma la app). Con viejas, también las redactadas con otra
    versión del prompt (2026-11-12: las de v1 trataban de vos o de tú). Nunca lanza por la IA: devuelve el motivo."""
    actual = asistente.sesion(conn, nro_sicop)
    if actual is None:
        raise asistente.AsistenteInvalido("El asistente de este cartel no se ha empezado.")
    otra_version = {i for (i,) in conn.execute(
        "SELECT item_id FROM eligibility_questions WHERE session_id = ? AND prompt_version <> ?",
        (actual.id, VERSION))} if viejas else set()
    faltan = [p for p in asistente.recorrido(conn, nro_sicop, ahora.astimezone(HORA_CR).date())
              if p.origen == "app" or p.item.id in otra_version]
    if not faltan:
        return Redaccion(0, None)
    if not settings.ia_activa:
        return Redaccion(0, "la IA está apagada (AI_MODE=none): se usan las preguntas de la app")
    extra = {"dormir": dormir} if dormir is not None else {}
    redactadas, motivo = 0, None
    for inicio in range(0, len(faltan), TANDA):
        tanda = faltan[inicio:inicio + TANDA]
        if (motivo := _sin_presupuesto(conn, settings)) is not None:
            break
        try:
            r = ia_cliente.pedir(conn, settings, cargar_prompt(), texto_para_ia(tanda), "asistente", nro_sicop,
                                 cliente=cliente, formato=FORMATO, **extra)
        except (ia_cliente.IaApagada, ia_cliente.IaConfiguracion) as exc:
            motivo = str(exc)
            break
        except ia_cliente.IaFallo as exc:
            motivo = f"OpenAI no respondió bien ({exc.motivo}): se usan las preguntas de la app"
            break
        try:
            datos = normalizar(json.loads(r.texto), ESQUEMA) if r.resultado == "ok" else None
        except ValueError:
            datos = None
        if datos is None:
            motivo = f"la respuesta de la IA no sirvió ({r.motivo or 'no es JSON válido'}): se usan las de la app"
            break
        por_ref = {f"R{n}": p for n, p in enumerate(tanda, start=1)}
        preguntas = {}
        for x in datos["preguntas"]:
            paso, texto = por_ref.get(str(x["ref"]).strip().upper()), " ".join(str(x["pregunta"]).split())
            if paso is not None and texto and texto != "no encontrado":
                preguntas[paso.item.id] = (paso.item.requisito, texto)
        asistente.guardar_preguntas(conn, actual.id, preguntas, r.uso_id, VERSION, ahora)
        redactadas += len(preguntas)
    if redactadas:
        with transaccion(conn):
            historial.registrar(conn, quien, "redactar_preguntas_asistente", f"{nro_sicop}: {redactadas} preguntas")
    if motivo is None and redactadas < len(faltan):
        motivo = f"la IA no redactó {len(faltan) - redactadas} preguntas: para esas se usan las de la app"
    return Redaccion(redactadas, motivo)
