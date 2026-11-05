"""«¿Cumple?» en el resumen con IA y en el Reporte de cartel (pedido de Ivania, 2026-11-05; migración 0038).

* Requerimientos: el estado lo calcula el asistente de elegibilidad (app/elegibilidad.py) con las respuestas de hoy:
  Cumple · No cumple · Falta · Revisar. Cada requerimiento del resumen se une con su requisito de la lista de
  verificación por «clave» (su texto normalizado, la misma de app/ai/verificacion.py). Sin asistente empezado, o si
  el requisito ya no está en la lista: «Sin evaluar». Los informativos (plazos, lugar…) no se preguntan: «Informativo».
* Qué piden: nada en la app compara bienes y especificaciones con lo que ofrece Hermatix, así que lo marca una
  persona (el encargado o un administrador): Cumple · No cumple · Revisar, con una nota. Vale la última marca.
* La app no decide nada: muestra lo que dicen el asistente y las personas (regla: todo requisito se presenta).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from app import asistente, elegibilidad, historial
from app.ai import verificacion
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

ESTADOS_LINEA = {"cumple": "Cumple", "no_cumple": "No cumple", "revisar": "Revisar"}
SIN_EVALUAR = "Sin evaluar"
INFORMATIVO = "Informativo"
MAX_NOTA = 500


class MarcaInvalida(ValueError):
    """La marca no se acepta; el mensaje es el que verá la persona."""


@dataclass(frozen=True)
class Estado:
    clave: str                 # cumple · no_cumple · falta · revisar · sin_evaluar · informativo (para el color)
    texto: str
    detalle: str = ""          # el motivo del asistente, o quién marcó y su nota


SIN = Estado("sin_evaluar", SIN_EVALUAR)


def clave_linea(linea: dict) -> str:
    """Una fila de «Qué piden»: su número de línea y su bien o servicio, normalizados."""
    return verificacion.clave_de(f"{linea.get('linea') or ''} {linea.get('bien_o_servicio') or ''}")


def de_requerimientos(conn: sqlite3.Connection, nro_sicop: str, dia: date) -> dict[str, Estado]:
    """{clave del requisito: estado} según el asistente de hoy; vacío si el asistente no se empezó."""
    if asistente.sesion(conn, nro_sicop) is None:
        return {}
    evaluaciones, _ = elegibilidad.evaluacion_actual(conn, nro_sicop, dia)
    pares = [(i, Estado("informativo", INFORMATIVO, "No se pregunta: es un dato del pliego."))
             for i in asistente.informativos(conn, nro_sicop)]
    pares += [(e.item, Estado(e.estado, e.estado_texto, e.motivo)) for e in evaluaciones]
    # Por su clave (la del resumen del que salió) y por su texto actual (los agregados a mano tienen otra clave).
    estados = {verificacion.clave_de(i.requisito): e for i, e in pares}
    estados.update({i.clave: e for i, e in pares})
    return estados


def de_lineas(conn: sqlite3.Connection, nro_sicop: str) -> dict[str, Estado]:
    """{clave de la fila: la última marca de una persona}."""
    filas = conn.execute(
        "SELECT clave, estado, nota, marcado_por_nombre, creado_en FROM resumen_lineas_cumple"
        " WHERE id IN (SELECT MAX(id) FROM resumen_lineas_cumple WHERE nro_sicop = ? GROUP BY clave)",
        (nro_sicop,)).fetchall()
    return {clave: Estado(estado, ESTADOS_LINEA[estado],
                          f"Marcado por {por} el {creado[8:10]}/{creado[5:7]}/{creado[:4]}" + (f": {nota}" if nota else "."))
            for clave, estado, nota, por, creado in filas}


def requerimiento(estados: dict[str, Estado], q: dict) -> Estado:
    return estados.get(verificacion.clave_de(str(q.get("requisito") or "")), SIN)


def linea(estados: dict[str, Estado], i: dict) -> Estado:
    return estados.get(clave_linea(i), SIN)


def huella(reqs: dict[str, Estado], lineas: dict[str, Estado]) -> str:
    """Cambia si cambia algún estado: el reporte se rehace (app/ai/reporte.py)."""
    datos = {"r": {k: e.clave for k, e in reqs.items()}, "l": {k: e.clave for k, e in lineas.items()}}
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()


def marcar(conn: sqlite3.Connection, nro_sicop: str, resumen: dict, clave: str, estado: str, nota: str,
           quien: Quien, ahora: datetime) -> None:
    """Guarda la marca de una fila de «Qué piden» del resumen vigente. Nunca borra la anterior."""
    if estado not in ESTADOS_LINEA:
        raise MarcaInvalida("Elige «Cumple», «No cumple» o «Revisar».")
    nota = " ".join(nota.split())
    if len(nota) > MAX_NOTA:
        raise MarcaInvalida(f"La nota puede tener hasta {MAX_NOTA} caracteres.")
    fila = next((i for i in resumen.get("que_piden") or [] if clave_linea(i) == clave), None)
    if fila is None:
        raise MarcaInvalida("Esa fila ya no está en el resumen: recarga la página.")
    texto = f"{fila.get('linea') or ''} · {fila.get('bien_o_servicio') or ''}"
    with transaccion(conn):
        conn.execute(
            "INSERT INTO resumen_lineas_cumple (nro_sicop, clave, linea, estado, nota, marcado_por,"
            " marcado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nro_sicop, clave, texto, estado, nota, quien.user_id, quien.nombre,
             ahora.astimezone(HORA_CR).isoformat(timespec="seconds")))
        historial.registrar(conn, quien, "marcar_cumple_linea", f"{nro_sicop}: {texto[:80]} → {ESTADOS_LINEA[estado]}")
