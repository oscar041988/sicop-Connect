"""Respuesta técnica de un cartel: la matriz de cumplimiento (DECISION_PROPUESTA.md, etapa 2; migración 0042).

Una fila por especificación: «el cartel pide · Hermatix ofrece · documento que lo prueba · estado». En Tarrazú (2025)
la matriz valía 25 de 100 puntos. La app FORMULA el PDF; una persona lo revisa, lo firma y lo sube a SICOP.

* Sin IA (primera parte): las filas las escribe una persona. Para empezar, la app propone las especificaciones que ya
  sacó el resumen con IA (solo las que más pesan) con origen «resumen», para distinguirlas de las escritas a mano; si no
  hay resumen, una fila por línea del cartel (origen «cartel»). Ninguna se da por buena: todas empiezan sin marcar.
* Nunca se inventa: lo que Hermatix no cumple queda marcado «No cumple» y sale en el PDF; no se esconde ninguna fila.
* El documento que lo prueba se elige del perfil o del expediente, o se escribe (por ejemplo, «Ficha técnica, pág. 4»).
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import oferta_economica

ESTADOS = {"cumple": "Cumple", "no_cumple": "No cumple", "revisar": "Revisar"}
SIN_MARCAR = "Sin marcar"
ORIGENES = {"resumen": "Del resumen con IA: revisar contra el pliego", "cartel": "Línea del cartel", "": ""}
MAX_FILAS = 300
LIMITES = {"linea": 10, "pide": 1000, "cita": 120, "ofrece": 1000, "prueba": 300, "nota": 500}


class MatrizError(ValueError):
    """Un dato de la matriz no sirve; el mensaje es el que ve la persona."""


@dataclass(frozen=True)
class Fila:
    linea: str
    pide: str
    cita: str
    ofrece: str
    prueba: str
    estado: str          # cumple · no_cumple · revisar · "" (sin marcar)
    nota: str
    origen: str          # resumen · cartel · "" (escrita por una persona)

    @property
    def estado_texto(self) -> str:
        return ESTADOS.get(self.estado, SIN_MARCAR)


def _limpio(valor) -> str:
    return " ".join(str(valor or "").split())


def _sin_dato(texto: str) -> str:
    """El resumen escribe «no encontrado» cuando no tiene el dato: en la matriz va vacío."""
    return "" if texto.lower() == "no encontrado" else texto


def valores_iniciales(compra, resumen: dict | None) -> dict:
    """Una matriz nueva para el cartel. Las filas salen del resumen con IA vigente (sus especificaciones clave) o, si
    no hay, de las líneas del cartel. Lo que ofrece Hermatix, la prueba y el estado quedan vacíos."""
    filas = []
    for item in (resumen or {}).get("que_piden") or []:
        linea, cita = _sin_dato(_limpio(item.get("linea"))), _sin_dato(_limpio(item.get("cita")))
        specs = [_limpio(s) for s in item.get("especificaciones_clave") or [] if _limpio(s)]
        for pide in specs or [_limpio(item.get("bien_o_servicio"))]:
            if pide:
                filas.append({"linea": linea, "pide": pide, "cita": cita, "ofrece": "", "prueba": "", "estado": "",
                              "nota": "", "origen": "resumen"})
    if not filas:
        filas = [{"linea": l.numero_linea, "pide": l.nombre_catalogo or "", "cita": "", "ofrece": "", "prueba": "",
                  "estado": "", "nota": "", "origen": "cartel"} for l in compra.lineas]
    empresa = oferta_economica.configuracion().get("empresa") or {}
    return {"procedimiento": compra.nro_procedimiento or "", "institucion": compra.institucion or "",
            "objeto": compra.descripcion or "", "empresa": _limpio(empresa.get("nombre")), "filas": filas}


def desde_formulario(f) -> dict:
    """Los campos del formulario del panel (un MultiDict de Starlette). Las filas sin «pide», «ofrece» ni «prueba» se
    ignoran (son las vacías para agregar); lo demás lo revisa leer()."""
    columnas = [f.getlist(f"fil_{c}") for c in ("linea", "pide", "cita", "ofrece", "prueba", "estado", "nota",
                                                 "origen")]
    filas = [dict(zip(("linea", "pide", "cita", "ofrece", "prueba", "estado", "nota", "origen"),
                      (str(v).strip() for v in valores)))
             for valores in zip(*columnas)]
    return {"procedimiento": str(f.get("procedimiento") or "").strip(),
            "institucion": str(f.get("institucion") or "").strip(),
            "objeto": str(f.get("objeto") or "").strip(), "empresa": str(f.get("empresa") or "").strip(),
            "filas": [fi for fi in filas if fi["pide"] or fi["ofrece"] or fi["prueba"]][:MAX_FILAS]}


def leer(datos: dict) -> list[Fila]:
    """Revisa la matriz antes del PDF. Cada fila necesita «el cartel pide»; el estado puede quedar sin marcar (sale así
    en el PDF, para que nadie la dé por cumplida)."""
    if not _limpio(datos.get("procedimiento")):
        raise MatrizError("Falta el número de procedimiento.")
    if not _limpio(datos.get("empresa")):
        raise MatrizError("Falta la empresa que presenta la oferta.")
    filas = []
    for n, fi in enumerate(datos.get("filas") or [], start=1):
        valores = {c: _limpio(fi.get(c)) for c in LIMITES}
        if not valores["pide"]:
            raise MatrizError(f"La fila {n} no dice qué pide el cartel.")
        for campo, limite in LIMITES.items():
            if len(valores[campo]) > limite:
                raise MatrizError(f"La fila {n} tiene más de {limite} caracteres en «{campo}».")
        estado = _limpio(fi.get("estado"))
        if estado and estado not in ESTADOS:
            raise MatrizError(f"La fila {n} tiene un estado que no existe.")
        origen = _limpio(fi.get("origen"))
        filas.append(Fila(estado=estado, origen=origen if origen in ORIGENES else "", **valores))
    if not filas:
        raise MatrizError("La matriz no tiene filas: agrega al menos una especificación.")
    return filas


def conteo(filas: list[Fila]) -> dict[str, int]:
    """Cuántas filas hay en cada estado, en el orden en que se muestran; los ceros no salen."""
    textos = [*ESTADOS.values(), SIN_MARCAR]
    cuenta = {t: sum(1 for fi in filas if fi.estado_texto == t) for t in textos}
    return {t: n for t, n in cuenta.items() if n}


def html(datos: dict, filas: list[Fila], hoy: date) -> str:
    entorno = Environment(loader=FileSystemLoader(oferta_economica.PLANTILLAS), autoescape=select_autoescape(["html"]))
    logo = oferta_economica.LOGO
    logo = "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode("ascii") if logo.is_file() else ""
    return entorno.get_template("respuesta_tecnica.html").render(
        d=datos, filas=filas, conteo=conteo(filas), logo=logo, fecha=oferta_economica.fecha_larga(hoy))


def pdf(contenido_html: str, procedimiento: str) -> bytes:
    return oferta_economica.pdf(contenido_html, procedimiento, titulo="Respuesta técnica", membrete=False)


# --- Panel: borrador y sugerencias -----------------------------------------------------------------------------------

def borrador(conn, nro_sicop: str) -> tuple[dict, str, str] | None:
    """(datos, quién lo guardó, cuándo) del borrador del cartel, o None si no hay."""
    fila = conn.execute("SELECT datos_json, actualizado_por_nombre, actualizado_en FROM respuestas_tecnicas_borrador"
                        " WHERE nro_sicop = ?", (nro_sicop,)).fetchone()
    return (json.loads(fila[0]), fila[1], fila[2]) if fila else None


def guardar_borrador(conn, nro_sicop: str, datos: dict, quien, ahora) -> None:
    """Reemplaza el borrador del cartel y lo anota en el historial."""
    from app import historial
    from app.database import transaccion
    with transaccion(conn):
        conn.execute(
            "INSERT INTO respuestas_tecnicas_borrador (nro_sicop, datos_json, actualizado_por, actualizado_por_nombre,"
            " actualizado_en) VALUES (?, ?, ?, ?, ?) ON CONFLICT (nro_sicop) DO UPDATE SET datos_json ="
            " excluded.datos_json, actualizado_por = excluded.actualizado_por, actualizado_por_nombre ="
            " excluded.actualizado_por_nombre, actualizado_en = excluded.actualizado_en",
            (nro_sicop, json.dumps(datos, ensure_ascii=False), quien.user_id, quien.nombre,
             ahora.isoformat(timespec="seconds")))
        historial.registrar(conn, quien, "guardar_respuesta_tecnica", nro_sicop)


def sugerencias_prueba(conn, nro_sicop: str) -> list[str]:
    """Para «documento que lo prueba»: los documentos del perfil de Hermatix y los archivos del expediente del cartel.
    Solo los nombres; la persona puede escribir otro."""
    from app import expediente_archivos, perfil
    nombres = [f"Perfil: {e.titulo}" for e in perfil.listar(conn)]
    nombres += [f"Expediente: {a.nombre}" for a in expediente_archivos.listar(conn, nro_sicop)]
    return list(dict.fromkeys(nombres))
