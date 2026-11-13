"""Lee los marcadores `[captura: <pantalla> · resaltar <qué>]` de las misiones (docs/ayuda/misiones/*.md).

Cada marcador queda ligado a su misión y al número del paso donde está escrito. Si un paso tiene más de una
captura, la segunda es «-2», la tercera «-3».
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.ayuda import MISIONES_DIR

_PASO = re.compile(r"^\s*(\d+)\.\s")
_CAPTURA = re.compile(r"\[captura:(.*)\]\s*$")
_PARTES = re.compile(r"\s*(.+?)\s+·\s+resaltar\s+(.+?)\s*")


class MarcadorInvalido(ValueError):
    """Un marcador mal escrito: dice la misión y la línea."""


@dataclass(frozen=True)
class Marcador:
    mision: str      # nombre del archivo sin .md, p. ej. «08-revision»
    paso: int
    orden: int       # 1 la primera captura del paso, 2 la segunda…
    pantalla: str    # «Cartel», «Panel de carteles»…
    objetivo: str    # ««Guardar revisión»», «la prioridad»…
    linea: int

    @property
    def imagen(self) -> str:
        """Ruta de la imagen dentro de la carpeta de capturas: «08-revision/08.png», «02-…/03-2.png»."""
        sufijo = "" if self.orden == 1 else f"-{self.orden}"
        return f"{self.mision}/{self.paso:02d}{sufijo}.png"

    @property
    def alt(self) -> str:
        """Texto alternativo: lo lee un lector de pantalla o se ve si la imagen no carga."""
        return f"Pantalla «{self.pantalla}»: {self.objetivo} resaltado."

    @property
    def donde(self) -> str:
        return f"{self.mision}, paso {self.paso}"


def leer_mision(archivo: Path) -> list[Marcador]:
    mision = archivo.stem
    marcadores: list[Marcador] = []
    paso: int | None = None
    orden = 0
    for n, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), start=1):
        if m := _PASO.match(linea):
            paso, orden = int(m.group(1)), 0
        if not (c := _CAPTURA.search(linea)):
            continue
        partes = _PARTES.fullmatch(c.group(1))
        if partes is None:
            raise MarcadorInvalido(f"{mision}, línea {n}: el marcador debe ser "
                                   f"«[captura: <pantalla> · resaltar <qué>]» y dice «{c.group(0)}».")
        if paso is None:
            raise MarcadorInvalido(f"{mision}, línea {n}: la captura está antes del primer paso numerado.")
        orden += 1
        marcadores.append(Marcador(mision, paso, orden, partes.group(1), partes.group(2), n))
    return marcadores


def leer(carpeta: Path = MISIONES_DIR) -> list[Marcador]:
    """Todos los marcadores de todas las misiones, en el orden de las misiones (01, 02…)."""
    return [m for archivo in sorted(carpeta.glob("*.md")) for m in leer_mision(archivo)]
