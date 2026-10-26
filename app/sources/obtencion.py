"""Espera del enlace, descarga y validación del reporte (obtención automática, lección 3).

Máquina de estados de cada solicitud (tabla solicitudes_sicop, migración 0010), solo hacia adelante:
    solicitado → codigo_ingresado → esperando_enlace → descargado → validado,  o  fallido (con su motivo).
    Con OBTAIN_DOWNLOAD=manual (por defecto): esperando_enlace → enlace_recibido, y la descarga la hace una persona.
obtain request (app/sources/sicop_browser.py) llega hasta esperando_enlace. obtain poll (sondear) sigue desde ahí:
1. Revisa el buzón con el lector de la lección 1. Si el correo no llega en OBTAIN_LINK_MAX_HOURS → fallido.
2. Con OBTAIN_DOWNLOAD=manual se detiene aquí: SICOP bloqueó la descarga hecha por el programa (2026-10-22) y Oscar
   decidió descargar a mano (2026-10-26). La solicitud queda enlace_recibido y obtain auto manda el recordatorio.
   Con auto: descarga el ZIP con el enlace a RAW_DATA_DIR/descargas (el original se conserva) y guarda su SHA-256.
3. Lo valida: el ZIP de pliegos con sus dos CSV, UTF-8 con BOM, separador «;», encabezados esperados y filas > 0.
   Un archivo vacío o raro es un FALLO, nunca «cero oportunidades».
4. Si es válido, lo copia a INCOMING_DIR, donde el ciclo de la lección 4 lo importa. Aquí no se importa nada.
Como el estado está en la base, un reinicio no pierde la solicitud: el siguiente sondeo sigue donde quedó.
Nunca se pide otro reporte automáticamente, y nunca se muestran el enlace ni el processId.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from app import ciclo
from app.bloqueo import bloqueo
from app.config import Settings
from app.database import connect
from app.importers import zip_pliegos
from app.importers.comun import HORA_CR
from app.importers.csv_reader import parse_csv
from app.sources import sicop_browser
from app.sources.gmail_reader import CorreoNoLlego, FormatoDesconocido
from app.sources.sicop_browser import MARGEN_RELOJ, FalloObtencion

ABIERTOS = ("solicitado", "codigo_ingresado", "esperando_enlace", "descargado")
VIGENCIA_ENLACE = timedelta(hours=24)  # «El archivo permanecerá disponible 24 hrs» (ventana de SICOP)
BOM = b"\xef\xbb\xbf"


class ArchivoNoValido(Exception):
    """El archivo descargado no es el reporte esperado. El mensaje dice por qué."""


@dataclass(frozen=True)
class ResultadoSondeo:
    solicitud_id: int | None
    estado: str | None  # estado después del sondeo; None si no había ninguna solicitud abierta
    mensaje: str        # sin enlaces ni processId
    fallo: bool = False


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def ruta_bloqueo(settings: Settings) -> Path:
    """Junto a la base, como el del ciclo: un solo sondeo a la vez."""
    return settings.database_path.parent / "obtain-poll.lock"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def validar(path: Path) -> dict[str, int]:
    """Filas de cada CSV del ZIP de pliegos, o ArchivoNoValido con el motivo."""
    if path.stat().st_size == 0:
        raise ArchivoNoValido("está vacío (0 bytes)")
    with path.open("rb") as f:
        inicio = f.read(512).lstrip().lower()
    if inicio.startswith((b"<!doctype", b"<html", b"<")):
        raise ArchivoNoValido("SICOP entregó una página web en vez del ZIP (¿enlace vencido?)")
    if not zip_pliegos.es_zip_de_pliegos(path):
        raise ArchivoNoValido("no es el ZIP del reporte «Detalle pliego de condiciones»")
    filas: dict[str, int] = {}
    with tempfile.TemporaryDirectory() as temporal:
        try:
            csvs = zip_pliegos.extraer(path, Path(temporal))
        except zip_pliegos.ZipInvalido as exc:
            raise ArchivoNoValido(str(exc)) from None
        for reporte, csv in csvs:
            raw = csv.read_bytes()
            try:
                encabezado = set(ciclo.revisar_csv(raw, csv.name))
            except ciclo.ArchivoInvalido as exc:
                raise ArchivoNoValido(f"{csv.name}: {exc}") from None
            if not raw.startswith(BOM):
                raise ArchivoNoValido(f"{csv.name}: no es UTF-8 con BOM, como lo entrega SICOP (¿pasó por Excel?)")
            leido = parse_csv(raw)
            if leido.delimiter != ";":
                raise ArchivoNoValido(f"{csv.name}: el separador no es «;»")
            if faltan := ciclo.ENCABEZADOS[reporte] - encabezado:
                raise ArchivoNoValido(f"{csv.name}: faltan columnas ({', '.join(sorted(faltan))}); "
                                      "comparar con docs/MAPEO_DATOS.md")
            if not leido.rows:
                raise ArchivoNoValido(f"{csv.name}: no tiene filas (solo el encabezado)")
            filas[reporte] = len(leido.rows)
    return filas


def _momento(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def sondear(settings: Settings, lector, *, reloj: Callable[[], datetime] = _ahora,
            descargar: Callable = sicop_browser.descargar) -> ResultadoSondeo:
    """Un sondeo: avanza la última solicitud abierta todo lo que se pueda. Lanza CicloOcupado si hay otro sondeo
    y GmailError si no se pudo leer el buzón (la solicitud sigue abierta para el próximo sondeo)."""
    with bloqueo(ruta_bloqueo(settings), f"obtain poll · {_momento(reloj())} · proceso {os.getpid()}"):
        with closing(connect(settings.database_path)) as conn:
            conn.row_factory = sqlite3.Row
            try:
                fila = conn.execute("SELECT * FROM solicitudes_sicop WHERE estado IN (?, ?, ?, ?) ORDER BY id DESC"
                                    " LIMIT 1", ABIERTOS).fetchone()
            except sqlite3.OperationalError:
                raise FalloObtencion("La base no tiene la tabla solicitudes_sicop: ejecuta python -m app.cli migrate.") from None
            if fila is None:
                return ResultadoSondeo(None, None, "No hay ninguna solicitud abierta (la crea obtain request).")
            return _avanzar(conn, settings, dict(fila), lector, reloj, descargar)


def _avanzar(conn, settings: Settings, fila: dict, lector, reloj, descargar) -> ResultadoSondeo:
    sid, ahora = fila["id"], reloj()
    solicitada = datetime.fromisoformat(fila["solicitada_en"])
    plazo = solicitada + timedelta(hours=settings.obtain_link_max_hours)

    def actualizar(**campos) -> None:
        columnas = ", ".join(f"{c} = ?" for c in campos)
        conn.execute(f"UPDATE solicitudes_sicop SET {columnas} WHERE id = ?", (*campos.values(), sid))

    def fallar(motivo: str) -> ResultadoSondeo:
        actualizar(estado="fallido", motivo=motivo, terminada_en=_momento(reloj()))
        return ResultadoSondeo(sid, "fallido", motivo, fallo=True)

    if fila["estado"] == "solicitado":
        if ahora > plazo:
            return fallar("La solicitud quedó a medias (no se llegó a escribir el código en SICOP). "
                          "No se pide otro reporte hoy.")
        return ResultadoSondeo(sid, "solicitado", "La solicitud todavía no tiene el código escrito "
                                                  "(obtain request sigue en curso o se cortó).")

    if fila["estado"] in ("codigo_ingresado", "esperando_enlace"):
        try:
            correo = lector.buscar_enlace(solicitada - MARGEN_RELOJ)
        except CorreoNoLlego:
            if ahora > plazo:
                return fallar(f"El enlace no llegó en {settings.obtain_link_max_hours} h. No se pide otro reporte "
                              "hoy: si llega tarde, descargarlo a mano.")
            return ResultadoSondeo(sid, fila["estado"], "Todavía no llegó el correo con el enlace "
                                                        f"(se espera hasta las {plazo:%H:%M}).")
        except FormatoDesconocido as exc:
            return fallar(str(exc))
        encontrado = re.search(r"processId=(\d+)", correo.valor)
        process_id = encontrado.group(1) if encontrado else None
        if fila["process_id"] and process_id != fila["process_id"]:
            return ResultadoSondeo(sid, fila["estado"], "Llegó el enlace de otra solicitud (no coincide con la "
                                                        "ventana de SICOP); se sigue esperando el de esta.")
        if ahora - correo.recibido > VIGENCIA_ENLACE:
            return fallar("El enlace tiene más de 24 h: ya venció. No se pide otro reporte hoy.")
        if settings.obtain_download == "manual":
            actualizar(estado="enlace_recibido", enlace_recibido_en=_momento(correo.recibido),
                       process_id=fila["process_id"] or process_id, terminada_en=_momento(reloj()))
            return ResultadoSondeo(sid, "enlace_recibido", "Llegó el correo «Envío de reporte»: la descarga es a mano "
                                                           "(descargar el ZIP y subirlo en «Cargar archivo»).")
        nombre = f"sicop-pliegos-{solicitada:%Y%m%d}-{sid}.zip"
        try:
            ruta = descargar(correo.valor, settings.raw_data_dir / "descargas", nombre)
        except FalloObtencion as exc:
            # El enlace sí llegó: la alerta de la lección 4 lo usa para indicar el plan B (descargar a mano).
            actualizar(enlace_recibido_en=_momento(correo.recibido))
            if exc.captura:
                actualizar(captura=str(exc.captura))
            return fallar(exc.motivo)
        actualizar(estado="descargado", enlace_recibido_en=_momento(correo.recibido),
                   process_id=fila["process_id"] or process_id, descargado_en=_momento(reloj()),
                   archivo_original=str(ruta), archivo_sha256=sha256(ruta))
        fila.update(estado="descargado", archivo_original=str(ruta))

    # descargado: se valida ese mismo archivo (también si el sondeo anterior se cortó aquí), sin bajarlo de nuevo.
    original = Path(fila["archivo_original"])
    if not original.is_file():
        return fallar("No se encuentra el archivo descargado en RAW_DATA_DIR/descargas.")
    try:
        filas = validar(original)
    except ArchivoNoValido as exc:
        return fallar(f"El archivo descargado no es válido: {exc}. Se queda en descargas/ para revisarlo; "
                      "no pasó a la carpeta de entrada.")
    settings.incoming_dir.mkdir(parents=True, exist_ok=True)
    destino = settings.incoming_dir / original.name
    parcial = destino.with_name(destino.name + ".part")  # el ciclo ignora los .part
    shutil.copy2(original, parcial)
    parcial.replace(destino)
    actualizar(estado="validado", validado_en=_momento(reloj()), archivo_entrada=str(destino),
               terminada_en=_momento(reloj()))
    return ResultadoSondeo(sid, "validado", f"ZIP validado y dejado en la carpeta de entrada: {filas['carteles']} "
                                            f"carteles y {filas['lineas']} líneas. El ciclo lo importará.")


def ultimas(settings: Settings, cuantas: int = 5) -> list[dict]:
    """Las últimas solicitudes, para obtain status (sin process_id)."""
    with closing(connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute("SELECT * FROM solicitudes_sicop ORDER BY id DESC LIMIT ?", (cuantas,)).fetchall()
    return [{k: v for k, v in dict(f).items() if k != "process_id"} for f in filas]
