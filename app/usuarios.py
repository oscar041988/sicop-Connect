"""Usuarios del panel: contraseñas con hash Argon2 (biblioteca argon2-cffi) en la tabla users (migración 0001).

La contraseña nunca se guarda, ni se imprime, ni se registra: solo su hash.

Niveles de acceso (aprobados por Oscar, 2026-10-12), en la columna users.role:
- encargado: ver oportunidades, guardar revisiones y subir archivos de SICOP.
- admin: lo mismo, más gestionar usuarios y (lección 7) los destinatarios de los avisos.
Cada cambio de administración queda en el historial (app/historial.py).
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app import historial
from app.database import transaccion
from app.historial import TERMINAL, Quien

# 10 (antes 12): pedido de Hermatix, 2026-10-12, a cambio de sugerir frases de varias palabras.
MIN_CONTRASENA = 10
CONSEJO_CONTRASENA = "usa 3 o 4 palabras, por ejemplo «cafe verde lunes»: es larga y fácil de recordar"
MAX_CONTRASENA = 128  # tope para que una contraseña enorme no ocupe al servidor calculando el hash
ADMIN, ENCARGADO = "admin", "encargado"
NIVELES = {ADMIN: "Administrador", ENCARGADO: "Encargado"}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_hasher = PasswordHasher()  # parámetros recomendados por la biblioteca (Argon2id)


class UsuarioInvalido(Exception):
    """Los datos del usuario no cumplen las reglas, o el cambio no está permitido."""


@dataclass
class Usuario:
    id: int
    email: str
    nombre: str
    rol: str
    activo: bool
    creado: str


@lru_cache(maxsize=1)
def _hash_de_relleno() -> str:
    # Si el correo no existe se verifica contra este hash, para que la respuesta tarde lo mismo
    # y no delate qué correos tienen cuenta.
    return _hasher.hash("contraseña de relleno que no es de nadie")


def validar_contrasena(contrasena: str) -> None:
    if len(contrasena) < MIN_CONTRASENA:
        raise UsuarioInvalido(f"La contraseña debe tener al menos {MIN_CONTRASENA} caracteres. Consejo: "
                              f"{CONSEJO_CONTRASENA}.")
    if len(contrasena) > MAX_CONTRASENA:
        raise UsuarioInvalido(f"La contraseña admite como máximo {MAX_CONTRASENA} caracteres.")


def _validar_nivel(rol: str) -> None:
    if rol not in NIVELES:
        raise UsuarioInvalido("El nivel debe ser Administrador o Encargado.")


def crear_usuario(conn: sqlite3.Connection, email: str, nombre: str, contrasena: str, rol: str = ENCARGADO,
                  quien: Quien = TERMINAL) -> int:
    email, nombre = email.strip(), nombre.strip()
    if not EMAIL.match(email):
        raise UsuarioInvalido("El correo no es válido.")
    if not nombre:
        raise UsuarioInvalido("Falta el nombre.")
    if len(nombre) > 100:
        raise UsuarioInvalido("El nombre admite hasta 100 caracteres.")
    _validar_nivel(rol)
    validar_contrasena(contrasena)
    if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise UsuarioInvalido(f"Ya existe un usuario con el correo {email}.")
    with transaccion(conn):  # el cambio y su línea del historial, juntos
        cursor = conn.execute(
            "INSERT INTO users (email, nombre, role, password_hash, active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (email, nombre, rol, _hasher.hash(contrasena), datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        historial.registrar(conn, quien, "crear_usuario", f"{email} ({NIVELES[rol]})")
    return cursor.lastrowid


def autenticar(conn: sqlite3.Connection, email: str, contrasena: str) -> tuple[int, str, str] | None:
    """Devuelve (id, nombre, huella) si el correo y la contraseña son correctos y el usuario está activo; si no, None."""
    if not contrasena or len(contrasena) > MAX_CONTRASENA:
        return None
    fila = conn.execute("SELECT id, nombre, email, password_hash, active FROM users WHERE email = ?",
                        (email.strip(),)).fetchone()
    try:
        _hasher.verify(fila[3] if fila else _hash_de_relleno(), contrasena)
    except (VerificationError, InvalidHashError):
        return None
    if fila is None or not fila[4]:
        return None
    return fila[0], fila[1] or fila[2], huella(fila[3])


def huella(password_hash: str) -> str:
    """Resumen corto del hash que se guarda en la sesión: si la contraseña cambia, la huella ya no coincide.

    Es un resumen del hash (que ya tiene sal), no de la contraseña: no sirve para adivinarla.
    """
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def sesion_vigente(conn: sqlite3.Connection, user_id: int, huella_de_sesion: str | None) -> str | None:
    """Nivel actual del usuario si su sesión sigue valiendo (existe, está activo y no cambió su contraseña
    desde que entró); None si ya no vale. Se lee en cada petición: un cambio de nivel aplica en el siguiente clic."""
    fila = conn.execute("SELECT password_hash, active, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if (fila is None or not fila[1] or huella_de_sesion is None
            or not hmac.compare_digest(huella(fila[0]), huella_de_sesion)):
        return None
    return fila[2]


def buscar_id(conn: sqlite3.Connection, email: str) -> int:
    fila = conn.execute("SELECT id FROM users WHERE email = ?", (email.strip(),)).fetchone()
    if fila is None:
        raise UsuarioInvalido(f"No hay un usuario con el correo {email.strip()}.")
    return fila[0]


def obtener(conn: sqlite3.Connection, user_id: int) -> Usuario:
    """El usuario vigente con ese id. Uno dado de baja (eliminar) ya no se puede cambiar: UsuarioInvalido."""
    fila = conn.execute("SELECT id, email, nombre, role, active, created_at, eliminado_en FROM users WHERE id = ?",
                        (user_id,)).fetchone()
    if fila is None:
        raise UsuarioInvalido("Ese usuario no existe.")
    if fila[6] is not None:
        raise UsuarioInvalido(f"{fila[2] or 'Ese usuario'} fue eliminado: ya no se puede cambiar.")
    return Usuario(fila[0], fila[1], fila[2] or fila[1], fila[3], bool(fila[4]), fila[5])


def _quedaria_sin_admin(conn: sqlite3.Connection, usuario: Usuario) -> bool:
    """True si el usuario es el único administrador activo."""
    if usuario.rol != ADMIN or not usuario.activo:
        return False
    return conn.execute("SELECT count(*) FROM users WHERE role = ? AND active = 1", (ADMIN,)).fetchone()[0] <= 1


def cambiar_contrasena(conn: sqlite3.Connection, user_id: int, contrasena: str, quien: Quien = TERMINAL) -> str:
    """Pone una contraseña nueva; las sesiones abiertas de ese usuario dejan de valer. Devuelve la huella nueva."""
    validar_contrasena(contrasena)
    usuario = obtener(conn, user_id)
    nuevo_hash = _hasher.hash(contrasena)
    with transaccion(conn):  # el cambio y su línea del historial, juntos
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (nuevo_hash, user_id))
        historial.registrar(conn, quien, "cambiar_contrasena", usuario.email)
    return huella(nuevo_hash)


def cambiar_estado(conn: sqlite3.Connection, user_id: int, activo: bool, quien: Quien = TERMINAL) -> bool:
    """Activa o desactiva (nunca borra: sus revisiones lo siguen nombrando). Devuelve False si ya estaba así."""
    usuario = obtener(conn, user_id)
    if usuario.activo == activo:
        return False
    if not activo:
        if quien.user_id == user_id:
            raise UsuarioInvalido("No puedes desactivarte a ti misma o a ti mismo.")
        if _quedaria_sin_admin(conn, usuario):
            raise UsuarioInvalido("Debe quedar al menos un administrador activo.")
    with transaccion(conn):  # el cambio y su línea del historial, juntos
        conn.execute("UPDATE users SET active = ? WHERE id = ?", (int(activo), user_id))
        historial.registrar(conn, quien, "activar" if activo else "desactivar", usuario.email)
    return True


def cambiar_nivel(conn: sqlite3.Connection, user_id: int, rol: str, quien: Quien = TERMINAL) -> bool:
    """Cambia el nivel de acceso. Devuelve False si ya tenía ese nivel."""
    _validar_nivel(rol)
    usuario = obtener(conn, user_id)
    if usuario.rol == rol:
        return False
    if rol != ADMIN:
        if quien.user_id == user_id:
            raise UsuarioInvalido("No puedes quitarte a ti misma o a ti mismo el nivel de administrador.")
        if _quedaria_sin_admin(conn, usuario):
            raise UsuarioInvalido("Debe quedar al menos un administrador activo.")
    with transaccion(conn):  # el cambio y su línea del historial, juntos
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (rol, user_id))
        historial.registrar(conn, quien, "cambiar_nivel",
                            f"{usuario.email}: {NIVELES[usuario.rol]} → {NIVELES[rol]}")
    return True


def expedientes_a_cargo(conn: sqlite3.Connection, user_id: int) -> list[str]:
    """N.º SICOP de los carteles en seguimiento cuyo encargado vigente (la última asignación) es este usuario."""
    return [nro for (nro,) in conn.execute(
        "SELECT s.nro_sicop FROM seguimientos s WHERE (SELECT a.encargado_id FROM seguimiento_asignaciones a"
        " WHERE a.seguimiento_id = s.id ORDER BY a.id DESC LIMIT 1) = ? ORDER BY s.nro_sicop", (user_id,))]


def eliminar(conn: sqlite3.Connection, user_id: int, quien: Quien = TERMINAL) -> str:
    """Baja definitiva (migración 0016; decisión de Ivania, 2026-10-26), p. ej. cuando alguien deja la empresa.

    No borra la fila: sus revisiones, seguimientos e historial lo siguen nombrando. Lo desactiva, cambia su
    contraseña por una que no es de nadie (sus sesiones abiertas se cierran) y libera su correo para otra cuenta.
    No se deshace: un trigger impide modificarlo después. Devuelve el nombre del usuario eliminado.
    """
    usuario = obtener(conn, user_id)
    if quien.user_id == user_id:
        raise UsuarioInvalido("No puedes eliminarte a ti misma o a ti mismo.")
    if _quedaria_sin_admin(conn, usuario):
        raise UsuarioInvalido("Debe quedar al menos un administrador activo.")
    if expedientes := expedientes_a_cargo(conn, user_id):
        raise UsuarioInvalido(f"{usuario.nombre} es encargado de {len(expedientes)} expediente(s) en seguimiento "
                              f"({', '.join(expedientes)}). Asigna otro encargado en «Seguimiento» y vuelve a intentarlo.")
    if conn.execute("SELECT 1 FROM notification_recipients WHERE email = ? AND active = 1",
                    (usuario.email,)).fetchone():
        raise UsuarioInvalido(f"El correo {usuario.email} sigue recibiendo los avisos: quítalo primero en "
                              "«Destinatarios».")
    with transaccion(conn):  # la baja y su línea del historial, juntas
        conn.execute(
            "UPDATE users SET active = 0, email = ?, password_hash = ?, eliminado_en = ? WHERE id = ?",
            (f"eliminado-{user_id}@baja.invalid", _hasher.hash(secrets.token_urlsafe(32)),
             datetime.now(timezone.utc).isoformat(timespec="seconds"), user_id))
        historial.registrar(conn, quien, "eliminar_usuario", f"{usuario.nombre} ({usuario.email})")
    return usuario.nombre


def listar(conn: sqlite3.Connection) -> list[Usuario]:
    """Los usuarios vigentes (sin los eliminados), nunca el hash."""
    return [Usuario(i, e, n or e, r, bool(a), c) for i, e, n, r, a, c in conn.execute(
        "SELECT id, email, nombre, role, active, created_at FROM users WHERE eliminado_en IS NULL ORDER BY email")]
