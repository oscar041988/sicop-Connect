"""Gestor de documentos, paso 1A: seguimiento de un cartel y su encargado (docs/GESTOR_DOCUMENTOS.md).

* Cualquier usuario con sesión da «Dar seguimiento» a un cartel; queda «sin encargado» hasta que un
  administrador lo asigne. Solo un administrador asigna o cambia el encargado (eso lo revisa la ruta).
* El expediente lo ven solo su encargado vigente y los administradores (puede_entrar). Los demás ven la marca
  «En seguimiento · <nombre>», pero no entran.
* El encargado vigente es la última asignación: cambiarlo agrega una fila y nunca borra la anterior, así queda
  el historial de traspasos. Cada cambio va también a audit_log.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app import historial, usuarios
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR


class SeguimientoInvalido(ValueError):
    """No se puede hacer el cambio; el mensaje es el que verá la persona."""


@dataclass(frozen=True)
class Estado:
    """El seguimiento de un cartel: quién lo abrió y quién es el encargado vigente (None = sin encargado)."""
    nro_sicop: str
    abierto_por: str
    abierto_en: str
    encargado_id: int | None
    encargado: str | None


@dataclass(frozen=True)
class Asignacion:
    encargado: str
    asignado_por: str
    fecha: str


@dataclass(frozen=True)
class Fila:
    """Un cartel de la página «Seguimiento»."""
    estado: Estado
    titulo: str | None
    institucion: str | None
    cierre: str | None


# Encargado vigente de cada seguimiento: su última asignación.
_ULTIMA = ("(SELECT a.{campo} FROM seguimiento_asignaciones a WHERE a.seguimiento_id = s.id"
           " ORDER BY a.id DESC LIMIT 1)")
_COLUMNAS_ESTADO = (f"s.nro_sicop, s.abierto_por_nombre, s.abierto_en, {_ULTIMA.format(campo='encargado_id')},"
                    f" {_ULTIMA.format(campo='encargado_nombre')}")


def _momento(ahora: datetime) -> str:
    return ahora.astimezone(HORA_CR).isoformat(timespec="seconds")


def _nombre_activo(conn: sqlite3.Connection, user_id: int | None) -> str:
    fila = conn.execute("SELECT coalesce(nombre, email) FROM users WHERE id = ? AND active = 1",
                        (user_id,)).fetchone()
    if fila is None:
        raise SeguimientoInvalido("Tu usuario no existe o está desactivado. Vuelve a iniciar sesión.")
    return fila[0]


def estado(conn: sqlite3.Connection, nro_sicop: str) -> Estado | None:
    fila = conn.execute(f"SELECT {_COLUMNAS_ESTADO} FROM seguimientos s WHERE s.nro_sicop = ?",
                        (nro_sicop,)).fetchone()
    return Estado(*fila) if fila else None


def de_carteles(conn: sqlite3.Connection, nros: list[str]) -> dict[str, Estado]:
    """El seguimiento de cada cartel de una lista (los que no tienen, no aparecen). Para la marca del panel."""
    resultado: dict[str, Estado] = {}
    unicos = list(dict.fromkeys(nros))
    for inicio in range(0, len(unicos), 900):  # por tandas: SQLite limita los parámetros de una consulta
        tanda = unicos[inicio:inicio + 900]
        for fila in conn.execute(f"SELECT {_COLUMNAS_ESTADO} FROM seguimientos s"
                                 f" WHERE s.nro_sicop IN ({', '.join('?' * len(tanda))})", tanda):
            resultado[fila[0]] = Estado(*fila)
    return resultado


def abrir(conn: sqlite3.Connection, nro_sicop: str, quien: Quien, ahora: datetime) -> bool:
    """Pone el cartel en seguimiento, sin encargado. Devuelve False si ya estaba (no se duplica)."""
    nombre = _nombre_activo(conn, quien.user_id)
    if conn.execute("SELECT 1 FROM tenders WHERE nro_sicop = ?", (nro_sicop,)).fetchone() is None:
        raise SeguimientoInvalido(f"No existe el cartel {nro_sicop}.")
    with transaccion(conn):  # el seguimiento y su línea del historial, juntos
        cursor = conn.execute(
            "INSERT OR IGNORE INTO seguimientos (nro_sicop, abierto_por, abierto_por_nombre, abierto_en)"
            " VALUES (?, ?, ?, ?)", (nro_sicop, quien.user_id, nombre, _momento(ahora)))
        if cursor.rowcount:
            historial.registrar(conn, quien, "abrir_seguimiento", nro_sicop)
    return bool(cursor.rowcount)


def asignar(conn: sqlite3.Connection, nro_sicop: str, encargado_id: int, quien: Quien, ahora: datetime) -> bool:
    """Asigna o cambia el encargado. Devuelve False si ya era el encargado vigente (no se cambia nada).
    Que quien asigna sea administrador lo revisa la ruta (exigir_admin)."""
    nombre_quien = _nombre_activo(conn, quien.user_id)
    actual = estado(conn, nro_sicop)
    if actual is None:
        raise SeguimientoInvalido(f"El cartel {nro_sicop} no está en seguimiento: primero «Dar seguimiento».")
    try:
        encargado = usuarios.obtener(conn, encargado_id)
    except usuarios.UsuarioInvalido as exc:
        raise SeguimientoInvalido("Elige un encargado de la lista.") from exc
    if not encargado.activo:
        raise SeguimientoInvalido(f"{encargado.nombre} está desactivado: no se le puede asignar un cartel.")
    if actual.encargado_id == encargado.id:
        return False
    with transaccion(conn):  # la asignación y su línea del historial, juntas
        conn.execute(
            "INSERT INTO seguimiento_asignaciones (seguimiento_id, encargado_id, encargado_nombre, asignado_por,"
            " asignado_por_nombre, created_at)"
            " SELECT id, ?, ?, ?, ?, ? FROM seguimientos WHERE nro_sicop = ?",
            (encargado.id, encargado.nombre, quien.user_id, nombre_quien, _momento(ahora), nro_sicop))
        antes = actual.encargado or "sin encargado"
        historial.registrar(conn, quien, "asignar_encargado", f"{nro_sicop}: {antes} → {encargado.nombre}")
    return True


def historial_de(conn: sqlite3.Connection, nro_sicop: str) -> list[Asignacion]:
    """Las asignaciones del cartel, de la más reciente a la más vieja."""
    return [Asignacion(*fila) for fila in conn.execute(
        "SELECT a.encargado_nombre, a.asignado_por_nombre, a.created_at FROM seguimiento_asignaciones a"
        " JOIN seguimientos s ON s.id = a.seguimiento_id WHERE s.nro_sicop = ? ORDER BY a.id DESC",
        (nro_sicop,))]


def listar(conn: sqlite3.Connection) -> list[Fila]:
    """Todos los carteles en seguimiento: primero los sin encargado, después por cierre más próximo."""
    filas = conn.execute(
        f"SELECT {_COLUMNAS_ESTADO}, t.descripcion, i.nombre, t.fecha_cierre_recepcion FROM seguimientos s"
        " JOIN tenders t ON t.nro_sicop = s.nro_sicop LEFT JOIN institutions i ON i.cedula = t.institution_cedula"
        " ORDER BY t.fecha_cierre_recepcion IS NULL, t.fecha_cierre_recepcion, s.nro_sicop").fetchall()
    lista = [Fila(Estado(*f[:5]), *f[5:]) for f in filas]
    return sorted(lista, key=lambda f: f.estado.encargado_id is not None)  # sorted es estable: conserva el orden


def puede_entrar(usuario: dict | None, actual: Estado | None) -> bool:
    """La regla de acceso al expediente: un administrador, o el encargado vigente."""
    if usuario is None or actual is None:
        return False
    return usuario.get("rol") == usuarios.ADMIN or usuario.get("id") == actual.encargado_id


def asignables(conn: sqlite3.Connection) -> list[usuarios.Usuario]:
    """Usuarios activos, para el formulario del administrador."""
    return [u for u in usuarios.listar(conn) if u.activo]
