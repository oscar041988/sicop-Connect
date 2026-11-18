"""La ayuda dentro de la app (lección 3): índice, páginas de misión, buscador, glosario y botón «?».

Los textos se leen de docs/ayuda/ en cada petición (cambiar la ayuda es editar el Markdown, sin tocar código).
El convertidor de Markdown es propio y entiende solo lo que usan las misiones: TODO el texto se escapa primero y
después se agregan unas pocas etiquetas (títulos, listas, negrita, enlaces a otras misiones y capturas).
"""

from __future__ import annotations

import fnmatch
import functools
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from markupsafe import Markup, escape

from app.ayuda import CAPTURAS_DIR, MISIONES_DIR, PROJECT_ROOT
from app.ayuda.misiones import Marcador, leer_mision

INDICE = MISIONES_DIR.parent / "MISIONES.md"
GLOSARIO = MISIONES_DIR.parent / "GLOSARIO.md"
CONFIG = PROJECT_ROOT / "config" / "ayuda.yaml"
NOMBRE = re.compile(r"^\d{2}-[a-z0-9-]+$")

_FILA_INDICE = re.compile(r"^\|.*`(\d{2}-[a-z0-9-]+)\.md`")
_TITULO = re.compile(r"^(#{1,3})\s+(.*)$")
_NUMERO = re.compile(r"^(\d+)\.\s+(.*)$")
_VINETA = re.compile(r"^-\s+(.*)$")
_SUBVINETA = re.compile(r"^\s+-\s+(.*)$")
_NEGRITA = re.compile(r"\*\*(.+?)\*\*")
_ENLACE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


@dataclass(frozen=True)
class Mision:
    nombre: str          # «08-revision»
    titulo: str          # «¿Cómo marco si un cartel interesa o no?»
    para_que: str        # la frase de «Para qué sirve»
    bloque: str          # «Página del cartel, de arriba abajo»
    solo_admin: bool


@dataclass
class Bloque:
    titulo: str
    misiones: list[Mision] = field(default_factory=list)


@dataclass(frozen=True)
class Termino:
    palabra: str
    que: str
    ejemplo: str


# --- Configuración e índice ----------------------------------------------------------------------------------------

def _config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def _limpiar(texto: str) -> str:
    """Quita la marca de Markdown de un texto corto: «**Para qué sirve:** x» → «Para qué sirve: x»."""
    return _ENLACE.sub(r"\1", _NEGRITA.sub(r"\1", texto)).strip()


def _cabecera(archivo: Path) -> tuple[str, str]:
    titulo, para_que = archivo.stem, ""
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if linea.startswith("# "):
            titulo = linea[2:].strip()
        elif linea.startswith("**Para qué sirve:**"):
            para_que = _limpiar(linea.split(":**", 1)[1])
            break
    return titulo, para_que


def todas() -> list[Mision]:
    """Las misiones de MISIONES.md, en su orden y con su bloque («## A. Panel de carteles» → «Panel de carteles»)."""
    solo_admin = set(_config().get("solo_admin") or [])
    misiones, bloque = [], ""
    for linea in INDICE.read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            bloque = re.sub(r"\s*\(.*\)$", "", re.sub(r"^[A-Z]\.\s+", "", linea[3:].strip()))
        elif (fila := _FILA_INDICE.match(linea)) and (archivo := MISIONES_DIR / f"{fila.group(1)}.md").is_file():
            misiones.append(Mision(fila.group(1), *_cabecera(archivo), bloque, fila.group(1) in solo_admin))
    return misiones


def visibles(es_admin: bool) -> list[Mision]:
    return [m for m in todas() if es_admin or not m.solo_admin]


def indice(es_admin: bool) -> list[Bloque]:
    bloques: list[Bloque] = []
    for m in visibles(es_admin):
        if not bloques or bloques[-1].titulo != m.bloque:
            bloques.append(Bloque(m.bloque))
        bloques[-1].misiones.append(m)
    return bloques


def buscar_mision(nombre: str) -> Mision | None:
    if not NOMBRE.fullmatch(nombre):
        return None
    return next((m for m in todas() if m.nombre == nombre), None)


def mision_de_ruta(ruta: str) -> str | None:
    """La misión del botón «?» para esta dirección (config/ayuda.yaml), o None."""
    for regla in _config().get("pantallas") or []:
        if fnmatch.fnmatchcase(ruta, regla["ruta"]):
            return regla["mision"]
    return None


def ayuda_para(ruta: str) -> str:
    mision = mision_de_ruta(ruta)
    return f"/ayuda/{mision}" if mision else "/ayuda"


# --- Convertidor de Markdown ---------------------------------------------------------------------------------------

def _en_linea(texto: str) -> str:
    """Una línea de texto ya escapada, con negritas y enlaces a otras misiones."""
    html = _NEGRITA.sub(r"<strong>\1</strong>", str(escape(texto)))

    def enlace(m: re.Match) -> str:
        destino = m.group(2)
        if (nombre := re.fullmatch(r"(\d{2}-[a-z0-9-]+)\.md", destino)) is not None:
            return f'<a href="/ayuda/{nombre.group(1)}">{m.group(1)}</a>'
        if destino == "../MISIONES.md":
            return f'<a href="/ayuda">{m.group(1)}</a>'
        return m.group(1)   # cualquier otro enlace queda como texto
    return _ENLACE.sub(enlace, html)


def _figura(m: Marcador, carpeta: Path) -> str:
    alt = escape(m.alt)
    if (carpeta / m.imagen).is_file():
        return (f'<figure class="captura-ayuda"><img src="/static/ayuda/{m.imagen}" alt="{alt}" loading="lazy">'
                "</figure>")
    return f'<figure class="captura-ayuda pendiente"><figcaption>Captura pendiente: {alt}</figcaption></figure>'


def convertir(texto: str, marcadores: dict[int, Marcador], carpeta: Path = CAPTURAS_DIR) -> tuple[str, Markup]:
    """(título, cuerpo en HTML) de una misión. marcadores: número de línea → marcador de captura."""
    salida: list[str] = []
    parrafo: list[str] = []
    titulo = ""
    estado = {"ol": False, "li": False, "sub": False, "ul": False}

    def cerrar_parrafo():
        if parrafo:
            salida.append("<p>" + "<br>".join(parrafo) + "</p>")
            parrafo.clear()

    def cerrar_sub():
        cerrar_parrafo()
        if estado["sub"]:
            salida.append("</ul>")
            estado["sub"] = False

    def cerrar_paso():
        cerrar_sub()
        if estado["li"]:
            salida.append("</li>")
            estado["li"] = False

    def cerrar_listas():
        cerrar_paso()
        if estado["ol"]:
            salida.append("</ol>")
            estado["ol"] = False
        if estado["ul"]:
            salida.append("</ul>")
            estado["ul"] = False

    for n, linea in enumerate(texto.splitlines(), start=1):
        if not linea.strip():
            cerrar_parrafo()
        elif n in marcadores:
            cerrar_sub()
            salida.append(_figura(marcadores[n], carpeta))
        elif t := _TITULO.match(linea):
            cerrar_listas()
            cerrar_parrafo()
            nivel = len(t.group(1))
            if nivel == 1:
                titulo = _limpiar(t.group(2))
            else:
                salida.append(f"<h{nivel}>{_en_linea(t.group(2))}</h{nivel}>")
        elif p := _NUMERO.match(linea):
            cerrar_paso()
            if estado["ul"]:
                cerrar_listas()
            if not estado["ol"]:
                salida.append(f'<ol start="{int(p.group(1))}">')
                estado["ol"] = True
            salida.append("<li>")
            estado["li"] = True
            parrafo.append(_en_linea(p.group(2)))
        elif (s := _SUBVINETA.match(linea)) and estado["li"]:
            cerrar_parrafo()
            if not estado["sub"]:
                salida.append("<ul>")
                estado["sub"] = True
            salida.append(f"<li>{_en_linea(s.group(1))}</li>")
        elif v := _VINETA.match(linea):
            if estado["ol"]:
                cerrar_listas()
            cerrar_parrafo()
            if not estado["ul"]:
                salida.append("<ul>")
                estado["ul"] = True
            salida.append(f"<li>{_en_linea(v.group(1))}</li>")
        elif linea[0].isspace() and estado["li"]:
            if estado["sub"]:
                cerrar_sub()
            parrafo.append(_en_linea(linea.strip()))
        else:
            cerrar_listas()
            parrafo.append(_en_linea(linea.strip()))
    cerrar_listas()
    cerrar_parrafo()
    return titulo, Markup("\n".join(salida))


def pagina(m: Mision) -> Markup:
    archivo = MISIONES_DIR / f"{m.nombre}.md"
    marcadores = {x.linea: x for x in leer_mision(archivo)}
    return convertir(archivo.read_text(encoding="utf-8"), marcadores)[1]


# --- Buscador ------------------------------------------------------------------------------------------------------

def normalizar(texto: str) -> str:
    """Sin tildes, sin mayúsculas y con espacios simples: «Repórte» → «reporte»."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().split())


def _texto_buscable(m: Mision) -> str:
    lineas = [x for x in (MISIONES_DIR / f"{m.nombre}.md").read_text(encoding="utf-8").splitlines()
              if "[captura:" not in x]
    return normalizar(m.titulo + " " + _limpiar(" ".join(lineas)))


def buscar(consulta: str, es_admin: bool) -> list[Mision]:
    """Las misiones que tienen TODAS las palabras de la consulta (en el título o en los pasos)."""
    palabras = normalizar(consulta).split()
    if not palabras:
        return []
    return [m for m in visibles(es_admin) if all(p in _texto_buscable(m) for p in palabras)]


# --- Glosario ------------------------------------------------------------------------------------------------------

@functools.lru_cache(maxsize=4)
def _glosario(_version: int) -> tuple[Termino, ...]:
    terminos = []
    for linea in GLOSARIO.read_text(encoding="utf-8").splitlines():
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) == 3 and celdas[0].startswith("**"):
            terminos.append(Termino(_limpiar(celdas[0]), *celdas[1:]))
    return tuple(terminos)


def glosario() -> tuple[Termino, ...]:
    return _glosario(GLOSARIO.stat().st_mtime_ns)   # se vuelve a leer solo si el archivo cambió


def termino(palabra: str, texto: str | None = None) -> Markup:
    """Una palabra del panel con su explicación del glosario al pasar el mouse (o con el teclado)."""
    buscada = normalizar(palabra)
    t = next((x for x in glosario() if normalizar(x.palabra) == buscada), None)
    if t is None:
        raise KeyError(f"«{palabra}» no está en docs/ayuda/GLOSARIO.md")
    return Markup('<span class="termino" tabindex="0" data-def="{}">{}</span>').format(t.que, texto or palabra)
