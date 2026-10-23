"""ZIP de «Detalle pliego de condiciones» tal como lo entrega SICOP: trae los carteles y sus líneas.

Así nadie tiene que descomprimirlo a mano (DECISION_OBTENCION.md, opción O4a).
* Se revisa el ZIP (dañado, archivos que faltan o sobran, tamaño) y se extraen los dos CSV a una carpeta que
  decide el programa, con el nombre de siempre.
* Cada CSV se importa con su importador de siempre. Su huella (hash) es la misma que si alguien descomprime el
  ZIP a mano, así que un CSV ya importado se reconoce y no se importa dos veces.
* El orden importa: primero los carteles y después sus líneas.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

# Nombre dentro del ZIP → reporte, en el orden en que se importan (observado en el ZIP real del 2026-10-09).
ARCHIVOS = {"Detalle de pliegos de condiciones.csv": "carteles", "Detalles lineas.csv": "lineas"}
# Los dos CSV reales suman ≈ 7,5 MB: un tamaño muy distinto es señal de un archivo que no es el reporte.
MAX_DESCOMPRIMIDO = 200 * 1024 * 1024


class ZipInvalido(Exception):
    """El ZIP no se puede usar tal como está; el mensaje es el que verá la usuaria."""


def es_zip_de_pliegos(path: Path, archivos: dict[str, str] = ARCHIVOS) -> bool:
    """¿Es un ZIP legible que trae alguno de los CSV del reporte de pliegos? (Si está dañado, no lo es.)

    `archivos` permite preguntar lo mismo por otro ZIP de SICOP (p. ej. adjudicaciones)."""
    if path.suffix.lower() != ".zip" or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            return any(n in archivos for n in zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def extraer(path: Path, carpeta: Path, archivos: dict[str, str] = ARCHIVOS,
            reporte_zip: str = "reporte de pliegos") -> list[tuple[str, Path]]:
    """Extrae los CSV en la carpeta y devuelve [(reporte, ruta)] en el orden de `archivos` (carteles primero).

    `archivos` y `reporte_zip` permiten usarlo con otro ZIP de SICOP (p. ej. adjudicaciones).
    """
    try:
        with zipfile.ZipFile(path) as zf:
            nombres = zf.namelist()
            faltan = [n for n in archivos if n not in nombres]
            sobran = [n for n in nombres if n not in archivos]
            if faltan or sobran:
                detalle = "; ".join(filter(None, [f"faltan {', '.join(faltan)}" if faltan else "",
                                                  f"sobran {', '.join(sobran)}" if sobran else ""]))
                raise ZipInvalido(f"el ZIP no es el {reporte_zip} tal como lo entrega SICOP ({detalle})")
            if sum(zf.getinfo(n).file_size for n in archivos) > MAX_DESCOMPRIMIDO:
                raise ZipInvalido(f"el ZIP descomprimido pasa de {MAX_DESCOMPRIMIDO // (1024 * 1024)} MB: "
                                  f"no parece el {reporte_zip}")
            if (malo := zf.testzip()) is not None:
                raise ZipInvalido(f"el ZIP está dañado ({malo}). Vuelve a descargarlo")
            carpeta.mkdir(parents=True, exist_ok=True)
            extraidos = []
            for nombre, reporte in archivos.items():
                # El nombre lo pone el programa (de `archivos`), nunca una ruta que venga dentro del ZIP.
                destino = carpeta / nombre
                destino.write_bytes(zf.read(nombre))
                extraidos.append((reporte, destino))
            return extraidos
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise ZipInvalido(f"el ZIP no se puede leer: {exc}") from exc
