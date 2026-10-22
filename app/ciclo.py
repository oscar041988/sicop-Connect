"""Ciclo completo (lección 8): recoger → importar → evaluar → avisar, con un solo comando (run-cycle).

Reglas:
* Un bloqueo de archivo impide dos ciclos a la vez; el segundo se va sin tocar nada (CicloOcupado).
* Cada ejecución queda en source_runs (kind = 'ciclo') con su cobertura: qué archivos vio y qué pasó con cada uno.
* Un archivo incompleto, ilegible o que no se reconoce es un ERROR explícito: no se importa, se aparta en
  INCOMING_DIR/con_error/<fecha>/ y el ciclo queda «fallo». Nunca se interpreta como «cero oportunidades».
* Si la fuente falló o no llegó ningún archivo nuevo, se evalúa igual (los plazos cambian con el día) pero
  NO se avisa: un correo sin los datos de hoy daría a entender que no hubo compras nuevas.
* Los archivos importados (o ya importados antes) se mueven a INCOMING_DIR/procesados/<fecha>/.
* El ZIP de pliegos se acepta tal como llega: se importan sus dos CSV (app/importers/zip_pliegos.py) y el ZIP
  se mueve entero, a procesados o, si alguno de sus CSV falló, a con_error.
* Obtención en modo manual: los archivos los descarga una persona y los deja en INCOMING_DIR (o los sube en el
  panel). Este módulo no programa nada; el horario lo pone el temporizador del servidor (lección 9).
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import time
import zipfile
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app import avisos
from app.bloqueo import CicloOcupado, bloqueo
from app.config import Settings
from app.database import connect
from app.importers import carteles, catalogo, instituciones, lineas, zip_pliegos
from app.importers.comun import HORA_CR, ImportacionError
from app.importers.csv_reader import parse_csv
from app.matching.evaluar import ResultadoEvaluacion, evaluar_base
from app.matching.reglas import REGLAS_PATH, cargar_reglas

__all__ = ["CicloOcupado", "Ciclo", "ArchivoCiclo", "run_cycle", "ruta_bloqueo"]

# Orden de importación: el comprador y el cartel antes que sus líneas; el catálogo antes de las líneas
# (la línea se marca «sin catálogo» según lo que haya al importarla).
ORDEN = ("instituciones", "carteles", "catalogo", "lineas")
IMPORTADORES = {"instituciones": instituciones.import_instituciones, "carteles": carteles.import_carteles,
                "catalogo": catalogo.import_catalogo, "lineas": lineas.import_lineas}
# Encabezados que identifican cada reporte (los mismos que exige su importador).
ENCABEZADOS = {"instituciones": set(instituciones.COLUMNAS), "carteles": set(carteles.COLUMNAS),
               "catalogo": set(catalogo.COLUMNAS), "lineas": set(lineas.COLUMNAS)}

# Un archivo modificado hace menos de esto puede estar copiándose todavía: se deja para el próximo ciclo.
ESPERA_S = 60
TEMPORALES = (".part", ".crdownload", ".download", ".tmp", ".partial")
PROCESADOS, CON_ERROR = "procesados", "con_error"


class ArchivoInvalido(Exception):
    """El archivo no se puede importar tal como está; el mensaje es el que verá la usuaria."""


@dataclass
class ArchivoCiclo:
    archivo: str
    resultado: str               # importado · ya_importado · error · en_espera · ignorado
    reporte: str | None = None
    detalle: str = ""
    import_id: int | None = None
    aceptadas: int = 0
    rechazadas: int = 0
    movido_a: str | None = None


@dataclass
class Ciclo:
    id: int
    dry_run: bool
    estado: str = "en_curso"     # ok · fallo
    error: str | None = None
    archivos: list[ArchivoCiclo] = field(default_factory=list)
    periodo: tuple[str | None, str | None] = (None, None)
    evaluacion: ResultadoEvaluacion | None = None
    avisos: avisos.Resultado | None = None
    aviso_omitido: str | None = None   # por qué no se avisó, si no se avisó

    def contar(self, resultado: str) -> int:
        return sum(1 for a in self.archivos if a.resultado == resultado)


def ruta_bloqueo(settings: Settings) -> Path:
    """Junto a la base: en el servidor, /var/lib/sicop-connect/run-cycle.lock."""
    return settings.database_path.parent / "run-cycle.lock"


def _momento(ahora: datetime) -> str:
    return ahora.isoformat(timespec="seconds")


# --- Recoger --------------------------------------------------------------------------------------------

def recoger(carpeta: Path, ahora_epoch: float | None = None) -> tuple[list[Path], list[ArchivoCiclo]]:
    """Archivos completos de la carpeta (sin entrar en subcarpetas) y los que se dejan para después."""
    ahora_epoch = time.time() if ahora_epoch is None else ahora_epoch
    listos, apartados = [], []
    for path in sorted(p for p in carpeta.iterdir() if p.is_file()):
        nombre = path.name
        if nombre.startswith((".", "~$")) or nombre.lower().endswith(TEMPORALES):
            apartados.append(ArchivoCiclo(nombre, "ignorado", detalle="archivo temporal o de descarga en curso"))
        elif ahora_epoch - path.stat().st_mtime < ESPERA_S:
            apartados.append(ArchivoCiclo(nombre, "en_espera",
                                          detalle=f"modificado hace menos de {ESPERA_S} s: puede estar copiándose"))
        else:
            listos.append(path)
    return listos, apartados


def revisar_csv(raw: bytes, nombre: str) -> list[str]:
    """Encabezado del CSV, si el archivo está completo; si no, ArchivoInvalido con el motivo."""
    if not raw:
        raise ArchivoInvalido("el archivo está vacío (0 bytes)")
    # Los reportes de SICOP terminan con un salto de línea: si no, la descarga se cortó a mitad de una fila.
    if not raw.endswith(b"\n"):
        raise ArchivoInvalido("incompleto: termina a mitad de una fila (¿descarga cortada?). Vuelve a descargarlo")
    try:
        csv_file = parse_csv(raw)
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de lectura es «ilegible»
        raise ArchivoInvalido(f"ilegible: {exc}") from exc
    if csv_file.rows:
        linea, valores = csv_file.rows[-1]
        if len(valores) != len(csv_file.header):
            raise ArchivoInvalido(f"incompleto: la última fila (línea {linea}) tiene {len(valores)} columnas y el "
                                  f"encabezado {len(csv_file.header)}. Vuelve a descargarlo")
    return csv_file.header


def tipo_de_reporte(path: Path) -> str:
    """Qué reporte es, por su contenido (no por el nombre, que el navegador o la persona pueden cambiar)."""
    if path.suffix.lower() == ".zip":
        if not zipfile.is_zipfile(path):
            raise ArchivoInvalido("el ZIP está dañado o incompleto. Vuelve a descargarlo")
        try:
            with zipfile.ZipFile(path) as zf:
                malo = zf.testzip()
                if catalogo.ARCHIVO_EN_ZIP not in zf.namelist():
                    raise ArchivoInvalido(f"el ZIP no trae {catalogo.ARCHIVO_EN_ZIP!r} ni los CSV de pliegos: "
                                          "no es el catálogo ni el reporte de pliegos del portal")
                raw = zf.read(catalogo.ARCHIVO_EN_ZIP)
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise ArchivoInvalido(f"el ZIP no se puede leer: {exc}") from exc
        if malo:
            raise ArchivoInvalido(f"el ZIP está dañado ({malo}). Vuelve a descargarlo")
    else:
        raw = path.read_bytes()
    encabezado = set(revisar_csv(raw, path.name))
    tipos = [t for t in ORDEN if ENCABEZADOS[t] <= encabezado]
    if len(tipos) != 1:
        motivo = "varios tipos" if tipos else "ninguno"
        raise ArchivoInvalido(f"no se reconoce el tipo de reporte ({motivo}) por su encabezado. "
                              "¿Es un reporte de SICOP? ¿Pasó por Excel? (docs/MAPEO_DATOS.md)")
    return tipos[0]


def _mover(path: Path, carpeta: Path) -> Path:
    """Mueve sin pisar: si ya hay uno con ese nombre (p. ej. el mismo archivo otra vez), agrega un número."""
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / path.name
    n = 2
    while destino.exists():
        destino = carpeta / f"{path.stem} ({n}){path.suffix}"
        n += 1
    shutil.move(str(path), str(destino))
    return destino


# --- Registro en source_runs ---------------------------------------------------------------------------

def _cobertura(ciclo: Ciclo) -> str:
    datos = {
        "modo": "dry-run" if ciclo.dry_run else "envio",
        "archivos": [{k: v for k, v in a.__dict__.items() if v not in (None, "", 0)} | {"resultado": a.resultado}
                     for a in ciclo.archivos],
    }
    if ciclo.evaluacion:
        e = ciclo.evaluacion
        datos["evaluacion"] = {"reglas": e.version, "carteles": e.carteles, "nuevas": e.nuevas,
                               "actualizadas": e.actualizadas}
    if ciclo.avisos:
        a = ciclo.avisos
        datos["avisos"] = {"destinatarios": a.destinatarios, "nuevos": a.nuevos,
                           "preparados": sum(len(v) for v in a.preparados.values()),
                           "envios": {p: e.estado for p, e in a.envios.items()}}
    if ciclo.aviso_omitido:
        datos["avisos_omitidos"] = ciclo.aviso_omitido
    return json.dumps(datos, ensure_ascii=False)


def _abrir(conn: sqlite3.Connection, origen: str, ahora: datetime, modo: str) -> int:
    return conn.execute(
        "INSERT INTO source_runs (started_at, mode, data_origin, status, kind) VALUES (?, ?, ?, 'en_curso', 'ciclo')",
        (_momento(ahora), modo, origen)).lastrowid


def _cerrar(conn: sqlite3.Connection, ciclo: Ciclo) -> None:
    conn.execute(
        "UPDATE source_runs SET finished_at = ?, status = ?, error = ?, period_from = ?, period_to = ?, coverage = ?"
        " WHERE id = ?",
        (_momento(datetime.now(HORA_CR)), ciclo.estado, ciclo.error, *ciclo.periodo, _cobertura(ciclo), ciclo.id))


def registrar_ocupado(settings: Settings, origen: str, quien: str, ahora: datetime) -> None:
    """El ciclo que no pudo tomar el bloqueo también queda registrado (sin tocar nada más)."""
    with closing(connect(settings.database_path)) as conn:
        momento = _momento(ahora)
        conn.execute(
            "INSERT INTO source_runs (started_at, finished_at, mode, data_origin, status, error, kind)"
            " VALUES (?, ?, 'manual', ?, 'fallo', ?, 'ciclo')",
            (momento, momento, origen, "otro ciclo en curso" + (f" ({quien})" if quien else "") + ": no se hizo nada"))


# --- El ciclo ----------------------------------------------------------------------------------------

def _clasificar(path: Path, temporal: Path) -> list[tuple[str, Path]]:
    """[(reporte, CSV a importar)]. El ZIP de pliegos se abre en sus dos CSV; lo demás es un solo archivo."""
    if zip_pliegos.es_zip_de_pliegos(path):
        try:
            csvs = zip_pliegos.extraer(path, temporal)
        except zip_pliegos.ZipInvalido as exc:
            raise ArchivoInvalido(str(exc)) from exc
        return [(tipo_de_reporte(csv), csv) for _, csv in csvs]  # misma revisión que un CSV suelto
    return [(tipo_de_reporte(path), path)]


def _importar(conn, settings: Settings, ciclo: Ciclo, listos: list[Path], origen: str, fecha: str) -> list[str]:
    errores: list[str] = []
    por_tipo: dict[str, list[Path]] = {t: [] for t in ORDEN}
    zip_de: dict[Path, Path] = {}                 # CSV sacado de un ZIP de pliegos → ese ZIP
    partes: dict[Path, list[ArchivoCiclo]] = {}   # ZIP → lo que pasó con cada uno de sus CSV
    con_error: set[Path] = set()
    with tempfile.TemporaryDirectory() as temporal:
        for n, path in enumerate(listos):
            try:
                clasificados = _clasificar(path, Path(temporal) / str(n))
            except (ArchivoInvalido, OSError) as exc:
                errores.append(f"{path.name}: {exc}")
                movido = _mover(path, settings.incoming_dir / CON_ERROR / fecha)
                ciclo.archivos.append(ArchivoCiclo(path.name, "error", detalle=str(exc), movido_a=str(movido)))
                continue
            for tipo, csv in clasificados:
                por_tipo[tipo].append(csv)
                if csv != path:
                    zip_de[csv] = path
                    partes.setdefault(path, [])
        desde, hasta = [], []
        for tipo in ORDEN:
            for path in por_tipo[tipo]:
                zip_origen = zip_de.get(path)
                nombre = f"{zip_origen.name} › {path.name}" if zip_origen else path.name
                try:
                    r = IMPORTADORES[tipo](conn, path, origen, settings.raw_data_dir, source_run_id=ciclo.id)
                except (ImportacionError, OSError) as exc:
                    errores.append(f"{nombre}: {exc}")
                    archivo = ArchivoCiclo(nombre, "error", tipo, str(exc))
                    if zip_origen:  # el ZIP entero se aparta al final
                        con_error.add(zip_origen)
                        partes[zip_origen].append(archivo)
                    else:
                        archivo.movido_a = str(_mover(path, settings.incoming_dir / CON_ERROR / fecha))
                    ciclo.archivos.append(archivo)
                    continue
                if r.ya_importado is not None:
                    archivo = ArchivoCiclo(nombre, "ya_importado", tipo,
                                           f"igual a la importación #{r.ya_importado}: no cambió nada", r.ya_importado)
                else:
                    archivo = ArchivoCiclo(nombre, "importado", tipo, import_id=r.import_id,
                                           aceptadas=r.aceptadas, rechazadas=len(r.rechazos))
                    if r.periodo[0]:
                        desde.append(r.periodo[0])
                        hasta.append(r.periodo[1])
                if zip_origen:
                    partes[zip_origen].append(archivo)
                else:
                    archivo.movido_a = str(_mover(path, settings.incoming_dir / PROCESADOS / fecha))
                ciclo.archivos.append(archivo)
    # Cada ZIP se mueve una sola vez: a con_error si alguno de sus CSV falló; si no, a procesados.
    for zip_path, archivos in partes.items():
        destino = CON_ERROR if zip_path in con_error else PROCESADOS
        movido = str(_mover(zip_path, settings.incoming_dir / destino / fecha))
        for archivo in archivos:
            archivo.movido_a = movido
    ciclo.periodo = (min(desde), max(hasta)) if desde else (None, None)
    return errores


def run_cycle(settings: Settings, origen: str, dry_run: bool = True, ahora: datetime | None = None,
              proveedor: avisos.Proveedor | None = None, reglas_path: Path = REGLAS_PATH,
              modo: str = "manual") -> Ciclo:
    """Un ciclo completo. Lanza CicloOcupado si ya hay otro. Con dry_run=False hace falta el proveedor.
    modo (source_runs.mode): manual = run-cycle o la tarea de las 8:00 · auto = lo lanzó obtain auto."""
    ahora = (ahora or datetime.now(HORA_CR)).astimezone(HORA_CR)
    quien = f"empezó {ahora:%Y-%m-%d %H:%M:%S}, proceso {os.getpid()}"
    with bloqueo(ruta_bloqueo(settings), quien), closing(connect(settings.database_path)) as conn:
        # Un ciclo anterior que se cortó (apagón, proceso cerrado) quedó «en_curso»: ya no lo está.
        conn.execute("UPDATE source_runs SET status = 'fallo', error = 'interrumpido: el ciclo no terminó'"
                     " WHERE kind = 'ciclo' AND status = 'en_curso'")
        ciclo = Ciclo(_abrir(conn, origen, ahora, modo), dry_run)
        try:
            _paso_a_paso(conn, settings, ciclo, origen, ahora, proveedor, reglas_path)
        except Exception as exc:
            ciclo.estado, ciclo.error = "fallo", f"error inesperado: {type(exc).__name__}: {exc}"
            _cerrar(conn, ciclo)
            raise
        _cerrar(conn, ciclo)
        return ciclo


def _paso_a_paso(conn, settings, ciclo: Ciclo, origen, ahora, proveedor, reglas_path) -> None:
    errores: list[str] = []
    carpeta = settings.incoming_dir
    if not carpeta.is_dir():
        errores.append(f"no existe la carpeta de entrada INCOMING_DIR ({carpeta})")
    else:
        listos, apartados = recoger(carpeta)
        ciclo.archivos.extend(apartados)
        errores += _importar(conn, settings, ciclo, listos, origen, f"{ahora:%Y-%m-%d}")
    nuevos = ciclo.contar("importado")
    en_espera = ciclo.contar("en_espera")
    if not errores and nuevos == 0 and en_espera:
        errores.append(f"no se importó ningún archivo nuevo: {en_espera} en espera (modificado hace menos de "
                       f"{ESPERA_S} s); vuelve a correr el ciclo en un minuto")
    elif not errores and nuevos == 0:
        errores.append("no llegó ningún archivo nuevo: no hay datos de hoy (no significa que no haya compras)")

    # Evaluar siempre: aunque no haya datos nuevos, los plazos cambian con el día.
    ciclo.evaluacion = evaluar_base(conn, cargar_reglas(reglas_path), ahora=ahora)

    if errores:
        ciclo.estado, ciclo.error = "fallo", " · ".join(errores)
        ciclo.aviso_omitido = "la fuente falló o no trajo datos nuevos: no se avisa con datos incompletos"
        return
    try:
        ciclo.avisos = avisos.notify(conn, settings, ahora, dry_run=ciclo.dry_run, proveedor=proveedor)
    except avisos.AvisoError as exc:
        ciclo.estado, ciclo.error = "fallo", f"avisos: {exc}"
        return
    no_aceptados = sorted(p for p, e in ciclo.avisos.envios.items() if e.estado != "aceptado")
    if no_aceptados:
        ciclo.estado, ciclo.error = "fallo", "avisos sin aceptar: " + ", ".join(
            f"{p} ({ciclo.avisos.envios[p].estado})" for p in no_aceptados)
        return
    ciclo.estado = "ok"
