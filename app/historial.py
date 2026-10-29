"""Historial de cambios de administración (tabla audit_log, migración 0005): quién cambió qué y cuándo.
Hoy: usuarios, destinatarios de los avisos, avisos revisados a mano y seguimiento de carteles.

No se borra ni se modifica (triggers). Nunca guarda contraseñas ni hashes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

ACCIONES = {
    "crear_usuario": "Creó un usuario",
    "cambiar_nivel": "Cambió un nivel",
    "activar": "Activó un usuario",
    "desactivar": "Desactivó un usuario",
    "cambiar_contrasena": "Puso una contraseña nueva",
    "eliminar_usuario": "Eliminó un usuario",
    "agregar_destinatario": "Agregó un destinatario de avisos",
    "activar_destinatario": "Volvió a activar un destinatario",
    "desactivar_destinatario": "Quitó un destinatario de avisos",
    "reintentar_aviso": "Volvió a preparar un aviso",
    "confirmar_aviso": "Confirmó que un aviso sí salió",
    "abrir_seguimiento": "Dio seguimiento a un cartel",
    "asignar_encargado": "Asignó el encargado de un cartel",
    "cambiar_etapa": "Cambió la etapa de un cartel en seguimiento",
}
DE_USUARIOS = ("crear_usuario", "cambiar_nivel", "activar", "desactivar", "cambiar_contrasena", "eliminar_usuario")
DE_DESTINATARIOS = ("agregar_destinatario", "activar_destinatario", "desactivar_destinatario")
DE_AVISOS = ("reintentar_aviso", "confirmar_aviso")
DE_SEGUIMIENTO = ("abrir_seguimiento", "asignar_encargado", "cambiar_etapa")


@dataclass(frozen=True)
class Quien:
    """Quién hace el cambio: un administrador desde el panel o la terminal (user_id None)."""
    user_id: int | None
    nombre: str


TERMINAL = Quien(None, "terminal")


@dataclass
class Evento:
    actor: str
    accion: str
    detalle: str
    fecha: str


def registrar(conn: sqlite3.Connection, quien: Quien, accion: str, detalle: str) -> None:
    if accion not in ACCIONES:
        raise ValueError(f"Acción desconocida para el historial: {accion}")
    conn.execute("INSERT INTO audit_log (user_id, actor, accion, detalle, created_at) VALUES (?, ?, ?, ?, ?)",
                 (quien.user_id, quien.nombre, accion, detalle,
                  datetime.now(timezone.utc).isoformat(timespec="seconds")))


def ultimos(conn: sqlite3.Connection, acciones: tuple[str, ...], limite: int = 50) -> list[Evento]:
    """Los cambios más recientes de esas acciones (p. ej. DE_USUARIOS), del más nuevo al más viejo."""
    marcas = ", ".join("?" for _ in acciones)
    return [Evento(*fila) for fila in conn.execute(
        f"SELECT actor, accion, detalle, created_at FROM audit_log WHERE accion IN ({marcas}) ORDER BY id DESC LIMIT ?",
        (*acciones, limite))]
