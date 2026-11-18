"""Lo que el asistente pide para la oferta, además de los requisitos (pedido de Ivania, 2026-11-18; migración 0048).

* Precio del cartel: lo escribe una persona (la IA no pone ni cambia precios: DECISION_IA.md regla 3). Manda sobre
  config/tarifario.yaml solo en ese cartel; el tarifario no cambia. Montos en Decimal, con su moneda.
* Producto y ficha técnica (anexo 3): se elige el producto y se sube su ficha en PDF, por cartel.
* Pliego: si el enriquecimiento no trajo uno con texto, una persona sube el PDF descargado de SICOP. Queda aparte de
  los documentos de SICOP (tender_documents), marcado como subido por esa persona.
* Representante legal: uno para todas las ofertas, solo un administrador (lo revisa la ruta). Nunca va a la IA.

Lo usan el encargado del cartel y los administradores (la regla del asistente; la revisa la ruta). Nada se borra:
cambiar es agregar una fila, y vale la más nueva. El historial anota quién y qué cartel, nunca montos ni cédulas.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO

from app import archivos, historial, oferta_economica
from app.archivos import ArchivoInvalido
from app.config import Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR
from app.sources import sicop_documentos

# Los productos de Hermatix (las claves de config/hermatix_rules.yaml y de config/tarifario.yaml).
PRODUCTOS = {"fleetmatix": "FleetMatix", "fenova_ia": "Fenova IA", "passengeriq": "PassengerIQ", "moveon": "MoveOn",
             "smarttags": "SmartTags", "fleetrun": "FleetRun", "osmia_iot": "Osmia IoT", "bodycams": "BodyCams"}
PERIODOS = {"mensual": "por mes", "unico": "precio único"}
_CEDULA = re.compile(r"^[0-9][0-9 -]{7,18}[0-9]$")


class DatoInvalido(ValueError):
    """Un dato no sirve; el mensaje es el que ve la persona."""


@dataclass(frozen=True)
class Precio:
    moneda: str
    precio: str
    periodo: str
    iva: str
    desglose: dict
    por: str
    en: str

    def como_tarifa(self) -> dict:
        """En el formato de un producto de config/tarifario.yaml (lo que usa propuesta.economica)."""
        return {"moneda": self.moneda, "precio": self.precio, "periodo": self.periodo, "iva": self.iva,
                "desglose": self.desglose}


@dataclass(frozen=True)
class Archivo:
    id: int
    producto: str | None
    nombre: str
    ruta: str          # relativa a ASSISTANT_DOCS_DIR
    paginas: int | None
    por: str
    en: str

    @property
    def producto_nombre(self) -> str:
        return PRODUCTOS.get(self.producto or "", self.producto or "")


def _momento(ahora: datetime) -> str:
    return ahora.astimezone(HORA_CR).isoformat(timespec="seconds")


# --- Precio del cartel -----------------------------------------------------------------------------------------------

def precio(conn: sqlite3.Connection, nro_sicop: str) -> Precio | None:
    f = conn.execute("SELECT moneda, precio, periodo, iva, desglose_json, creado_por_nombre, creado_en"
                     " FROM oferta_precios WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1", (nro_sicop,)).fetchone()
    return Precio(f[0], f[1], f[2], f[3], json.loads(f[4]), f[5], f[6]) if f else None


def _numero(valor: str, campo: str) -> Decimal:
    try:
        return oferta_economica.decimal(valor, campo)
    except oferta_economica.OfertaError as exc:
        raise DatoInvalido(str(exc)) from None


def guardar_precio(conn: sqlite3.Connection, nro_sicop: str, *, moneda: str, precio_unitario: str, periodo: str,
                   iva_modo: str, iva_tasa: str, iva_exento: str, desglose: dict[str, str], quien: Quien,
                   ahora: datetime) -> Precio:
    """Revisa y guarda el precio del cartel. Lanza DatoInvalido con lo que está mal."""
    if moneda not in oferta_economica.MONEDAS:
        raise DatoInvalido("Elige la moneda: colones (CRC) o dólares (USD).")
    monto = _numero(precio_unitario, "el precio por unidad")
    if monto <= 0:
        raise DatoInvalido("El precio por unidad tiene que ser mayor que cero.")
    if periodo not in PERIODOS:
        raise DatoInvalido("Elige si el precio es por mes o un precio único.")
    if iva_modo == "exento":
        if not iva_exento.strip():
            raise DatoInvalido("Si está exento de IVA, escribe el motivo (p. ej. la ley que lo exonera).")
        iva = f"exento: {iva_exento.strip()}"
    else:
        tasa = _numero(iva_tasa, "la tasa de IVA")
        if not 0 <= tasa <= 100:
            raise DatoInvalido("La tasa de IVA va de 0 a 100.")
        iva = str(tasa)
    porcentajes = {clave: _numero(desglose.get(clave, ""), f"el porcentaje de «{clave.replace('_', ' ')}»")
                   for clave in oferta_economica.RUBROS}
    if any(p < 0 for p in porcentajes.values()) or sum(porcentajes.values()) != 100:
        raise DatoInvalido(f"Los cuatro porcentajes del desglose tienen que sumar 100 (suman "
                           f"{sum(porcentajes.values())}).")
    momento = _momento(ahora)
    with transaccion(conn):
        conn.execute("INSERT INTO oferta_precios (nro_sicop, moneda, precio, periodo, iva, desglose_json, creado_por,"
                     " creado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (nro_sicop, moneda, str(monto), periodo, iva,
                      json.dumps({k: str(v) for k, v in porcentajes.items()}), quien.user_id, quien.nombre, momento))
        historial.registrar(conn, quien, "guardar_precio_oferta", nro_sicop)   # sin montos
    return precio(conn, nro_sicop)


# --- Archivos (ficha técnica y pliego) -------------------------------------------------------------------------------

def _carpeta(base: Path, nro_sicop: str) -> Path:
    if not nro_sicop.isdigit():
        raise DatoInvalido("El Número SICOP solo lleva dígitos.")
    carpeta = base / nro_sicop / "oferta"
    if carpeta.resolve().parent.parent != base.resolve():   # nunca fuera de ASSISTANT_DOCS_DIR
        raise DatoInvalido("Número SICOP no válido.")
    return carpeta


def _recibir_pdf(base: Path, nro_sicop: str, origen: BinaryIO | None, nombre_original: str | None,
                 limite_mb: int, variable: str) -> tuple[str, Path, str, int]:
    """(nombre para mostrar, ruta final, sha256, tamaño) de un PDF subido. Lanza DatoInvalido o ArchivoInvalido."""
    nombre = archivos.nombre_para_mostrar(nombre_original)
    if origen is None or not nombre:
        raise DatoInvalido("Elige el archivo PDF.")
    if not nombre.lower().endswith(".pdf"):
        raise DatoInvalido(f"Se acepta solo PDF (se recibió «{nombre}»).")
    carpeta = _carpeta(base, nro_sicop)
    with archivos.recibir(origen, carpeta, limite_mb * 1024 * 1024,
                          f"El archivo supera el límite de {limite_mb} MB ({variable}).") as r:
        if not archivos.primeros_bytes(r.temporal).startswith(b"%PDF-"):
            raise ArchivoInvalido(f"El contenido de «{nombre}» no es un PDF de verdad.")
        destino = carpeta / f"{r.sha256}.pdf"
        os.replace(r.temporal, destino)
        return nombre, destino, r.sha256, r.tamano


def ficha(conn: sqlite3.Connection, nro_sicop: str) -> Archivo | None:
    f = conn.execute("SELECT id, producto, nombre_archivo, ruta, creado_por_nombre, creado_en FROM oferta_fichas"
                     " WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1", (nro_sicop,)).fetchone()
    return Archivo(f[0], f[1], f[2], f[3], None, f[4], f[5]) if f else None


def guardar_ficha(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, producto: str,
                  origen: BinaryIO | None, nombre_original: str | None, quien: Quien, ahora: datetime) -> Archivo:
    if producto not in PRODUCTOS:
        raise DatoInvalido("Elige el producto que se oferta.")
    nombre, destino, sha, tamano = _recibir_pdf(settings.assistant_docs_dir, nro_sicop, origen, nombre_original,
                                                settings.assistant_doc_max_mb, "ASSISTANT_DOC_MAX_MB")
    with transaccion(conn):
        conn.execute("INSERT INTO oferta_fichas (nro_sicop, producto, nombre_archivo, ruta, sha256, tamano, creado_por,"
                     " creado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (nro_sicop, producto, nombre, f"{nro_sicop}/oferta/{destino.name}", sha, tamano, quien.user_id,
                      quien.nombre, _momento(ahora)))
        historial.registrar(conn, quien, "subir_ficha_oferta", f"{nro_sicop}: {PRODUCTOS[producto]} · {nombre}")
    return ficha(conn, nro_sicop)


def pliego(conn: sqlite3.Connection, nro_sicop: str) -> Archivo | None:
    f = conn.execute("SELECT id, nombre_archivo, ruta, paginas, creado_por_nombre, creado_en FROM oferta_pliegos"
                     " WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1", (nro_sicop,)).fetchone()
    return Archivo(f[0], None, f[1], f[2], f[3], f[4], f[5]) if f else None


def paginas_pliego(conn: sqlite3.Connection, nro_sicop: str) -> list[tuple[str, int, str]]:
    """(nombre del archivo, página, texto) del pliego subido más nuevo; [] si no hay."""
    p = pliego(conn, nro_sicop)
    if p is None:
        return []
    return [(p.nombre, n, t) for n, t in conn.execute(
        "SELECT pagina, texto FROM oferta_pliego_texto WHERE pliego_id = ? ORDER BY pagina", (p.id,))]


def guardar_pliego(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, origen: BinaryIO | None,
                   nombre_original: str | None, quien: Quien, ahora: datetime) -> Archivo:
    """Guarda el PDF y su texto por página. Un PDF escaneado (sin texto) no sirve: se rechaza."""
    nombre, destino, sha, tamano = _recibir_pdf(settings.assistant_docs_dir, nro_sicop, origen, nombre_original,
                                                settings.document_max_mb, "DOCUMENT_MAX_MB")
    texto = sicop_documentos.extraer_texto(destino.read_bytes(), ".pdf")
    if texto.estado != "extraido":
        raise DatoInvalido(f"No se pudo sacar el texto de «{nombre}»: {texto.motivo or texto.estado}. Sin texto no "
                           "sirve para armar la oferta.")
    with transaccion(conn):
        pliego_id = conn.execute(
            "INSERT INTO oferta_pliegos (nro_sicop, nombre_archivo, ruta, sha256, tamano, paginas, creado_por,"
            " creado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nro_sicop, nombre, f"{nro_sicop}/oferta/{destino.name}", sha, tamano, texto.paginas, quien.user_id,
             quien.nombre, _momento(ahora))).lastrowid
        conn.executemany("INSERT INTO oferta_pliego_texto (pliego_id, pagina, texto) VALUES (?, ?, ?)",
                         [(pliego_id, pagina, t) for _, pagina, t in texto.filas])
        historial.registrar(conn, quien, "subir_pliego_oferta", f"{nro_sicop}: {nombre} ({texto.paginas} págs.)")
    return pliego(conn, nro_sicop)


# --- Representante legal (uno para todas las ofertas) ----------------------------------------------------------------

def representante(conn: sqlite3.Connection) -> dict | None:
    f = conn.execute("SELECT nombre, cedula, calidades, cargo, creado_por_nombre, creado_en FROM representante_legal"
                     " ORDER BY id DESC LIMIT 1").fetchone()
    return dict(zip(("nombre", "cedula", "calidades", "cargo", "por", "en"), f)) if f else None


def guardar_representante(conn: sqlite3.Connection, *, nombre: str, cedula: str, calidades: str, cargo: str,
                          quien: Quien, ahora: datetime) -> dict:
    """Solo administradores (lo revisa la ruta). La cédula queda como texto, tal como se escribe."""
    nombre, cedula = " ".join(nombre.split()), cedula.strip()
    if len(nombre) < 5:
        raise DatoInvalido("Escribe el nombre completo de quien firma la oferta.")
    if not _CEDULA.match(cedula):
        raise DatoInvalido("La cédula lleva solo números y guiones (p. ej. 1-1234-0567).")
    with transaccion(conn):
        conn.execute("INSERT INTO representante_legal (nombre, cedula, calidades, cargo, creado_por, creado_por_nombre,"
                     " creado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (nombre, cedula, " ".join(calidades.split()), " ".join(cargo.split()) or "representante legal",
                      quien.user_id, quien.nombre, _momento(ahora)))
        historial.registrar(conn, quien, "guardar_representante", "datos del representante legal")   # sin la cédula
    return representante(conn)
