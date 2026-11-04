"""«¿Te sirvió esta ayuda?» (Página de ayuda, lección 4): votos por misión y el resumen para los administradores."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from app.historial import Quien

MAX_COMENTARIO = 500


class VotoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class Resumen:
    mision: str
    si: int
    no: int
    ultimo_comentario: str     # el comentario más reciente que no esté vacío ('' si no hay)


def votar(conn: sqlite3.Connection, mision: str, util: str, comentario: str, quien: Quien, ahora: datetime) -> None:
    if util not in ("si", "no"):
        raise VotoInvalido("Elige «Sí» o «No».")
    comentario = comentario.strip()
    if len(comentario) > MAX_COMENTARIO:
        raise VotoInvalido(f"El comentario puede tener hasta {MAX_COMENTARIO} caracteres.")
    conn.execute("INSERT INTO ayuda_votos (mision, util, comentario, usuario_id, usuario_nombre, creado_en)"
                 " VALUES (?, ?, ?, ?, ?, ?)",
                 (mision, 1 if util == "si" else 0, comentario, quien.user_id, quien.nombre,
                  ahora.isoformat(timespec="seconds")))
    conn.commit()


def resumen(conn: sqlite3.Connection) -> list[Resumen]:
    """Una fila por misión votada, primero las que tienen más «no»."""
    return [Resumen(*fila) for fila in conn.execute(
        "SELECT mision, SUM(util), SUM(1 - util),"
        " COALESCE((SELECT comentario FROM ayuda_votos c WHERE c.mision = v.mision AND comentario <> ''"
        "           ORDER BY id DESC LIMIT 1), '')"
        " FROM ayuda_votos v GROUP BY mision ORDER BY SUM(1 - util) DESC, SUM(util) ASC, mision")]
