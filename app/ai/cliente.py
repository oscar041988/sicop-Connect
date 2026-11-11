"""Cliente de la IA (Reporte con IA, lección 2): la ÚNICA parte de la app que habla con OpenAI o con Anthropic.

* AI_MODE elige: openai, anthropic (DECISION_IA.md §8, aprobado por Oscar el 2026-11-05) o none. Con none no llama
  a nada y ni siquiera carga un SDK: la app funciona igual que sin IA. Solo se carga el SDK del modo elegido.
* La clave (OPENAI_API_KEY / ANTHROPIC_API_KEY) y el modelo (OPENAI_MODEL / ANTHROPIC_MODEL) vienen de la
  configuración; nunca van en el código. IA_PRECIO_ENTRADA_USD / IA_PRECIO_SALIDA_USD son los del modelo activo.
* Tiempo de espera IA_TIMEOUT_SECONDS. El SDK no reintenta solo (max_retries=0): esta capa reintenta como máximo 2
  veces y solo ante errores temporales (límite de uso 429, error del servidor 5xx, tiempo agotado, conexión).
  Nunca ante clave inválida (401), permiso (403), petición mala (400), modelo no encontrado (404) ni falta de
  saldo (429 con código insufficient_quota o credit_balance_exhausted): repetir no lo arregla y solo gastaría o
  demoraría.
* Cada llamada deja una fila en ia_usage (migración 0023), salga bien o mal, SIN el texto enviado, la respuesta ni
  la clave. El motivo de un fallo es el tipo de error y su código HTTP: el texto del error puede traer parte de la
  clave, por eso no se guarda ni se muestra.
* OpenAI: store=False (se le pide que no guarde la respuesta en la cuenta).
* Anthropic: las instrucciones van en «system» y el texto como mensaje del usuario; ANTHROPIC_EFFORT (opcional)
  regula cuánto razona el modelo, y ese razonamiento cuenta dentro de IA_MAX_OUTPUT_TOKENS. Nunca se reintenta
  ante el tope de gasto de la cuenta (EnforcedSpendLimitReachedError) ni ante falta de saldo (400).
* Lección 3: con «formato» (un JSON Schema) se pide salida estructurada estricta. Si el modelo se niega a hacer la
  tarea (rechazo), la llamada queda como fallo «rechazo del modelo»; el texto del rechazo no se guarda.

Las firmas usadas (OpenAI(api_key, timeout, max_retries), responses.create(model, instructions, input,
max_output_tokens, store), Response.status / usage / output_text, errores con status_code y code) se leyeron del
SDK instalado, openai 3.40.0. Las de Anthropic (Anthropic(api_key, timeout, max_retries), messages.create(model,
max_tokens, system, messages, output_config), Message.stop_reason / content / usage y la jerarquía de errores) se
leyeron del SDK instalado, anthropic 2.8.0.
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from app.config import Settings
from app.database import transaccion
from app.dinero import texto_decimal
from app.importers.comun import HORA_CR

MAX_REINTENTOS = 2
PAUSAS_S = (2, 6)               # espera antes del 1.er y del 2.º reintento
MILLON = Decimal(1_000_000)
CODIGO = re.compile(r"^[a-z_]{1,40}$")   # códigos de OpenAI como «insufficient_quota»; cualquier otra cosa no se copia


class IaApagada(RuntimeError):
    """AI_MODE=none: no se llama a ninguna IA."""


class IaConfiguracion(ValueError):
    """Falta la clave o el modelo: no se llama."""


class IaFallo(RuntimeError):
    """La IA no respondió bien. Ya quedó anotado en ia_usage."""

    def __init__(self, motivo: str, intentos: int, uso_id: int):
        super().__init__(motivo)
        self.motivo, self.intentos, self.uso_id = motivo, intentos, uso_id


@dataclass
class Respuesta:
    texto: str
    modelo: str
    tokens_entrada: int | None
    tokens_salida: int | None
    costo: Decimal | None        # USD; None = sin precio configurado
    duracion_s: float
    intentos: int
    resultado: str               # ok · incompleta
    motivo: str | None
    uso_id: int


@dataclass
class _Salida:
    """Lo que la app necesita de una respuesta, igual para los dos proveedores."""
    texto: str
    modelo: str | None
    entrada: int | None
    salida: int | None
    fallo: str | None            # motivo si la respuesta no sirve (rechazo del modelo, estado failed)
    incompleta: str | None       # razón si se cortó (tope de tokens); None = completa


def crear_cliente(settings: Settings):
    """El cliente real del SDK del modo elegido (el SDK se carga recién aquí). El SDK no reintenta solo."""
    if settings.ai_mode == "anthropic":
        from anthropic import Anthropic
        return Anthropic(api_key=settings.anthropic_api_key, timeout=settings.ia_timeout_seconds, max_retries=0)
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key, timeout=settings.ia_timeout_seconds, max_retries=0)


def costo_estimado(settings: Settings, entrada: int | None, salida: int | None) -> Decimal | None:
    """Tokens × precio por millón, en USD. Sin los dos precios configurados no se calcula (no se inventa)."""
    p_entrada, p_salida = settings.ia_precio_entrada_usd, settings.ia_precio_salida_usd
    if p_entrada is None or p_salida is None or entrada is None or salida is None:
        return None
    return ((Decimal(entrada) * p_entrada + Decimal(salida) * p_salida) / MILLON).quantize(Decimal("0.000001"))


# Un 429 con uno de estos códigos es falta de saldo, no un límite de uso pasajero. credit_balance_exhausted es el
# que devolvió OpenAI en la primera llamada real (29/10, cuenta sin saldo).
SIN_SALDO = ("insufficient_quota", "credit_balance_exhausted")


def _es_temporal(exc: Exception, modo: str) -> bool:
    if modo == "anthropic":
        import anthropic
        if isinstance(exc, anthropic.EnforcedSpendLimitReachedError):   # tope de gasto de la cuenta: no se repite
            return False
        # RateLimitError 429; InternalServerError incluye 529 (sobrecarga), 503 y 504; APIConnectionError incluye
        # el tiempo agotado. La falta de saldo es un 400: no se reintenta.
        return isinstance(exc, (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError))
    import openai
    if isinstance(exc, openai.RateLimitError):
        return getattr(exc, "code", None) not in SIN_SALDO
    return isinstance(exc, (openai.InternalServerError, openai.APIConnectionError))   # incluye APITimeoutError


def motivo_de(exc: Exception) -> str:
    """«AuthenticationError 401» o «RateLimitError 429 · insufficient_quota»: nunca el texto del error."""
    partes = [type(exc).__name__]
    estado = getattr(exc, "status_code", None)
    if isinstance(estado, int):
        partes.append(str(estado))
    codigo = getattr(exc, "code", None)
    motivo = " ".join(partes)
    return f"{motivo} · {codigo}" if isinstance(codigo, str) and CODIGO.match(codigo) else motivo


def _registrar(conn: sqlite3.Connection, proposito: str, nro_sicop: str | None, modelo: str, entrada, salida,
               costo: Decimal | None, duracion: float, intentos: int, resultado: str, motivo: str | None) -> int:
    with transaccion(conn):
        return conn.execute(
            "INSERT INTO ia_usage (creado_en, proposito, nro_sicop, modelo, tokens_entrada, tokens_salida,"
            " costo_estimado, moneda, duracion_s, intentos, resultado, motivo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
            " ?, ?)",
            (datetime.now(HORA_CR).isoformat(timespec="seconds"), proposito, nro_sicop, modelo, entrada, salida,
             texto_decimal(costo) if costo is not None else None, "USD" if costo is not None else None,
             round(duracion, 2), intentos, resultado, motivo)).lastrowid


def _rechazo(r) -> bool:
    """True si alguna parte de la respuesta de OpenAI es un rechazo del modelo (tipo «refusal» del SDK)."""
    for item in getattr(r, "output", None) or []:
        for parte in getattr(item, "content", None) or []:
            if getattr(parte, "type", None) == "refusal":
                return True
    return False


def _llamar_openai(cliente, settings: Settings, modelo: str, instrucciones: str, texto: str,
                   formato: dict | None) -> _Salida:
    extra = {"text": {"format": formato}} if formato is not None else {}
    r = cliente.responses.create(model=modelo, instructions=instrucciones, input=texto,
                                 max_output_tokens=settings.ia_max_output_tokens, store=False, **extra)
    usage = getattr(r, "usage", None)
    estado = getattr(r, "status", None)
    fallo = "respuesta con estado failed" if estado == "failed" else "rechazo del modelo" if _rechazo(r) else None
    incompleta = None
    if estado == "incomplete":
        incompleta = getattr(getattr(r, "incomplete_details", None), "reason", None) or ""
    return _Salida(r.output_text or "", getattr(r, "model", None), getattr(usage, "input_tokens", None),
                   getattr(usage, "output_tokens", None), fallo, incompleta)


# Razones de corte de Anthropic que dejan la respuesta incompleta (stop_reason del SDK).
CORTES_ANTHROPIC = ("max_tokens", "model_context_window_exceeded")


def _llamar_anthropic(cliente, settings: Settings, modelo: str, instrucciones: str, texto: str,
                      formato: dict | None) -> _Salida:
    config: dict = {}
    if formato is not None:
        # El mismo JSON Schema que con OpenAI; Anthropic no usa «name» ni «strict» (el formato ya es estricto).
        config["format"] = {"type": "json_schema", "schema": formato["schema"]}
    if settings.anthropic_effort:
        config["effort"] = settings.anthropic_effort
    extra = {"output_config": config} if config else {}
    r = cliente.messages.create(model=modelo, max_tokens=settings.ia_max_output_tokens, system=instrucciones,
                                messages=[{"role": "user", "content": texto}], **extra)
    usage = getattr(r, "usage", None)
    entrada = getattr(usage, "input_tokens", None)
    if entrada is not None:   # los tokens leídos o escritos en caché también son de entrada
        entrada += sum(getattr(usage, c, None) or 0 for c in ("cache_creation_input_tokens", "cache_read_input_tokens"))
    razon = getattr(r, "stop_reason", None)
    bloques = getattr(r, "content", None) or []
    texto_r = "".join(b.text for b in bloques if getattr(b, "type", None) == "text")
    return _Salida(texto_r, getattr(r, "model", None), entrada, getattr(usage, "output_tokens", None),
                   "rechazo del modelo" if razon == "refusal" else None,
                   razon if razon in CORTES_ANTHROPIC else None)


def pedir(conn: sqlite3.Connection, settings: Settings, instrucciones: str, texto: str, proposito: str,
          nro_sicop: str | None = None, cliente=None, dormir: Callable[[float], None] = time.sleep,
          reloj: Callable[[], float] = time.monotonic, formato: dict | None = None) -> Respuesta:
    """Manda instrucciones + texto al modelo y devuelve su respuesta. Lanza IaApagada, IaConfiguracion o IaFallo.

    cliente, dormir y reloj solo se cambian en las pruebas (una IA SIMULADA, sin esperas reales)."""
    modo = settings.ai_mode
    if modo == "none":
        raise IaApagada("La IA está apagada (AI_MODE=none): no se llamó a ninguna IA.")
    proveedor = "Anthropic" if modo == "anthropic" else "OpenAI"
    clave = settings.anthropic_api_key if modo == "anthropic" else settings.openai_api_key
    modelo = settings.ia_modelo
    if not clave or not modelo:
        faltan = [n for n, v in ((f"{modo.upper()}_API_KEY", clave), (f"{modo.upper()}_MODEL", modelo)) if not v]
        raise IaConfiguracion(f"Falta {' y '.join(faltan)} en la configuración: no se llamó a {proveedor}.")
    llamar = _llamar_anthropic if modo == "anthropic" else _llamar_openai
    cliente = cliente if cliente is not None else crear_cliente(settings)
    inicio, intentos = reloj(), 0
    while True:
        intentos += 1
        try:
            r = llamar(cliente, settings, modelo, instrucciones, texto, formato)
            break
        except Exception as exc:  # noqa: BLE001 — cualquier error queda anotado antes de salir
            temporal = _es_temporal(exc, modo)
            if temporal and intentos <= MAX_REINTENTOS:
                dormir(PAUSAS_S[intentos - 1])
                continue
            motivo = motivo_de(exc)
            uso = _registrar(conn, proposito, nro_sicop, modelo, None, None, None, reloj() - inicio, intentos,
                             "fallo", motivo)
            # «from None»: el error original (que puede traer parte de la clave) no se encadena ni se imprime.
            raise IaFallo(motivo, intentos, uso) from None
    duracion = reloj() - inicio
    entrada, salida = r.entrada, r.salida
    costo = costo_estimado(settings, entrada, salida)
    if r.fallo:
        uso = _registrar(conn, proposito, nro_sicop, modelo, entrada, salida, costo, duracion, intentos, "fallo",
                         r.fallo)
        raise IaFallo(r.fallo, intentos, uso)
    resultado, motivo = "ok", None
    if r.incompleta is not None:
        razon = r.incompleta
        resultado = "incompleta"
        motivo = f"incompleta · {razon}" if isinstance(razon, str) and CODIGO.match(razon) else "incompleta"
    uso = _registrar(conn, proposito, nro_sicop, modelo, entrada, salida, costo, duracion, intentos, resultado, motivo)
    return Respuesta(r.texto, r.modelo or modelo, entrada, salida, costo, round(duracion, 2), intentos, resultado,
                     motivo, uso)
