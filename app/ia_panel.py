"""La IA en uso, cambiada desde el panel (Administración → IA; pedido de Oscar el 2026-11-18, DECISION_IA.md §11).

Un administrador elige el proveedor (OpenAI, Anthropic o apagada), el modelo, la clave y los precios. Antes de
guardar, la app hace una llamada corta de prueba (como `ia probar`) con lo nuevo: si falla, no cambia nada.
Lo guardado va a ia.env, junto a la base (config.ruta_ia_panel), y gana sobre .env y app.env:
* nunca a la base ni a los respaldos, ni a Git (data/ está fuera de Git);
* la clave nunca se muestra completa: solo sus últimos 4 caracteres; el historial dice «clave nueva», nunca la clave.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app import historial
from app.ai import cliente as ia_cliente
from app.config import CLAVES_IA_PANEL, Settings, leer_ia_panel, ruta_ia_panel
from app.database import transaccion
from app.historial import Quien

PROVEEDORES = {"anthropic": "Anthropic (Claude)", "openai": "OpenAI", "none": "Apagada"}
# La clave no se inventa: la crea el proveedor en su consola, ligada a la cuenta y al saldo de Hermatix (Ivania, 18/11).
CONSOLAS = {"anthropic": "https://console.anthropic.com/settings/keys", "openai": "https://platform.openai.com/api-keys"}
# Lo que escribe un administrador: nombres de modelo como claude-opus-5-5 o gpt-6.1-terra.
MODELO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
CLAVE = re.compile(r"^[A-Za-z0-9_\-.]{20,300}$")
PRUEBA_INSTRUCCIONES = "Eres una prueba de conexión de SICOP CONNECT. Responde exactamente con la palabra OK."
PRUEBA_TEXTO = "Responde solo: OK"


class CambioInvalido(ValueError):
    """El cambio no se guardó; el mensaje es el que ve el administrador."""


@dataclass(frozen=True)
class Estado:
    modo: str
    proveedor: str
    modelo: str
    clave_final: str          # últimos 4 caracteres de la clave del proveedor en uso; vacío si no hay
    claves: dict[str, str]    # proveedor → últimos 4 de su clave (para saber si ya hay una guardada)
    modelos: dict[str, str]   # proveedor → su modelo
    precio_entrada: str
    precio_salida: str
    desde_panel: bool         # True si lo que manda está en ia.env


def _final(clave: str) -> str:
    return clave[-4:] if len(clave) >= 8 else ""


def estado(settings: Settings) -> Estado:
    modo = settings.ai_mode
    claves = {"openai": _final(settings.openai_api_key), "anthropic": _final(settings.anthropic_api_key)}
    return Estado(modo=modo, proveedor=PROVEEDORES[modo], modelo=settings.ia_modelo, clave_final=claves.get(modo, ""),
                  claves=claves, modelos={"openai": settings.openai_model, "anthropic": settings.anthropic_model},
                  precio_entrada=settings.get("IA_PRECIO_ENTRADA_USD").strip(),
                  precio_salida=settings.get("IA_PRECIO_SALIDA_USD").strip(),
                  desde_panel=bool(leer_ia_panel(settings.get("DATABASE_PATH"))))


def _precio(valor: str, nombre: str) -> str:
    valor = valor.strip().replace(",", ".")
    if not valor:
        return ""
    try:
        numero = Decimal(valor)
    except InvalidOperation:
        raise CambioInvalido(f"El precio de {nombre} debe ser un número, por ejemplo 5 o 2.50.") from None
    if not numero.is_finite() or numero < 0 or numero > 1000:
        raise CambioInvalido(f"El precio de {nombre} debe estar entre 0 y 1000 USD por millón de tokens.")
    return valor


def _escribir(ruta: Path, valores: dict[str, str]) -> None:
    """Escribe ia.env de una vez (archivo temporal + reemplazo): nunca queda a medias. Permisos 600 donde se pueda."""
    lineas = ["# Escrito por el panel de SICOP CONNECT (Administración → IA). Gana sobre .env y app.env.",
              "# Tiene la clave de la IA: nunca a Git, a un chat ni a un respaldo compartido.",
              *(f"{k}={valores[k]}" for k in CLAVES_IA_PANEL if k in valores)]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    os.replace(temporal, ruta)


def cambiar(conn: sqlite3.Connection, settings: Settings, *, modo: str, modelo: str, clave: str,
            precio_entrada: str, precio_salida: str, quien: Quien, cliente=None) -> str:
    """Prueba lo nuevo y, si responde, lo guarda en ia.env. Devuelve el mensaje para el administrador.

    Lanza CambioInvalido si un dato no sirve o si la prueba falla (en ese caso ia.env no cambia).
    cliente solo se cambia en las pruebas (una IA SIMULADA)."""
    modo, modelo, clave = modo.strip().lower(), modelo.strip(), clave.strip()
    if modo not in PROVEEDORES:
        raise CambioInvalido("Elija OpenAI, Anthropic o apagada.")
    nuevos = dict(leer_ia_panel(settings.get("DATABASE_PATH")))
    nuevos["AI_MODE"] = modo
    nuevos["IA_PRECIO_ENTRADA_USD"] = _precio(precio_entrada, "entrada")
    nuevos["IA_PRECIO_SALIDA_USD"] = _precio(precio_salida, "salida")
    partes = [PROVEEDORES[modo]]
    if modo != "none":
        prefijo = modo.upper()
        if not MODELO.match(modelo):
            raise CambioInvalido("Escriba el nombre del modelo tal como sale en la documentación del proveedor,"
                                 " por ejemplo claude-opus-5-5.")
        nuevos[f"{prefijo}_MODEL"] = modelo
        partes.append(modelo)
        if clave:
            if not CLAVE.match(clave):
                raise CambioInvalido("La clave no parece válida: cópiela completa, sin espacios.")
            nuevos[f"{prefijo}_API_KEY"] = clave
            partes.append("clave nueva")
        elif not settings.get(f"{prefijo}_API_KEY").strip():
            raise CambioInvalido(f"No hay clave de {PROVEEDORES[modo]} guardada: escríbala.")
        prueba = Settings(raw={**settings.raw, **nuevos}, env_file_loaded=settings.env_file_loaded)
        try:
            r = ia_cliente.pedir(conn, prueba, PRUEBA_INSTRUCCIONES, PRUEBA_TEXTO, "prueba", cliente=cliente)
        except ia_cliente.IaConfiguracion as exc:
            raise CambioInvalido(f"No se guardó nada: {exc}") from None
        except ia_cliente.IaFallo as exc:
            raise CambioInvalido(f"No se guardó nada: la prueba con {PROVEEDORES[modo]} falló ({exc.motivo};"
                                 f" anotado en el uso de la IA, #{exc.uso_id}). Revise el modelo y la clave.") from None
        if r.resultado != "ok":
            raise CambioInvalido(f"No se guardó nada: la prueba con {PROVEEDORES[modo]} salió «{r.resultado}»"
                                 f"{f' ({r.motivo})' if r.motivo else ''}.")
    _escribir(ruta_ia_panel(settings.get("DATABASE_PATH")), nuevos)
    with transaccion(conn):
        historial.registrar(conn, quien, "cambiar_ia", " · ".join(partes))
    if modo == "none":
        return "Listo: la IA quedó apagada. La app no llama a ninguna IA."
    return f"Listo: la app usa {PROVEEDORES[modo]} con el modelo {modelo}. La prueba respondió bien."
