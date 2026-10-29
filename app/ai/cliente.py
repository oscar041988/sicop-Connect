"""Cliente de la API de OpenAI (Reporte con IA, lección 2): la ÚNICA parte de la app que habla con OpenAI.

* Con AI_MODE=none no llama a nada y ni siquiera carga el SDK: la app funciona igual que sin IA.
* La clave (OPENAI_API_KEY) y el modelo (OPENAI_MODEL) vienen de la configuración; nunca van en el código.
* Tiempo de espera IA_TIMEOUT_SECONDS. El SDK no reintenta solo (max_retries=0): esta capa reintenta como máximo 2
  veces y solo ante errores temporales (límite de uso 429, error del servidor 5xx, tiempo agotado, conexión).
  Nunca ante clave inválida (401), permiso (403), petición mala (400), modelo no encontrado (404) ni falta de
  saldo (429 con código insufficient_quota o credit_balance_exhausted): repetir no lo arregla y solo gastaría o
  demoraría.
* Cada llamada deja una fila en ia_usage (migración 0023), salga bien o mal, SIN el texto enviado, la respuesta ni
  la clave. El motivo de un fallo es el tipo de error y su código HTTP: el texto del error puede traer parte de la
  clave, por eso no se guarda ni se muestra.
* store=False: se le pide a OpenAI que no guarde la respuesta en la cuenta.
* Lección 3: con «formato» (un JSON Schema) se pide salida estructurada estricta. Si el modelo se niega a hacer la
  tarea (rechazo), la llamada queda como fallo «rechazo del modelo»; el texto del rechazo no se guarda.

Las firmas usadas (OpenAI(api_key, timeout, max_retries), responses.create(model, instructions, input,
max_output_tokens, store), Response.status / usage / output_text, errores con status_code y code) se leyeron del
SDK instalado, openai 3.40.0.
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
    """AI_MODE=none: no se llama a OpenAI."""


class IaConfiguracion(ValueError):
    """Falta la clave o el modelo: no se llama."""


class IaFallo(RuntimeError):
    """OpenAI no respondió bien. Ya quedó anotado en ia_usage."""

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


def crear_cliente(settings: Settings):
    """El cliente real del SDK. Solo se llama con AI_MODE=openai (el SDK se carga recién aquí)."""
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


def _es_temporal(exc: Exception) -> bool:
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
    """True si alguna parte de la respuesta es un rechazo del modelo (tipo «refusal» del SDK)."""
    for item in getattr(r, "output", None) or []:
        for parte in getattr(item, "content", None) or []:
            if getattr(parte, "type", None) == "refusal":
                return True
    return False


def pedir(conn: sqlite3.Connection, settings: Settings, instrucciones: str, texto: str, proposito: str,
          nro_sicop: str | None = None, cliente=None, dormir: Callable[[float], None] = time.sleep,
          reloj: Callable[[], float] = time.monotonic, formato: dict | None = None) -> Respuesta:
    """Manda instrucciones + texto al modelo y devuelve su respuesta. Lanza IaApagada, IaConfiguracion o IaFallo.

    cliente, dormir y reloj solo se cambian en las pruebas (un OpenAI SIMULADO, sin esperas reales)."""
    if settings.ai_mode != "openai":
        raise IaApagada("La IA está apagada (AI_MODE=none): no se llamó a OpenAI.")
    modelo = settings.openai_model
    if not settings.openai_api_key or not modelo:
        faltan = [n for n, v in (("OPENAI_API_KEY", settings.openai_api_key), ("OPENAI_MODEL", modelo)) if not v]
        raise IaConfiguracion(f"Falta {' y '.join(faltan)} en la configuración: no se llamó a OpenAI.")
    cliente = cliente if cliente is not None else crear_cliente(settings)
    inicio, intentos = reloj(), 0
    while True:
        intentos += 1
        try:
            extra = {"text": {"format": formato}} if formato is not None else {}
            r = cliente.responses.create(model=modelo, instructions=instrucciones, input=texto,
                                         max_output_tokens=settings.ia_max_output_tokens, store=False, **extra)
            break
        except Exception as exc:  # noqa: BLE001 — cualquier error queda anotado antes de salir
            temporal = _es_temporal(exc)
            if temporal and intentos <= MAX_REINTENTOS:
                dormir(PAUSAS_S[intentos - 1])
                continue
            motivo = motivo_de(exc)
            uso = _registrar(conn, proposito, nro_sicop, modelo, None, None, None, reloj() - inicio, intentos,
                             "fallo", motivo)
            # «from None»: el error original (que puede traer parte de la clave) no se encadena ni se imprime.
            raise IaFallo(motivo, intentos, uso) from None
    duracion = reloj() - inicio
    usage = getattr(r, "usage", None)
    entrada = getattr(usage, "input_tokens", None)
    salida = getattr(usage, "output_tokens", None)
    costo = costo_estimado(settings, entrada, salida)
    estado = getattr(r, "status", None)
    if estado == "failed":
        uso = _registrar(conn, proposito, nro_sicop, modelo, entrada, salida, costo, duracion, intentos, "fallo",
                         "respuesta con estado failed")
        raise IaFallo("respuesta con estado failed", intentos, uso)
    if _rechazo(r):
        uso = _registrar(conn, proposito, nro_sicop, modelo, entrada, salida, costo, duracion, intentos, "fallo",
                         "rechazo del modelo")
        raise IaFallo("rechazo del modelo", intentos, uso)
    resultado, motivo = "ok", None
    if estado == "incomplete":
        razon = getattr(getattr(r, "incomplete_details", None), "reason", None)
        resultado = "incompleta"
        motivo = f"incompleta · {razon}" if isinstance(razon, str) and CODIGO.match(razon) else "incompleta"
    uso = _registrar(conn, proposito, nro_sicop, modelo, entrada, salida, costo, duracion, intentos, resultado, motivo)
    return Respuesta(r.output_text or "", getattr(r, "model", None) or modelo, entrada, salida, costo,
                     round(duracion, 2), intentos, resultado, motivo, uso)
