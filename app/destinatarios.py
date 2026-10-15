"""Destinatarios de los avisos por correo (tabla notification_recipients, migración 0006).

Los edita un administrador desde el panel (pedido de Oscar): no están fijos en MAIL_TO. No se borran, se
desactivan, y cada cambio queda en el historial. Agregar a alguien no envía nada por sí solo.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from app import historial
from app.database import transaccion
from app.historial import TERMINAL, Quien
from app.usuarios import EMAIL


class DestinatarioInvalido(ValueError):
    """El mensaje es el que verá la persona."""


@dataclass
class Destinatario:
    id: int
    email: str
    nombre: str
    activo: bool
    creado: str


def listar(conn: sqlite3.Connection) -> list[Destinatario]:
    return [Destinatario(i, e, n, bool(a), c) for i, e, n, a, c in conn.execute(
        "SELECT id, email, nombre, active, created_at FROM notification_recipients ORDER BY active DESC, email")]


def activos(conn: sqlite3.Connection) -> list[Destinatario]:
    return [d for d in listar(conn) if d.activo]


def agregar(conn: sqlite3.Connection, email: str, nombre: str, quien: Quien = TERMINAL) -> int:
    email, nombre = email.strip(), nombre.strip()
    if not EMAIL.match(email) or len(email) > 254:
        raise DestinatarioInvalido("El correo no es válido.")
    if not nombre or len(nombre) > 100:
        raise DestinatarioInvalido("Escribe el nombre (hasta 100 caracteres).")
    fila = conn.execute("SELECT active FROM notification_recipients WHERE email = ?", (email,)).fetchone()
    if fila is not None:
        estado = "activo" if fila[0] else "desactivado: actívalo de nuevo en la lista"
        raise DestinatarioInvalido(f"{email} ya está en la lista ({estado}).")
    with transaccion(conn):  # el cambio y su línea del historial, juntos
        cursor = conn.execute(
            "INSERT INTO notification_recipients (email, nombre, active, created_at) VALUES (?, ?, 1, ?)",
            (email, nombre, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        historial.registrar(conn, quien, "agregar_destinatario", f"{nombre} <{email}>")
    return cursor.lastrowid


def cambiar_estado(conn: sqlite3.Connection, destinatario_id: int, activo: bool, quien: Quien = TERMINAL) -> bool:
    """Devuelve False si ya estaba así."""
    fila = conn.execute("SELECT email, nombre, active FROM notification_recipients WHERE id = ?",
                        (destinatario_id,)).fetchone()
    if fila is None:
        raise DestinatarioInvalido("Ese destinatario no existe.")
    if bool(fila[2]) == activo:
        return False
    with transaccion(conn):
        conn.execute("UPDATE notification_recipients SET active = ? WHERE id = ?", (int(activo), destinatario_id))
        historial.registrar(conn, quien, "activar_destinatario" if activo else "desactivar_destinatario",
                            f"{fila[1]} <{fila[0]}>")
    return True
