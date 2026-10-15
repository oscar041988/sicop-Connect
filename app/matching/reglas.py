"""Reglas de familias comerciales (config/hermatix_rules.yaml) y búsqueda de términos en un texto.

* Normalizar solo sirve para comparar: minúsculas, sin tildes, NBSP y signos como espacios.
  La evidencia se devuelve con el texto ORIGINAL, tal como viene en SICOP.
* Un término coincide como palabra completa, admitiendo plural al final («edificio» → «edificios»),
  pero nunca dentro de otra palabra («lora» no coincide con «exploracion»).
* Si dos coincidencias se solapan, gana la más larga: en «monitoreo gps» no se cuenta además «gps».
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import PROJECT_ROOT

REGLAS_PATH = PROJECT_ROOT / "config" / "hermatix_rules.yaml"
TIPOS = ("senales_alta", "senales_media", "contexto", "exclusiones")


class ReglasError(Exception):
    """El archivo de reglas no tiene la forma esperada."""


def normalizar_con_mapa(texto: str) -> tuple[str, list[int]]:
    """Texto normalizado y, para cada carácter, su posición en el texto original."""
    salida: list[str] = []
    mapa: list[int] = []
    for i, caracter in enumerate(texto):
        for c in unicodedata.normalize("NFKD", caracter):
            if unicodedata.combining(c):
                continue  # la tilde separada de su letra: «á» → «a» + «´»
            c = c.lower()
            if not c.isalnum():
                c = " "
            if c == " " and (not salida or salida[-1] == " "):
                continue  # un solo espacio seguido, nunca al inicio
            salida.append(c)
            mapa.append(i)
    if salida and salida[-1] == " ":
        salida.pop()
        mapa.pop()
    return "".join(salida), mapa


def normalizar(texto: str) -> str:
    return normalizar_con_mapa(texto)[0]


@dataclass(frozen=True)
class Termino:
    tipo: str      # senales_alta | senales_media | contexto | exclusiones
    termino: str   # tal como está en el YAML
    patron: re.Pattern[str]


@dataclass(frozen=True)
class Familia:
    nombre: str
    producto: str
    terminos: tuple[Termino, ...]


@dataclass(frozen=True)
class Reglas:
    version: str   # huella del archivo: cambia si cambia cualquier término
    familias: tuple[Familia, ...]


@dataclass(frozen=True)
class Coincidencia:
    tipo: str
    termino: str
    frase: str     # texto original que coincidió
    inicio: int
    fin: int


def _patron(termino: str) -> re.Pattern[str]:
    norm = normalizar(termino)
    if not norm:
        raise ReglasError(f"Término vacío después de normalizar: {termino!r}")
    return re.compile(rf"(?<![a-z0-9]){re.escape(norm)}(?:s|es)?(?![a-z0-9])")


def cargar_reglas(path: Path = REGLAS_PATH) -> Reglas:
    contenido = path.read_bytes()
    # Saltos de línea normalizados: Windows (CRLF) y Linux (LF) dan la misma versión.
    version = hashlib.sha256(contenido.replace(b"\r\n", b"\n")).hexdigest()[:12]
    datos = yaml.safe_load(contenido.decode("utf-8"))
    if not isinstance(datos, dict) or not isinstance(datos.get("familias"), dict):
        raise ReglasError("El archivo debe empezar con «familias:»")
    familias = []
    for nombre, regla in datos["familias"].items():
        if not isinstance(regla, dict) or not regla.get("producto"):
            raise ReglasError(f"La familia {nombre} no tiene producto")
        desconocidas = set(regla) - {"producto", *TIPOS}
        if desconocidas:
            # Una clave mal escrita («Exlcusiones») dejaría la familia sin exclusiones sin avisar.
            raise ReglasError(f"La familia {nombre} tiene claves desconocidas: {', '.join(sorted(desconocidas))}")
        terminos = []
        for tipo in TIPOS:
            lista = regla.get(tipo) or []
            if not isinstance(lista, list) or not all(isinstance(t, str) for t in lista):
                raise ReglasError(f"{nombre}.{tipo} debe ser una lista de textos")
            terminos.extend(Termino(tipo, t, _patron(t)) for t in lista)
        familias.append(Familia(nombre, str(regla["producto"]), tuple(terminos)))
    return Reglas(version, tuple(familias))


def buscar(familia: Familia, texto: str) -> list[Coincidencia]:
    """Términos de la familia que aparecen en el texto, sin coincidencias contenidas en otra más larga."""
    norm, mapa = normalizar_con_mapa(texto)
    encontradas = []
    for t in familia.terminos:
        for m in t.patron.finditer(norm):
            frase = texto[mapa[m.start()]:mapa[m.end() - 1] + 1]
            encontradas.append(Coincidencia(t.tipo, t.termino, frase, m.start(), m.end()))
    return [c for c in encontradas
            if not any(o is not c and o.inicio <= c.inicio and c.fin <= o.fin and (o.fin - o.inicio) > (c.fin - c.inicio)
                       for o in encontradas)]
