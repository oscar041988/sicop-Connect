"""Importador del ZIP «Reporte de adjudicaciones en firme» (reportes 6, 6.1 y 6.2 del diccionario de SICOP).

Encabezados reales del 2026-10-22 (docs/MAPEO_DATOS.md). Lo que hay que saber de estos archivos:
* El adjudicatario viene SOLO como cédula («Cédula Empresa Proveedora»). No se inventa el nombre: lo pone
  Hermatix en config/competidores.yaml.
* Los archivos repiten filas idénticas (en el 6.1, miles): se advierten y se guardan una vez.
* Un cartel tiene varias filas en el 6 (un acto en firme por fila) y una línea puede tener más de un
  registro distinto en el 6.2. Se guarda cada registro distinto; su clave es su propia huella, que es la
  misma de raw_snapshots: así cada cifra se rastrea hasta la fila original y el archivo de donde salió.
* En el reporte 6, SICOP marca «sin valor» con un espacio (' '): en el archivo real del 2026-10-22, 4345 filas
  en «Fecha Maxima Recursos», 663 en «Permite Recursos» y 13 en «Fecha Comunicación». Se guarda como vacío;
  la fila original queda tal cual en raw_snapshots.
* Si el cartel no está importado, la adjudicación igual se guarda (es dato de SICOP), pero se advierte:
  sin cartel no hay título y no se le puede aplicar ninguna familia.
* Monto de la línea = cantidad × precio unitario − descuento (sin impuestos), en Decimal y en su moneda.
  En el archivo real el descuento y el IVA son montos, no porcentajes (p. ej. 11 × 55 000 con descuento
  90 750 = 15 %). IVA, otros impuestos y acarreos se guardan aparte y no se suman al monto.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from app.dinero import parse_decimal, texto_decimal
from app.importers import zip_pliegos
from app.importers.carteles import FORMATO_FECHA
from app.importers.comun import (HORA_CR, Fila, FilaRechazada, Resultado, exigir_digitos, importar_reporte,
                                 upsert)
from app.importers.csv_reader import parse_csv

# Nombre dentro del ZIP → reporte, en el orden en que se importan (ZIP real del 2026-10-22).
ARCHIVOS = {
    "Detalle Adjudicaciones.csv": "adjudicaciones",
    "Det Proveedores Adj.csv": "adjudicacion_proveedores",
    "Det Lineas Adjudicadas.csv": "adjudicacion_lineas",
}

COLUMNAS_ADJ = ("Número SICOP", "Numero de procedimiento", "Fecha Comunicación", "Fecha Adj Firme",
                "Permite Recursos", "Fecha Maxima Recursos", "Desierto")
COLUMNAS_PROV = ("Número SICOP", "Numero de procedimiento", "Cédula Empresa Proveedora")
COLUMNAS_LINEA = ("Número SICOP", "Numero de linea", "Cédula Empresa Proveedora", "Cantidad", "Precio", "Moneda",
                  "Descuento", "IVA", "Otros Impuestos", "Acarreos", "Tipo Cambio CRC")
_MONEDA = re.compile(r"^[A-Z]{3}$")

ADV_IDENTICA = "Fila idéntica a otra del archivo: se guarda una sola vez"
ADV_SIN_CARTEL = "Cartel no importado: se guarda, pero sin título no se le puede aplicar una familia"
ADV_VARIOS_REGISTROS = "Línea con más de un registro distinto (mismo cartel, línea y cédula): su monto no se suma"
ADV_EN_CERO = "Cantidad o precio en cero: monto 0"


def huella(original: dict[str, str]) -> str:
    """La misma huella que usa importar_reporte para raw_snapshots."""
    payload = json.dumps(original, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fecha(columna: str, valor: str) -> str | None:
    if not valor:
        return None
    try:
        fecha = datetime.strptime(valor, FORMATO_FECHA).replace(tzinfo=HORA_CR)
    except ValueError:
        raise FilaRechazada(f"«{columna}» con formato inválido ({valor!r}); se espera dd/mm/aaaa hh:mm:ss")
    return fecha.isoformat(timespec="seconds")


def _decimal(columna: str, valor: str):
    try:
        return parse_decimal(valor)
    except ValueError as exc:
        raise FilaRechazada(f"«{columna}» inválido: {exc}")


def _guardar_registro(conn: sqlite3.Connection, tabla: str, campos: dict, content_hash: str, import_id: int,
                      momento: str) -> str:
    """Un registro por huella: si ya estaba, solo se anota que se volvió a ver. `tabla` es constante del código."""
    if conn.execute(f"SELECT 1 FROM {tabla} WHERE content_hash = ?", (content_hash,)).fetchone():
        conn.execute(f"UPDATE {tabla} SET last_seen = ? WHERE content_hash = ?", (momento, content_hash))
        return "sin_cambios"
    valores = {**campos, "content_hash": content_hash, "first_import_id": import_id,
               "first_seen": momento, "last_seen": momento}
    conn.execute(f"INSERT INTO {tabla} ({', '.join(valores)}) VALUES ({', '.join(':' + c for c in valores)})",
                 valores)
    return "nueva"


def _carteles(conn: sqlite3.Connection) -> set[str]:
    return {nro for (nro,) in conn.execute("SELECT nro_sicop FROM tenders")}


def import_adjudicaciones(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                          source_run_id: int | None = None) -> Resultado:
    """Reporte 6 «Detalle Adjudicaciones»: una fila por acto en firme."""
    carteles = _carteles(conn)

    def validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
        v = {columna: valor.strip() for columna, valor in fila.items()}  # « » = sin valor (ver arriba)
        nro = exigir_digitos("Número SICOP", v["Número SICOP"])
        campos = {
            "nro_sicop": nro,
            "nro_procedimiento": v["Numero de procedimiento"] or None,
            "fecha_comunicacion": _fecha("Fecha Comunicación", v["Fecha Comunicación"]),
            "fecha_adj_firme": _fecha("Fecha Adj Firme", v["Fecha Adj Firme"]),
            "permite_recursos": v["Permite Recursos"] or None,
            "fecha_maxima_recursos": _fecha("Fecha Maxima Recursos", v["Fecha Maxima Recursos"]),
            "desierto": v["Desierto"] or None,
        }
        if nro not in carteles:
            resultado.advertir(ADV_SIN_CARTEL, linea)
        return Fila(f"{nro}|{huella(fila)[:16]}", campos, fila)

    def guardar(conn, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
        return _guardar_registro(conn, "adjudicaciones", fila.campos, content_hash, import_id, momento)

    raw = path.read_bytes()
    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(raw), report="adjudicaciones",
        entidad="adjudicacion", origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS_ADJ,
        nombre_clave="Adjudicación", validar=validar, guardar=guardar, source_run_id=source_run_id,
        repetida_identica=ADV_IDENTICA,
    )


def import_proveedores(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                       source_run_id: int | None = None) -> Resultado:
    """Reporte 6.1 «Det Proveedores Adj»: quién ganó cada cartel (solo la cédula)."""
    carteles = _carteles(conn)

    def validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
        nro = exigir_digitos("Número SICOP", fila["Número SICOP"])
        cedula = exigir_digitos("Cédula Empresa Proveedora", fila["Cédula Empresa Proveedora"])
        if nro not in carteles:
            resultado.advertir(ADV_SIN_CARTEL, linea)
        campos = {"nro_sicop": nro, "cedula_proveedor": cedula,
                  "nro_procedimiento": fila["Numero de procedimiento"] or None}
        return Fila(f"{nro}|{cedula}", campos, fila)

    def guardar(conn, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
        clave = {"nro_sicop": fila.campos["nro_sicop"], "cedula_proveedor": fila.campos["cedula_proveedor"]}
        return upsert(conn, "adjudicacion_proveedores", clave,
                      {"nro_procedimiento": fila.campos["nro_procedimiento"]}, content_hash, momento,
                      al_crear={"first_import_id": import_id})

    raw = path.read_bytes()
    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(raw), report="adjudicacion_proveedores",
        entidad="adjudicacion_proveedor", origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS_PROV,
        nombre_clave="Proveedor adjudicado (Número SICOP|cédula)", validar=validar, guardar=guardar,
        source_run_id=source_run_id, repetida_identica=ADV_IDENTICA,
    )


def import_lineas_adjudicadas(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                              source_run_id: int | None = None) -> Resultado:
    """Reporte 6.2 «Det Lineas Adjudicadas»: qué línea ganó cada cédula, a qué precio y en qué moneda."""
    carteles = _carteles(conn)
    primera_huella: dict[tuple[str, str, str], str] = {}  # (cartel, línea, cédula) → huella del primer registro

    def validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
        nro = exigir_digitos("Número SICOP", fila["Número SICOP"])
        numero = exigir_digitos("Numero de linea", fila["Numero de linea"])
        cedula = exigir_digitos("Cédula Empresa Proveedora", fila["Cédula Empresa Proveedora"])
        cantidad = _decimal("Cantidad", fila["Cantidad"])
        precio = _decimal("Precio", fila["Precio"])
        descuento = _decimal("Descuento", fila["Descuento"])
        for columna in ("IVA", "Otros Impuestos", "Acarreos", "Tipo Cambio CRC"):
            _decimal(columna, fila[columna])
        moneda = fila["Moneda"]
        if not _MONEDA.match(moneda):
            raise FilaRechazada(f"«Moneda» no válida ({moneda!r}); se esperan 3 letras, p. ej. CRC o USD")
        monto = cantidad * precio - descuento
        if monto < 0:
            raise FilaRechazada(f"el descuento ({descuento}) es mayor que cantidad × precio ({cantidad * precio})")
        if cantidad == 0 or precio == 0:
            resultado.advertir(ADV_EN_CERO, linea)
        if nro not in carteles:
            resultado.advertir(ADV_SIN_CARTEL, linea)
        propia = huella(fila)
        if primera_huella.setdefault((nro, numero, cedula), propia) != propia:
            resultado.advertir(ADV_VARIOS_REGISTROS, linea)
        campos = {
            "nro_sicop": nro, "numero_linea": numero, "cedula_proveedor": cedula,
            "cantidad": fila["Cantidad"], "precio_unitario": fila["Precio"], "moneda": moneda,
            "descuento": fila["Descuento"], "iva": fila["IVA"], "otros_impuestos": fila["Otros Impuestos"],
            "acarreos": fila["Acarreos"], "tipo_cambio_crc": fila["Tipo Cambio CRC"],
            "monto_sin_impuestos": texto_decimal(monto),
        }
        return Fila(f"{nro}|{numero}|{cedula}|{propia[:16]}", campos, fila)

    def guardar(conn, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
        return _guardar_registro(conn, "adjudicacion_lineas", fila.campos, content_hash, import_id, momento)

    raw = path.read_bytes()
    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(raw), report="adjudicacion_lineas",
        entidad="adjudicacion_linea", origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS_LINEA,
        nombre_clave="Línea adjudicada", validar=validar, guardar=guardar, source_run_id=source_run_id,
        repetida_identica=ADV_IDENTICA,
    )


IMPORTADORES = {
    "adjudicaciones": import_adjudicaciones,
    "adjudicacion_proveedores": import_proveedores,
    "adjudicacion_lineas": import_lineas_adjudicadas,
}


def import_zip(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
               source_run_id: int | None = None) -> list[tuple[str, Resultado]]:
    """Importa los tres CSV del ZIP tal como lo entrega SICOP. Lanza zip_pliegos.ZipInvalido si no lo es."""
    with tempfile.TemporaryDirectory() as temporal:
        csvs = zip_pliegos.extraer(path, Path(temporal), ARCHIVOS, "reporte de adjudicaciones en firme")
        return [(reporte, IMPORTADORES[reporte](conn, ruta, origen, raw_dir, source_run_id))
                for reporte, ruta in csvs]
