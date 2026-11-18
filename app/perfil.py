"""Perfil de Hermatix (asistente de elegibilidad, lección 1; migración 0029).

* Un ELEMENTO es un dato o documento de la empresa que los carteles suelen pedir (tipo + título). Cada carga o
  reemplazo agrega una VERSIÓN; la vigente es la última. Nada se borra ni se modifica (triggers).
* El estado se calcula con la fecha de hoy: pendiente · vencido · por vencer (≤ AVISO_DIAS) · vigente.
* Documentos: solo PDF, PNG y JPG, con su firma comprobada, en PROFILE_DOCS_DIR/<id>/<sha256>.<ext>, fuera de Git.
  Son confidenciales: cada vista o descarga queda en audit_log (registrar_acceso).
* Lo ven los dos niveles; crear, reemplazar y marcar lo revisan las rutas (solo administradores).
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import BinaryIO

import yaml

from app import archivos, historial, visor
from app.archivos import ArchivoInvalido
from app.config import PROJECT_ROOT
from app.database import transaccion
from app.historial import Evento, Quien
from app.importers.comun import HORA_CR

TIPOS = {"experiencia": "Experiencia", "personal": "Personal", "certificacion": "Certificación", "permiso": "Permiso",
         "poliza": "Póliza", "legal": "Legal", "financiero": "Financiero",
         # Migración 0035 (2026-11-04): soporte, taller, garantía y marcas; lo que da puntos en la evaluación.
         "capacidad": "Capacidad", "evaluacion": "Evaluación"}
ESTADOS = {"vigente": "Vigente", "por_vencer": "Por vencer", "vencido": "Vencido", "pendiente": "Pendiente"}
AVISO_DIAS = 30   # aviso de vencimiento (la guía dice 30 días; falta que Oscar lo confirme)
EXTENSIONES = {".pdf": ".pdf", ".png": ".png", ".jpg": ".jpg", ".jpeg": ".jpg"}
FIRMAS = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff"}
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}
NOMBRES = {".pdf": "PDF", ".png": "PNG", ".jpg": "JPG"}
SUGERENCIAS = PROJECT_ROOT / "config" / "perfil.yaml"
LARGO_TITULO = 150
LARGO_TEXTO = 1000


class PerfilInvalido(ValueError):
    """Un dato del perfil no se acepta; el mensaje es el que verá la persona."""


@dataclass(frozen=True)
class Datos:
    """Lo que se escribe en el formulario de una versión (todo opcional; se valida en limpiar)."""
    valor: str = ""
    numero: str = ""
    unidad: str = ""
    vigente_desde: str = ""
    vence_el: str = ""
    nota: str = ""


@dataclass(frozen=True)
class Version:
    id: int
    item_id: int
    valor: str | None
    numero: str | None
    unidad: str | None
    vigente_desde: str | None
    vence_el: str | None
    pendiente: bool
    nota: str | None
    archivo_nombre: str | None
    archivo_extension: str | None
    archivo_tamano: int | None
    cargado_por: str
    fecha: str

    @property
    def tiene_archivo(self) -> bool:
        return self.archivo_extension is not None

    @property
    def vista(self) -> str | None:
        """'pdf' o 'imagen': se puede «Ver» en el navegador (app/visor.py)."""
        return visor.vista(f"x{self.archivo_extension}") if self.archivo_extension else None


@dataclass(frozen=True)
class Elemento:
    id: int
    tipo: str
    titulo: str
    vigente: Version | None
    estado: str
    dias: int | None          # días hasta el vencimiento (negativo: ya venció)

    @property
    def tipo_texto(self) -> str:
        return TIPOS[self.tipo]

    @property
    def estado_texto(self) -> str:
        return ESTADOS[self.estado]


# --- Lectura -------------------------------------------------------------------------------------------------------

_VERSION = ("SELECT id, item_id, valor, numero, unidad, vigente_desde, vence_el, pendiente, nota, archivo_nombre,"
            " archivo_extension, archivo_tamano, cargado_por_nombre, created_at FROM company_profile_versions")


def _version(fila) -> Version:
    return Version(*fila[:7], bool(fila[7]), *fila[8:])


def hoy() -> date:
    return datetime.now(HORA_CR).date()


def dia(iso: str | None) -> str:
    """«2027-01-15» → «15/01/2027» (filtro de las plantillas)."""
    if not iso:
        return "—"
    try:
        return date.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def estado_de(v: Version | None, dia: date) -> tuple[str, int | None]:
    if v is None or v.pendiente:
        return "pendiente", None
    if not v.vence_el:
        return "vigente", None
    dias = (date.fromisoformat(v.vence_el) - dia).days
    if dias < 0:
        return "vencido", dias
    return ("por_vencer" if dias <= AVISO_DIAS else "vigente"), dias


def _elemento(conn: sqlite3.Connection, fila, dia: date) -> Elemento:
    item_id, tipo, titulo = fila
    ultima = conn.execute(f"{_VERSION} WHERE item_id = ? ORDER BY id DESC LIMIT 1", (item_id,)).fetchone()
    vigente = _version(ultima) if ultima else None
    return Elemento(item_id, tipo, titulo, vigente, *estado_de(vigente, dia))


def listar(conn: sqlite3.Connection, dia: date | None = None) -> list[Elemento]:
    """Todos los elementos, en el orden de TIPOS y luego por título."""
    dia = dia or hoy()
    orden = {t: n for n, t in enumerate(TIPOS)}
    elementos = [_elemento(conn, f, dia) for f in conn.execute("SELECT id, tipo, titulo FROM company_profile_items")]
    return sorted(elementos, key=lambda e: (orden[e.tipo], e.titulo.lower()))


def obtener(conn: sqlite3.Connection, item_id: int, dia: date | None = None) -> Elemento | None:
    fila = conn.execute("SELECT id, tipo, titulo FROM company_profile_items WHERE id = ?", (item_id,)).fetchone()
    return _elemento(conn, fila, dia or hoy()) if fila else None


def versiones(conn: sqlite3.Connection, item_id: int) -> list[Version]:
    """El historial del elemento, de la versión más nueva a la más vieja."""
    return [_version(f) for f in conn.execute(f"{_VERSION} WHERE item_id = ? ORDER BY id DESC", (item_id,))]


def _eventos(conn: sqlite3.Connection, item_id: int, acciones: tuple[str, ...]) -> list[Evento]:
    marcas = ", ".join("?" for _ in acciones)
    return [Evento(*f) for f in conn.execute(
        f"SELECT actor, accion, detalle, created_at FROM audit_log WHERE accion IN ({marcas}) AND detalle LIKE ?"
        " ORDER BY id DESC LIMIT 100", (*acciones, f"#{item_id} %"))]


def cambios(conn: sqlite3.Connection, item_id: int) -> list[Evento]:
    return _eventos(conn, item_id, historial.DE_PERFIL)


def accesos(conn: sqlite3.Connection, item_id: int) -> list[Evento]:
    """Quién vio o descargó los documentos del elemento (los últimos 100)."""
    return _eventos(conn, item_id, historial.ACCESOS_PERFIL)


def sugerencias(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Los elementos de config/perfil.yaml que todavía no existen, por tipo."""
    datos = yaml.safe_load(SUGERENCIAS.read_text(encoding="utf-8")) or {}
    existentes = {(t, x.casefold()) for t, x in conn.execute("SELECT tipo, titulo FROM company_profile_items")}
    resultado: dict[str, list[str]] = {}
    for tipo in TIPOS:
        faltan = [x for x in (datos.get("sugerencias") or {}).get(tipo) or [] if (tipo, x.casefold()) not in existentes]
        if faltan:
            resultado[tipo] = faltan
    return resultado


# --- Escritura -----------------------------------------------------------------------------------------------------

def _fecha(texto: str, campo: str) -> str | None:
    texto = texto.strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        raise PerfilInvalido(f"«{campo}» no es una fecha válida (AAAA-MM-DD).") from None


def _limpiar(d: Datos) -> dict:
    numero = d.numero.strip().replace(" ", "")
    if numero:
        try:
            numero = str(Decimal(numero.replace(",", ".")))
        except InvalidOperation:
            raise PerfilInvalido(f"«{d.numero}» no es un número (por ejemplo 8 o 2500000.00).") from None
    limpio = {"valor": d.valor.strip()[:LARGO_TEXTO] or None, "numero": numero or None,
              "unidad": d.unidad.strip()[:40] or None, "vigente_desde": _fecha(d.vigente_desde, "Vigente desde"),
              "vence_el": _fecha(d.vence_el, "Vence el"), "nota": d.nota.strip()[:LARGO_TEXTO] or None}
    if limpio["vence_el"] and limpio["vigente_desde"] and limpio["vence_el"] < limpio["vigente_desde"]:
        raise PerfilInvalido("«Vence el» no puede ser antes de «Vigente desde».")
    return limpio


def validar(d: Datos) -> None:
    """Revisa fechas y número sin guardar nada (lanza PerfilInvalido)."""
    _limpiar(d)


def guardar_documento(base: Path, carpeta: str, origen: BinaryIO, nombre_original: str | None, limite: int,
                      donde: str = "En el perfil", variable: str = "PROFILE_DOC_MAX_MB") -> dict:
    """Valida (PDF/PNG/JPG con su firma, tamaño) y guarda en base/carpeta/<sha256>.<ext>. También lo usa el
    asistente de elegibilidad (app/asistente.py) para los archivos de sus respuestas."""
    nombre = archivos.nombre_para_mostrar(nombre_original)
    extension = EXTENSIONES.get(PurePosixPath(nombre).suffix.lower())
    if extension is None:
        raise ArchivoInvalido(f"{donde} se aceptan solo PDF e imágenes PNG o JPG.")
    destino_dir = base / carpeta
    aviso = f"El archivo supera el límite de {limite // (1024 * 1024)} MB ({variable})."
    with archivos.recibir(origen, destino_dir, limite, aviso) as r:
        if not archivos.primeros_bytes(r.temporal).startswith(FIRMAS[extension]):
            raise ArchivoInvalido(f"El contenido de «{nombre}» no es un {NOMBRES[extension]} de verdad: no coincide"
                                  " con su extensión.")
        destino = destino_dir / f"{r.sha256}{extension}"
        os.replace(r.temporal, destino)
    return {"archivo_nombre": nombre, "archivo_extension": extension, "archivo_tamano": r.tamano,
            "archivo_sha256": r.sha256, "archivo_ruta": f"{carpeta}/{destino.name}"}


def _insertar_version(conn: sqlite3.Connection, item_id: int, campos: dict, quien: Quien, momento: str) -> int:
    campos = {**campos, "item_id": item_id, "cargado_por": quien.user_id, "cargado_por_nombre": quien.nombre,
              "created_at": momento}
    columnas = ", ".join(campos)
    return conn.execute(f"INSERT INTO company_profile_versions ({columnas}) VALUES ({', '.join('?' for _ in campos)})",
                        tuple(campos.values())).lastrowid


def crear(conn: sqlite3.Connection, tipo: str, titulo: str, quien: Quien, ahora: datetime) -> int:
    """Agrega un elemento sin datos todavía (queda «pendiente» hasta su primera versión)."""
    titulo = " ".join(titulo.split())[:LARGO_TITULO]
    if tipo not in TIPOS:
        raise PerfilInvalido("Elige el tipo del elemento.")
    if not titulo:
        raise PerfilInvalido("Escribe el título del elemento.")
    # En Python y no con lower() de SQLite, que no pasa a minúscula las letras con tilde («PÓLIZA»).
    if any(t.casefold() == titulo.casefold()
           for (t,) in conn.execute("SELECT titulo FROM company_profile_items WHERE tipo = ?", (tipo,))):
        raise PerfilInvalido(f"Ya existe «{titulo}» en {TIPOS[tipo]}.")
    momento = ahora.astimezone(HORA_CR).isoformat(timespec="seconds")
    with transaccion(conn):
        item_id = conn.execute("INSERT INTO company_profile_items (tipo, titulo, creado_por, creado_por_nombre,"
                               " created_at) VALUES (?, ?, ?, ?, ?)",
                               (tipo, titulo, quien.user_id, quien.nombre, momento)).lastrowid
        historial.registrar(conn, quien, "crear_elemento_perfil", f"#{item_id} {TIPOS[tipo]}: {titulo}")
    return item_id


def nueva_version(conn: sqlite3.Connection, base: Path, item_id: int, datos: Datos,
                  archivo: tuple[BinaryIO, str | None] | None, limite: int, quien: Quien, ahora: datetime) -> int:
    """Carga o reemplaza los datos del elemento (con o sin documento). La versión anterior queda en el historial."""
    elemento = obtener(conn, item_id)
    if elemento is None:
        raise PerfilInvalido("Ese elemento del perfil no existe.")
    campos = _limpiar(datos)
    if archivo is not None:
        campos.update(guardar_documento(base, str(item_id), archivo[0], archivo[1], limite))
    if not (campos["valor"] or campos["numero"] or archivo is not None):
        raise PerfilInvalido("Escribe un valor, un número o sube un documento. Si todavía no lo tienes, márcalo"
                             " pendiente.")
    momento = ahora.astimezone(HORA_CR).isoformat(timespec="seconds")
    with transaccion(conn):
        version_id = _insertar_version(conn, item_id, campos, quien, momento)
        documento = f" con «{campos['archivo_nombre']}»" if archivo is not None else ""
        historial.registrar(conn, quien, "nueva_version_perfil",
                            f"#{item_id} {elemento.titulo}: versión #{version_id}{documento}")
    return version_id


def marcar_pendiente(conn: sqlite3.Connection, item_id: int, nota: str, quien: Quien, ahora: datetime) -> int:
    """Una versión «pendiente»: todavía no se tiene el dato o el documento (o hay que renovarlo)."""
    elemento = obtener(conn, item_id)
    if elemento is None:
        raise PerfilInvalido("Ese elemento del perfil no existe.")
    momento = ahora.astimezone(HORA_CR).isoformat(timespec="seconds")
    with transaccion(conn):
        version_id = _insertar_version(conn, item_id, {"pendiente": 1, "nota": nota.strip()[:LARGO_TEXTO] or None},
                                       quien, momento)
        historial.registrar(conn, quien, "marcar_pendiente_perfil", f"#{item_id} {elemento.titulo}")
    return version_id


# --- Documentos: ruta segura y registro de cada acceso -------------------------------------------------------------

def documento(conn: sqlite3.Connection, base: Path, item_id: int, version_id: int) -> tuple[Path, Version] | None:
    """La ruta en disco y los datos del documento de ESA versión de ESE elemento, o None."""
    fila = conn.execute(f"{_VERSION.replace('FROM', ', archivo_ruta FROM')} WHERE id = ? AND item_id = ?",
                        (version_id, item_id)).fetchone()
    if fila is None or fila[-1] is None:
        return None
    ruta = base / fila[-1]
    if ruta.resolve().parent != (base / str(item_id)).resolve() or not ruta.is_file():
        return None
    return ruta, _version(fila[:-1])


def registrar_acceso(conn: sqlite3.Connection, quien: Quien, accion: str, item_id: int, titulo: str,
                     v: Version) -> None:
    with transaccion(conn):
        historial.registrar(conn, quien, accion, f"#{item_id} {titulo}: «{v.archivo_nombre}» (versión #{v.id})")
