"""Gestor de documentos, paso 4: descargar todo el expediente en un ZIP (docs/GESTOR_DOCUMENTOS.md).

Sirve para el traspaso: el encargado nuevo (o un administrador) baja de una vez lo que juntó el anterior.

* Lo descargan quienes entran al expediente (seguimiento.puede_entrar); eso lo revisa la ruta.
* El ZIP trae:
  - expediente.txt: datos del cartel, encargado, historial de encargados, etapas, notas y la lista de archivos
    con su huella SHA-256 (para comprobar que llegaron completos);
  - archivos/: los archivos subidos, con el nombre que se ve en el panel. Si dos se llaman igual, el segundo
    lleva « (2)». Un archivo que falta en disco no detiene la descarga: expediente.txt lo dice.
* Los documentos de SICOP del cartel no van: se bajan desde la página del cartel.
* Cada descarga va a audit_log (sin el contenido).
"""

from __future__ import annotations

import os
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from app import expediente_archivos, historial, panel, seguimiento
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

CARPETA = "archivos"


@dataclass(frozen=True)
class Resumen:
    archivos: int
    notas: int
    faltantes: int


def nombre_zip(nro_sicop: str, ahora: datetime) -> str:
    return f"expediente_{nro_sicop}_{ahora.astimezone(HORA_CR):%Y%m%d-%H%M}.zip"


def _nombres_unicos(nombres: list[str]) -> list[str]:
    """Si dos archivos se llaman igual, el segundo lleva « (2)», el tercero « (3)»… (sin distinguir mayúsculas,
    como Windows al descomprimir)."""
    usados: set[str] = set()
    resultado = []
    for nombre in nombres:
        raiz, ext = os.path.splitext(nombre)
        candidato, n = nombre, 1
        while candidato.lower() in usados:
            n += 1
            candidato = f"{raiz} ({n}){ext}"
        usados.add(candidato.lower())
        resultado.append(candidato)
    return resultado


def _texto(nro_sicop: str, actual: seguimiento.Estado, cartel: tuple | None, quien: Quien, ahora: datetime,
           asignaciones: list, etapas: list, notas: list, lineas_archivos: list[str]) -> str:
    titulo, institucion, cierre = cartel or (None, None, None)
    f = panel.fecha_cr
    lineas = [
        f"EXPEDIENTE DEL CARTEL {nro_sicop}",
        f"Descargado el {f(ahora.isoformat())} por {quien.nombre} · SICOP CONNECT",
        "",
        f"Cartel: {' '.join(panel.legible(titulo).split()) or '(sin título)'}",
        f"Institución: {' '.join(panel.legible(institucion).split()) or 'sin datos'}",
        f"Cierre de recepción: {f(cierre)}",
        f"En seguimiento desde: {f(actual.abierto_en)} (lo abrió {actual.abierto_por})",
        f"Encargado vigente: {actual.encargado or 'sin encargado'}",
        f"Etapa: {actual.etapa_texto}",
        "",
        "== HISTORIAL DE ENCARGADOS (del más reciente al más viejo) ==",
        *([f"- {a.encargado} · asignado por {a.asignado_por} · {f(a.fecha)}" for a in asignaciones]
          or ["Sin asignaciones."]),
        "",
        "== ETAPAS (de la más reciente a la más vieja) ==",
        *[f"- {e.texto} · la puso {e.puesta_por} · {f(e.fecha)}" for e in etapas],
        f"- Preparando · desde que se le dio seguimiento, el {f(actual.abierto_en)}",
        "",
        f"== NOTAS ({len(notas)}, de la más reciente a la más vieja) ==",
    ]
    for n in notas:
        lineas += [f"--- {n.escrita_por} · {f(n.fecha)}", n.texto, ""]
    if not notas:
        lineas += ["Sin notas.", ""]
    lineas += [f"== ARCHIVOS ({len(lineas_archivos)}, en la carpeta «{CARPETA}») ==",
               *(lineas_archivos or ["Sin archivos."]), ""]
    return "\n".join(lineas)


def armar(conn: sqlite3.Connection, base: Path, nro_sicop: str, destino: BinaryIO, quien: Quien,
          ahora: datetime) -> Resumen:
    """Escribe el ZIP del expediente en destino y anota la descarga en audit_log. Que quien descarga pueda entrar
    al expediente lo revisa la ruta (puede_entrar)."""
    actual = seguimiento.estado(conn, nro_sicop)
    if actual is None:
        raise seguimiento.SeguimientoInvalido(f"El cartel {nro_sicop} no está en seguimiento.")
    cartel = conn.execute(
        "SELECT t.descripcion, i.nombre, t.fecha_cierre_recepcion FROM tenders t"
        " LEFT JOIN institutions i ON i.cedula = t.institution_cedula WHERE t.nro_sicop = ?", (nro_sicop,)).fetchone()
    archivos = list(reversed(expediente_archivos.listar(conn, nro_sicop)))  # del más viejo al más nuevo
    notas = seguimiento.notas_de(conn, nro_sicop)
    momento = ahora.astimezone(HORA_CR)
    lineas_archivos, faltantes = [], 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for archivo, nombre in zip(archivos, _nombres_unicos([a.nombre for a in archivos])):
            datos = (f"{archivo.tipo} · {archivo.tamano / 1_000_000:.1f} MB · subido por {archivo.subido_por}"
                     f" · {panel.fecha_cr(archivo.fecha)} · SHA-256 {archivo.sha256}")
            hallado = expediente_archivos.obtener(conn, base, nro_sicop, archivo.id)
            if hallado is None:
                faltantes += 1
                lineas_archivos.append(f"- FALTA EN DISCO (no va en el ZIP): {nombre} · {datos}")
                continue
            zf.write(hallado[0], f"{CARPETA}/{nombre}")
            lineas_archivos.append(f"- {CARPETA}/{nombre} · {datos}")
        texto = _texto(nro_sicop, actual, cartel, quien, ahora, seguimiento.historial_de(conn, nro_sicop),
                       seguimiento.etapas_de(conn, nro_sicop), notas, lineas_archivos)
        info = zipfile.ZipInfo("expediente.txt", date_time=momento.timetuple()[:6])
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, texto.encode("utf-8"))
    resumen = Resumen(len(archivos) - faltantes, len(notas), faltantes)
    with transaccion(conn):
        historial.registrar(conn, quien, "descargar_expediente",
                            f"{nro_sicop}: {resumen.archivos} archivos, {resumen.notas} notas"
                            + (f", {faltantes} faltan en disco" if faltantes else ""))
    return resumen
