"""Consulta de una compra: cartel + institución compradora + líneas con su catálogo.

Las uniones son solo por claves verificadas (cédula, Número SICOP, código de identificación).
Lo que no une se muestra como faltante, nunca se rellena.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from app.dinero import Monto, parse_decimal, totales_por_moneda


@dataclass
class LineaCompra:
    numero_linea: str
    numero_partida: str | None
    codigo_identificacion: str
    nombre_catalogo: str | None
    estado_catalogo: str  # en_catalogo | clasificacion_no_descargada | codigo_no_esta_en_catalogo
    cantidad: str
    precio_unitario: str
    estimado: Monto


@dataclass
class Compra:
    nro_sicop: str
    nro_procedimiento: str | None
    descripcion: str | None
    fecha_publicacion: str | None
    fecha_cierre_recepcion: str | None
    institution_cedula: str | None
    institucion: str | None  # None = la cédula no está en institutions
    lineas: list[LineaCompra] = field(default_factory=list)

    @property
    def estimado_por_moneda(self) -> dict[str, Monto]:
        """Un total por moneda; CRC y USD nunca se mezclan."""
        return totales_por_moneda(linea.estimado for linea in self.lineas)


def detalle_compra(conn: sqlite3.Connection, nro_sicop: str) -> Compra | None:
    cartel = conn.execute(
        "SELECT t.nro_sicop, t.nro_procedimiento, t.descripcion, t.fecha_publicacion,"
        " t.fecha_cierre_recepcion, t.institution_cedula, i.nombre"
        " FROM tenders t LEFT JOIN institutions i ON i.cedula = t.institution_cedula"
        " WHERE t.nro_sicop = ?",
        (nro_sicop,),
    ).fetchone()
    if cartel is None:
        return None
    compra = Compra(*cartel)
    filas = conn.execute(
        "SELECT numero_linea, numero_partida, codigo_identificacion, nombre_catalogo, estado_catalogo,"
        " cantidad_solicitada, precio_unitario_estimado, estimado_linea, moneda"
        " FROM v_tender_lines WHERE nro_sicop = ? ORDER BY CAST(numero_linea AS INTEGER), numero_linea",
        (nro_sicop,),
    )
    for (numero, partida, codigo, nombre, estado, cantidad, precio, estimado, moneda) in filas:
        compra.lineas.append(LineaCompra(numero, partida, codigo, nombre, estado, cantidad, precio,
                                         Monto(parse_decimal(estimado), moneda)))
    return compra
