"""Inteligencia competitiva: quién gana lo adjudicado en cada familia de Hermatix.

Cómo se arma cada cifra (todas se rastrean hasta su registro original, ver registros()):
* Familia: la del cartel adjudicado, evaluado con las MISMAS reglas que las oportunidades
  (opportunity_assessments de la versión vigente). Las líneas adjudicadas no traen texto propio, así que todas
  las del cartel cuentan para sus familias; un cartel puede contar en más de una.
* Quién gana: la cédula del reporte 6.1. El nombre sale de config/competidores.yaml (lo edita Hermatix); sin
  nombre se muestra la cédula. SICOP no entrega el nombre del adjudicatario.
* Cuántas veces: carteles distintos que ganó (una cédula o cualquiera de las de su competidor).
* Montos: suma de cantidad × precio − descuento (sin impuestos) de sus líneas del reporte 6.2, SEPARADA POR
  MONEDA y en Decimal. Nunca se convierte con el tipo de cambio. Una línea con más de un registro distinto
  (mismo cartel, línea y cédula) no se suma: no se sabe cuál vale. Se cuenta aparte y se puede revisar.
* Periodo: por la fecha de adjudicación en firme del cartel (la primera, si tiene varios actos), en hora de
  Costa Rica.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml

from app.config import PROJECT_ROOT
from app.importers.comun import SOLO_DIGITOS

COMPETIDORES_PATH = PROJECT_ROOT / "config" / "competidores.yaml"
PRIORIDADES = {
    "candidatos": ("alta", "media"),
    "alta": ("alta",),
    "media": ("media",),
    "baja": ("baja",),
    "todas": ("alta", "media", "baja"),
}
PREFIJO_CEDULA = "cedula:"  # competidor sin nombre en el YAML: se identifica por su cédula


class CompetidoresError(Exception):
    """config/competidores.yaml no tiene la forma esperada; el mensaje es el que verá la usuaria."""


def cargar_competidores(path: Path | None = None) -> dict[str, str]:
    """{cédula: nombre del competidor}. Un archivo que no existe equivale a uno vacío."""
    path = path or COMPETIDORES_PATH
    if not path.exists():
        return {}
    try:
        datos = yaml.safe_load(path.read_bytes().decode("utf-8")) or {}
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise CompetidoresError(f"config/competidores.yaml no se puede leer: {exc}") from exc
    if not isinstance(datos, dict) or not isinstance(datos.get("competidores") or {}, dict):
        raise CompetidoresError("config/competidores.yaml debe empezar con «competidores:»")
    por_cedula: dict[str, str] = {}
    for nombre, valor in (datos.get("competidores") or {}).items():
        if not isinstance(valor, dict) or set(valor) != {"cedulas"} or not isinstance(valor["cedulas"], list):
            raise CompetidoresError(f"«{nombre}» debe tener solo «cedulas:» con una lista de cédulas")
        for cedula in valor["cedulas"]:
            if not isinstance(cedula, str):
                # YAML lee 0123 como número y se comería el cero inicial: las cédulas van entre comillas.
                raise CompetidoresError(f"«{nombre}»: la cédula {cedula!r} debe ir entre comillas, p. ej. \"3101000000\"")
            if not SOLO_DIGITOS.match(cedula):
                raise CompetidoresError(f"«{nombre}»: la cédula {cedula!r} debe tener solo dígitos, sin guiones")
            if cedula in por_cedula and por_cedula[cedula] != nombre:
                raise CompetidoresError(f"La cédula {cedula} está en «{por_cedula[cedula]}» y en «{nombre}»")
            por_cedula[cedula] = str(nombre)
    return por_cedula


@dataclass(frozen=True)
class Filtro:
    desde: date | None = None
    hasta: date | None = None
    prioridad: str = "candidatos"

    @classmethod
    def desde_texto(cls, desde: str = "", hasta: str = "", prioridad: str = "") -> Filtro:
        """Del formulario: fechas aaaa-mm-dd (una ilegible se ignora) y una prioridad conocida."""
        def leer(texto: str) -> date | None:
            try:
                return date.fromisoformat(texto) if texto else None
            except ValueError:
                return None
        return cls(leer(desde), leer(hasta), prioridad if prioridad in PRIORIDADES else "candidatos")

    def consulta(self) -> dict[str, str]:
        return {k: v for k, v in {"desde": self.desde.isoformat() if self.desde else "",
                                  "hasta": self.hasta.isoformat() if self.hasta else "",
                                  "prioridad": self.prioridad if self.prioridad != "candidatos" else ""}.items() if v}


@dataclass
class Competidor:
    clave: str                      # nombre del YAML, o «cedula:…» si no está
    nombre: str | None              # None = la cédula no está en competidores.yaml
    cedulas: set[str] = field(default_factory=set)
    carteles: set[str] = field(default_factory=set)
    instituciones: dict[str, int] = field(default_factory=dict)  # institución → carteles ganados
    montos: dict[str, Decimal] = field(default_factory=dict)     # moneda → suma (nunca mezcladas)
    lineas: int = 0                 # líneas sumadas
    lineas_en_conflicto: int = 0    # registros que no se suman (ver docstring)
    carteles_sin_lineas: int = 0    # ganó el cartel (6.1) pero no hay líneas suyas en 6.2

    @property
    def veces(self) -> int:
        return len(self.carteles)

    def montos_ordenados(self) -> list[tuple[str, Decimal]]:
        return sorted(self.montos.items())


@dataclass
class FamiliaCompetencia:
    familia: str
    carteles: set[str] = field(default_factory=set)
    competidores: list[Competidor] = field(default_factory=list)


@dataclass
class Cobertura:
    carteles_adjudicados: int = 0   # en el periodo, según el reporte 6
    con_cartel: int = 0             # su cartel está importado (se le pueden aplicar las reglas)
    clasificados: int = 0           # con alguna familia en la prioridad elegida
    sin_fecha: int = 0              # sin fecha en firme: no entran si se filtra por periodo


@dataclass
class Resumen:
    familias: list[FamiliaCompetencia]
    cobertura: Cobertura
    sin_nombre: int                 # cédulas ganadoras que no están en competidores.yaml


def _firmes(conn: sqlite3.Connection) -> dict[str, str | None]:
    """Cartel → primera fecha de adjudicación en firme (ISO en hora de Costa Rica)."""
    return {nro: fecha for nro, fecha in conn.execute(
        "SELECT nro_sicop, min(fecha_adj_firme) FROM adjudicaciones GROUP BY nro_sicop")}


def _en_periodo(fecha: str | None, filtro: Filtro) -> bool:
    if filtro.desde is None and filtro.hasta is None:
        return True
    if not fecha:
        return False
    dia = date.fromisoformat(fecha[:10])  # la fecha local: «2026-08-18T07:22:31-06:00» → 2026-08-18
    return (filtro.desde is None or dia >= filtro.desde) and (filtro.hasta is None or dia <= filtro.hasta)


def _clave(cedula: str, nombres: dict[str, str]) -> str:
    return nombres.get(cedula) or PREFIJO_CEDULA + cedula


def _ganadas(conn, version: str, filtro: Filtro, firmes: dict[str, str | None]):
    """[(familia, cartel, cédula, institución)] de los carteles adjudicados con familia en el periodo."""
    encajes = PRIORIDADES[filtro.prioridad]
    filas = conn.execute(
        f"""SELECT a.familia, p.nro_sicop, p.cedula_proveedor, coalesce(i.nombre, t.institution_cedula, 'Sin institución')
            FROM adjudicacion_proveedores p
            JOIN tenders t ON t.nro_sicop = p.nro_sicop
            JOIN opportunity_assessments a ON a.nro_sicop = p.nro_sicop AND a.rules_version = ?
             AND a.encaje IN ({', '.join('?' * len(encajes))})
            LEFT JOIN institutions i ON i.cedula = t.institution_cedula
            ORDER BY a.familia, p.nro_sicop, p.cedula_proveedor""",
        (version, *encajes))
    return [f for f in filas if f[1] in firmes and _en_periodo(firmes[f[1]], filtro)]


def _lineas(conn, carteles: set[str]):
    """{(cartel, cédula): [(moneda, monto, registros de esa línea)]} de los carteles pedidos."""
    resultado: dict[tuple[str, str], list[tuple[str, Decimal, int]]] = defaultdict(list)
    for nro, cedula, moneda, monto, registros in conn.execute(
        """SELECT l.nro_sicop, l.cedula_proveedor, l.moneda, l.monto_sin_impuestos,
                  count(*) OVER (PARTITION BY l.nro_sicop, l.numero_linea, l.cedula_proveedor)
           FROM adjudicacion_lineas l"""
    ):
        if nro in carteles:
            resultado[(nro, cedula)].append((moneda, Decimal(monto), registros))
    return resultado


def resumen(conn: sqlite3.Connection, version: str, filtro: Filtro, nombres: dict[str, str]) -> Resumen:
    firmes = _firmes(conn)
    ganadas = _ganadas(conn, version, filtro, firmes)
    lineas = _lineas(conn, {nro for _, nro, _, _ in ganadas})

    familias: dict[str, FamiliaCompetencia] = {}
    por_familia: dict[str, dict[str, Competidor]] = defaultdict(dict)
    for familia, nro, cedula, institucion in ganadas:
        fam = familias.setdefault(familia, FamiliaCompetencia(familia))
        fam.carteles.add(nro)
        clave = _clave(cedula, nombres)
        comp = por_familia[familia].setdefault(clave, Competidor(clave, nombres.get(cedula)))
        comp.cedulas.add(cedula)
        if nro not in comp.carteles:
            comp.carteles.add(nro)
            comp.instituciones[institucion] = comp.instituciones.get(institucion, 0) + 1
        suyas = lineas.get((nro, cedula), [])
        if not suyas:
            comp.carteles_sin_lineas += 1
        for moneda, monto, registros in suyas:
            if registros > 1:
                comp.lineas_en_conflicto += 1
                continue
            comp.montos[moneda] = comp.montos.get(moneda, Decimal(0)) + monto
            comp.lineas += 1

    for familia, comps in por_familia.items():
        familias[familia].competidores = sorted(comps.values(), key=lambda c: (-c.veces, c.clave))

    con_cartel = {nro for (nro,) in conn.execute(
        "SELECT DISTINCT d.nro_sicop FROM adjudicaciones d JOIN tenders t ON t.nro_sicop = d.nro_sicop")}
    en_periodo = [nro for nro, fecha in firmes.items() if _en_periodo(fecha, filtro)]
    cobertura = Cobertura(
        carteles_adjudicados=len(en_periodo),
        con_cartel=sum(1 for nro in en_periodo if nro in con_cartel),
        clasificados=len({nro for _, nro, _, _ in ganadas}),
        sin_fecha=sum(1 for fecha in firmes.values() if not fecha),
    )
    sin_nombre = len({cedula for _, _, cedula, _ in ganadas if cedula not in nombres})
    return Resumen(sorted(familias.values(), key=lambda f: f.familia), cobertura, sin_nombre)


@dataclass
class Registro:
    """Una línea adjudicada tal como se guardó, con el archivo de donde salió."""
    id: int
    numero_linea: str
    cedula: str
    cantidad: str
    precio_unitario: str
    moneda: str
    descuento: str | None
    iva: str | None
    monto: Decimal
    registros: int                  # > 1: en conflicto, no se suma
    import_id: int | None
    archivo: str | None


@dataclass
class CartelGanado:
    nro_sicop: str
    titulo: str | None
    institucion: str
    fecha_firme: str | None
    cedulas: list[str]
    lineas: list[Registro] = field(default_factory=list)


def registros(conn: sqlite3.Connection, version: str, filtro: Filtro, nombres: dict[str, str],
              familia: str, competidor: str) -> list[CartelGanado]:
    """Los carteles y líneas detrás de una fila del resumen: misma familia, competidor, periodo y prioridad."""
    firmes = _firmes(conn)
    elegidos: dict[str, CartelGanado] = {}
    for fam, nro, cedula, institucion in _ganadas(conn, version, filtro, firmes):
        if fam != familia or _clave(cedula, nombres) != competidor:
            continue
        cartel = elegidos.setdefault(nro, CartelGanado(nro, None, institucion, firmes.get(nro), []))
        cartel.cedulas.append(cedula)
    for cartel in elegidos.values():
        cartel.titulo = (conn.execute("SELECT descripcion FROM tenders WHERE nro_sicop = ?",
                                      (cartel.nro_sicop,)).fetchone() or (None,))[0]
        marcas = ", ".join("?" * len(cartel.cedulas))
        for fila in conn.execute(
            f"""SELECT l.id, l.numero_linea, l.cedula_proveedor, l.cantidad, l.precio_unitario, l.moneda,
                       l.descuento, l.iva, l.monto_sin_impuestos,
                       (SELECT count(*) FROM adjudicacion_lineas o WHERE o.nro_sicop = l.nro_sicop
                         AND o.numero_linea = l.numero_linea AND o.cedula_proveedor = l.cedula_proveedor),
                       l.first_import_id, m.file_name
                FROM adjudicacion_lineas l LEFT JOIN imports m ON m.id = l.first_import_id
                WHERE l.nro_sicop = ? AND l.cedula_proveedor IN ({marcas})
                ORDER BY CAST(l.numero_linea AS INTEGER), l.id""",
            (cartel.nro_sicop, *cartel.cedulas),
        ):
            cartel.lineas.append(Registro(*fila[:8], Decimal(fila[8]), *fila[9:]))
    return sorted(elegidos.values(), key=lambda c: (c.fecha_firme or "", c.nro_sicop), reverse=True)


def nombre_competidor(clave: str) -> str:
    """Para mostrar: el nombre del YAML, o «Cédula 3101…» si no tiene nombre."""
    if clave.startswith(PREFIJO_CEDULA):
        return f"Cédula {clave[len(PREFIJO_CEDULA):]}"
    return clave
