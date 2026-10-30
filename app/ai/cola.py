"""Cola automática de resúmenes con IA (Reporte con IA, lección 5): python -m app.cli ia cola.

La tarea programada de Windows la corre después del enriquecimiento de las 10:00 (deploy/windows/sicop-enriquecimiento.ps1).
Decisiones de Ivania (2026-10-30), provisionales hasta que Oscar decida (DECISION_IA.md §5):

* Cola: carteles Alta o Media en la evaluación vigente, ya enriquecidos (tienen ficha de SICOP), con plazo abierto
  y sin un resumen ok o revisar de su expediente actual (misma huella) con la versión vigente del prompt. Orden:
  Alta → Media y, dentro de cada uno, el que cierra antes. Un cartel que cambió (ficha o documentos nuevos) tiene
  otra huella y vuelve a la cola; su resumen anterior no se borra.
* Un cartel ya intentado hoy no se repite hoy (así un fallo no se paga dos veces el mismo día).
* Presupuesto diario: IA_MAX_SUMMARIES_PER_DAY resúmenes nuevos (10) y IA_MAX_DAILY_COST USD (1.00) de costo
  estimado de toda la IA del día. Antes de cada llamada se suma lo gastado hoy y lo máximo que podría costar ese
  resumen (su expediente + IA_MAX_OUTPUT_TOKENS): si no cabe, se detiene y lo demás queda para mañana.
* Un fallo de un cartel no detiene la cola. Sí la detienen la falta de saldo o una clave rechazada (401/403):
  seguir solo gastaría intentos.
* Con AI_MODE=none no hace nada. Una sola cola a la vez (bloqueo del sistema operativo).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Callable

from app.ai import cliente as ia_cliente
from app.ai import resumen as ia_resumen
from app.ai.expediente import armar_expediente
from app.bloqueo import bloqueo
from app.config import Settings
from app.database import connect
from app.importers.comun import HORA_CR
from app.panel import version_vigente

PRIORIDAD = {"alta": 0, "media": 1}
ETIQUETAS = {"alta": "Alta", "media": "Media"}
_DETIENEN = (*ia_cliente.SIN_SALDO, " 401", " 403")   # en el motivo de un fallido: «RateLimitError 429 · insufficient_quota»


@dataclass(frozen=True)
class EnCola:
    nro_sicop: str
    encaje: str
    cierre: str
    descripcion: str
    tokens_estimados: int


@dataclass
class Corrida:
    estado: str                          # apagada · sin_cola · ok · con_fallos · tope · detenida
    en_cola: int = 0
    resultados: list[ia_resumen.Resultado] = field(default_factory=list)
    pendientes: int = 0                  # quedaron para otro día
    motivo: str | None = None            # por qué se detuvo o por qué no siguió
    costo_hoy: Decimal = Decimal(0)


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def _fecha(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        fecha = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=HORA_CR)


def intentados_hoy(conn: sqlite3.Connection, hoy: date) -> set[str]:
    return {n for (n,) in conn.execute("SELECT DISTINCT nro_sicop FROM ia_summaries WHERE substr(creado_en, 1, 10) = ?",
                                       (hoy.isoformat(),))}


def costo_de_hoy(conn: sqlite3.Connection, hoy: date) -> Decimal:
    """Costo estimado de TODA la IA del día (resúmenes y pruebas), desde ia_usage."""
    return sum((Decimal(c) for (c,) in conn.execute(
        "SELECT costo_estimado FROM ia_usage WHERE substr(creado_en, 1, 10) = ? AND costo_estimado IS NOT NULL",
        (hoy.isoformat(),))), Decimal(0))


def cola(conn: sqlite3.Connection, settings: Settings, ahora: datetime) -> list[EnCola]:
    """Los carteles que hoy tocaría resumir, Alta → Media y por cierre (sin aplicar el presupuesto)."""
    version = version_vigente(conn)
    if version is None:
        return []
    prompt = settings.ia_prompt_version
    hoy = intentados_hoy(conn, ahora.date())
    filas = conn.execute(
        "SELECT t.nro_sicop, t.descripcion, t.fecha_cierre_recepcion, d.cierre_recepcion, a.rango"
        " FROM tenders t"
        " JOIN (SELECT nro_sicop, min(CASE encaje WHEN 'alta' THEN 0 ELSE 1 END) AS rango"
        "       FROM opportunity_assessments WHERE rules_version = ? AND encaje IN ('alta', 'media')"
        "       GROUP BY nro_sicop) a ON a.nro_sicop = t.nro_sicop"
        " JOIN (SELECT nro_sicop, max(id) AS id FROM tender_details GROUP BY nro_sicop) u ON u.nro_sicop = t.nro_sicop"
        " JOIN tender_details d ON d.id = u.id", (version,)).fetchall()
    encaje_de = {rango: encaje for encaje, rango in PRIORIDAD.items()}
    lista = []
    for nro, descripcion, cierre_datos, cierre_ficha, rango in filas:
        cierre_iso = cierre_ficha or cierre_datos   # la ficha es más reciente que los datos abiertos
        cierre = _fecha(cierre_iso)
        if nro in hoy or cierre is None or cierre <= ahora:
            continue
        exp = armar_expediente(conn, nro, settings.ia_max_input_tokens)
        if exp is None or conn.execute(
                "SELECT 1 FROM ia_summaries WHERE nro_sicop = ? AND huella = ? AND prompt_version = ?"
                " AND estado IN ('ok', 'revisar')", (nro, exp.huella, prompt)).fetchone():
            continue
        lista.append(EnCola(nro, encaje_de[rango], cierre_iso, descripcion or "", exp.tokens_estimados))
    return sorted(lista, key=lambda e: (PRIORIDAD[e.encaje], _fecha(e.cierre)))


def correr(settings: Settings, *, cliente=None, reloj: Callable[[], datetime] = _ahora,
           avisar: Callable[[str], None] = lambda _: None, **opciones) -> Corrida:
    """Una corrida de la cola. Lanza app.bloqueo.CicloOcupado si ya hay otra, IaConfiguracion o ValueError si la
    configuración no sirve. cliente y opciones (dormir) solo se cambian en las pruebas (OpenAI SIMULADO)."""
    if settings.ai_mode != "openai":
        return Corrida("apagada", motivo="AI_MODE=none")
    if settings.ia_precio_entrada_usd is None or settings.ia_precio_salida_usd is None:
        raise ia_cliente.IaConfiguracion("Faltan IA_PRECIO_ENTRADA_USD e IA_PRECIO_SALIDA_USD: sin precios no se puede"
                                         " respetar IA_MAX_DAILY_COST.")
    maximo, tope = settings.ia_max_summaries_per_day, settings.ia_max_daily_cost
    inicio = reloj()
    with bloqueo(settings.database_path.parent / "ia-cola.lock", f"{inicio:%Y-%m-%d %H:%M:%S} · ia cola"), \
            closing(connect(settings.database_path)) as conn:
        lista = cola(conn, settings, inicio)
        corrida = Corrida("sin_cola" if not lista else "ok", en_cola=len(lista))
        hechos_hoy = len(intentados_hoy(conn, inicio.date()))
        corrida.costo_hoy = costo_de_hoy(conn, inicio.date())
        avisar(f"En cola: {len(lista)} · resúmenes hoy: {hechos_hoy} de {maximo} · costo de la IA hoy:"
               f" {ia_cliente.texto_decimal(corrida.costo_hoy)} de {ia_cliente.texto_decimal(tope)} USD.")
        for i, item in enumerate(lista):
            posible = ia_cliente.costo_estimado(settings, item.tokens_estimados, settings.ia_max_output_tokens)
            if hechos_hoy >= maximo:
                corrida.estado, corrida.motivo = "tope", f"se llegó a {maximo} resúmenes hoy (IA_MAX_SUMMARIES_PER_DAY)"
            elif corrida.costo_hoy + posible > tope:
                corrida.estado, corrida.motivo = "tope", (
                    f"el siguiente podría costar hasta {ia_cliente.texto_decimal(posible)} USD y no cabe en el tope"
                    f" de {ia_cliente.texto_decimal(tope)} USD de hoy (IA_MAX_DAILY_COST)")
            if corrida.estado == "tope":
                corrida.pendientes = len(lista) - i
                avisar(f"Se detiene: {corrida.motivo}. Quedan {corrida.pendientes} para mañana.")
                break
            avisar(f"[{i + 1}/{len(lista)}] {item.nro_sicop} · {ETIQUETAS[item.encaje]} · aprox."
                   f" {item.tokens_estimados} tokens")
            try:
                res = ia_resumen.resumir(conn, settings, item.nro_sicop, cliente=cliente, **opciones)
            except ia_resumen.ResumenError as exc:   # el cartel ya no está: se sigue con el siguiente
                avisar(f"  Se omite: {exc}")
                continue
            hechos_hoy += 1
            corrida.costo_hoy = costo_de_hoy(conn, inicio.date())
            corrida.resultados.append(res)
            costo = f"{ia_cliente.texto_decimal(res.costo)} USD" if res.costo is not None else "sin costo"
            avisar(f"  {ia_resumen.ESTADOS[res.estado]}{f' ({res.motivo})' if res.motivo else ''} · {costo}")
            if res.estado == "fallido":
                corrida.estado = "con_fallos"
                if any(d in (res.motivo or "") for d in _DETIENEN):
                    corrida.estado, corrida.motivo = "detenida", f"OpenAI rechazó la clave o no hay saldo ({res.motivo})"
                    corrida.pendientes = len(lista) - i - 1
                    avisar(f"Se detiene: {corrida.motivo}. Quedan {corrida.pendientes} para otro día.")
                    break
    return corrida
