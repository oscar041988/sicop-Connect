"""Lecturas para el panel de lo que trae el enriquecimiento (lección 4, entrega 4B).

* informacion(): el bloque «Información de SICOP» del detalle, de la ficha más reciente (tender_details).
* documentos(): los documentos de la ficha, uno por archivo de SICOP, con lo que pasó al bajarlos.
* bitacora() y grabacion(): la bitácora de consultas (solo administradores) y los archivos de cada grabación.
Solo lee; lo único que escribe es marcar_revisada() (migración 0022). Los textos de SICOP se muestran escapados.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.database import transaccion
from app.historial import Quien

MONEDA = re.compile(r"^[A-Z]{3}$")
ARCHIVO_GRABACION = re.compile(r"^\d{6}-[A-Za-z0-9_-]+\.(webm|png)$")

# Garantías de la ficha (DETALLE_CARTEL.md §3): nombre, y las claves de «se pide», monto, tipo de monto y plazo.
GARANTIAS = (("Garantía de participación", "participationGuarn"), ("Garantía de cumplimiento", "fulfillmentGuarn"),
             ("Garantía colateral", "collateralGuarn"))
# Tipo de monto «RAT»: es un porcentaje. Comprobado por Ivania en la pantalla de SICOP (2026-10-28): 20261002726
# trae monto 5 y tipo RAT, y la pantalla dice «5 %». Va antes que MONEDA, porque «RAT» también tiene 3 letras.
PORCENTAJE = "RAT"
TEXTO = {"extraido": "con texto", "sin_texto": "escaneado, sin texto", "no_aplica": "solo guardado (no es PDF)",
         "error": "no se pudo leer el texto"}
ESTADOS = {"guardado": "Guardado", "duplicado": "Igual a otro ya guardado", "rechazado": "Rechazado",
           "omitido_tamano": "No se bajó: muy grande", "omitido_tope": "No se bajó: tope del cartel", "fallo": "FALLO"}
RESULTADOS = {"nueva": "Ficha nueva", "sin_cambios": "Sin cambios", "fallo": "FALLO", "control": "CAPTCHA o bloqueo"}
CORRIDAS = {"en_curso": "En curso", "ok": "Bien", "con_fallos": "Con FALLO", "detenida": "Detenida",
            "sin_cola": "Sin cola"}


class RevisionInvalida(ValueError):
    """No se puede marcar revisada esa grabación."""


@dataclass
class Garantia:
    nombre: str
    se_pide: str
    monto: Decimal | None = None
    moneda: str | None = None      # código de 3 letras; si SICOP trae otro tipo, va en tipo
    tipo: str | None = None
    plazo: str | None = None
    porcentaje: Decimal | None = None   # tipo RAT: «5 %» (entonces monto y moneda quedan vacíos)


@dataclass
class Informacion:
    consultado_en: str
    versiones: int
    estado: str | None
    version_pliego: str | None
    modificado: str | None
    numero_procedimiento: str | None
    tipo_procedimiento: str | None
    modalidad: str | None
    recepcion: str | None
    inicio: str | None
    cierre: str | None
    apertura: str | None
    aclaraciones: str | None
    monto: Decimal | None
    moneda: str | None
    monto_usd: Decimal | None
    lineas: int | None
    cierre_distinto: bool                      # el cierre de SICOP no es el de los datos abiertos
    garantias: list[Garantia] = field(default_factory=list)
    contrato: list[tuple[str, str]] = field(default_factory=list)   # (dato, valor): anticipo, reajuste, multas…
    criterios: list[str] = field(default_factory=list)
    impactos: list[str] = field(default_factory=list)


@dataclass
class Documento:
    id: int
    tipo: str | None
    nombre: str | None
    archivo: str | None
    tamano: int | None
    estado: str
    texto: str | None
    paginas: int | None
    motivo: str | None


def _json(texto: str | None, vacio):
    try:
        valor = json.loads(texto) if texto else vacio
    except ValueError:
        return vacio
    return valor if isinstance(valor, type(vacio)) else vacio


def _decimal(valor) -> Decimal | None:
    if valor in (None, ""):
        return None
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


def _limpio(valor) -> str | None:
    texto = " ".join(str(valor).split()) if valor is not None else ""
    return texto or None


def _instante(iso: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(iso) if iso else None
    except ValueError:
        return None


def _garantias(datos: dict) -> tuple[list[Garantia], list[tuple[str, str]]]:
    garantias = []
    for nombre, clave in GARANTIAS:
        se_pide = _limpio(datos.get(f"{clave}RcvYnNm"))
        if se_pide is None:
            continue
        tipo = _limpio(datos.get(f"{clave}AmtType"))
        monto = _decimal(datos.get(f"{clave}Amt"))
        plazo = _limpio(datos.get(f"{clave}Dur"))
        if plazo and plazo.isdigit():
            plazo = f"{plazo} meses"   # el JSON trae solo el número; la pantalla de SICOP dice «14 meses», «12 meses»
        if tipo == PORCENTAJE:
            garantias.append(Garantia(nombre, se_pide, plazo=plazo, porcentaje=monto))
            continue
        moneda = tipo if tipo and MONEDA.match(tipo) else None
        garantias.append(Garantia(nombre, se_pide, monto, moneda, None if moneda else tipo, plazo))
    contrato = []
    duracion = " ".join(x for x in (_limpio(datos.get("contractDur")), _limpio(datos.get("contractDurUnitNm"))) if x)
    prorroga = " ".join(x for x in (_limpio(datos.get("contractExtendDur")),
                                    _limpio(datos.get("contractExtendDurUnitNm"))) if x)
    for dato, valor in (("Duración del contrato", duracion), ("Prórroga", prorroga),
                        ("Anticipo", " · ".join(x for x in (_limpio(datos.get("advancedNm")),
                                                            _limpio(datos.get("advancedCont"))) if x)),
                        ("Reajuste de precios", " · ".join(x for x in (_limpio(datos.get("amtReadjustYnNm")),
                                                                       _limpio(datos.get("amtReadjustCont"))) if x)),
                        ("Multas", _limpio(datos.get("fine"))), ("Cláusula penal", _limpio(datos.get("fineArticle")))):
        if valor:
            contrato.append((dato, valor))
    return garantias, contrato


def informacion(conn: sqlite3.Connection, nro_sicop: str) -> Informacion | None:
    """La ficha más reciente del cartel, lista para mostrar; None si no hay ninguna."""
    fila = conn.execute(
        "SELECT d.consultado_en, (SELECT count(*) FROM tender_details x WHERE x.nro_sicop = d.nro_sicop),"
        "       d.estado_concurso, d.version_pliego, d.modificado, d.numero_procedimiento, d.tipo_procedimiento,"
        "       d.tipo_modalidad, d.tipo_recepcion, d.inicio_recepcion, d.cierre_recepcion, d.apertura,"
        "       d.limite_aclaraciones, d.monto_estimado, d.moneda_monto, d.monto_estimado_usd, d.lineas_total,"
        "       d.garantias, d.criterios, t.fecha_cierre_recepcion"
        " FROM tender_details d JOIN tenders t ON t.nro_sicop = d.nro_sicop"
        " WHERE d.nro_sicop = ? ORDER BY d.id DESC LIMIT 1", (nro_sicop,)).fetchone()
    if fila is None:
        return None
    (consultado, versiones, estado, version, modificado, numero, tipo, modalidad, recepcion, inicio, cierre,
     apertura, aclaraciones, monto, moneda, monto_usd, lineas, garantias, criterios, cierre_datos) = fila
    distinto = _instante(cierre) is not None and _instante(cierre) != _instante(cierre_datos)
    lista_garantias, contrato = _garantias(_json(garantias, {}))
    crit = _json(criterios, {})
    return Informacion(
        consultado, versiones, estado, version, {"Y": "Sí", "N": "No"}.get(modificado), numero, tipo, modalidad,
        recepcion, inicio, cierre, apertura, aclaraciones, _decimal(monto), moneda, _decimal(monto_usd), lineas,
        distinto, lista_garantias, contrato,
        [c for c in (_limpio(x) for x in crit.get("criterios") or []) if c],
        [c for c in (_limpio(x) for x in crit.get("impactos") or []) if c])


def retiro(conn: sqlite3.Connection, nro_sicop: str) -> str | None:
    """Cuándo se borró al cierre la información de SICOP del cartel (el último borrado), o None."""
    fila = conn.execute("SELECT retirado_en FROM enrich_retiros WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1",
                        (nro_sicop,)).fetchone()
    return fila[0] if fila else None


def documentos(conn: sqlite3.Connection, nro_sicop: str) -> list[Documento]:
    """Un documento por archivo de SICOP: el intento guardado o, si no hubo, el último. En el orden de SICOP."""
    filas = conn.execute(
        "SELECT id, tipo_documento, nombre_documento, nombre_original, tamano_bytes, estado, texto_estado, paginas,"
        "       motivo, server_file FROM tender_documents WHERE nro_sicop = ?"
        " ORDER BY (estado = 'guardado') DESC, id DESC", (nro_sicop,)).fetchall()
    vistos, lista = set(), []
    for *datos, server in filas:
        if server not in vistos:
            vistos.add(server)
            lista.append(Documento(*datos))
    return sorted(lista, key=lambda d: d.id)


def documento_guardado(conn: sqlite3.Connection, raiz: Path, nro_sicop: str, doc_id: int) -> tuple[Path, str] | None:
    """El archivo de un documento guardado de ESE cartel y su nombre original, solo si está dentro de raiz
    (DOCUMENTS_DIR) y existe. None en cualquier otro caso: la ruta guardada nunca saca el archivo de su carpeta."""
    fila = conn.execute("SELECT ruta_local, nombre_original, server_file FROM tender_documents WHERE id = ? AND"
                        " nro_sicop = ? AND estado = 'guardado'", (doc_id, nro_sicop)).fetchone()
    if fila is None or not fila[0]:
        return None
    base = raiz.resolve()
    ruta = (base / fila[0]).resolve()
    if not ruta.is_relative_to(base) or not ruta.is_file():
        return None
    return ruta, _limpio(fila[1]) or fila[2]


# --- Bitácora de consultas (solo administradores) -------------------------------------------------------------

@dataclass
class Consulta:
    id: int
    iniciada_en: str
    nro_sicop: str
    resultado: str
    motivo: str | None
    duracion_s: float | None
    documentos_guardados: int
    documentos_fallo: int
    grabacion: str | None
    es_reintento: bool
    run_id: int | None
    revisada_por: str | None = None
    revisada_en: str | None = None

    @property
    def por_revisar(self) -> bool:
        return self.resultado in ("fallo", "control") and self.revisada_por is None


_CONSULTA = ("SELECT c.id, c.iniciada_en, c.nro_sicop, c.resultado, c.motivo, c.duracion_s, c.documentos_guardados,"
             "       c.documentos_fallo, c.grabacion, c.es_reintento, c.run_id, r.nombre, r.revisada_en"
             " FROM enrich_consultas c LEFT JOIN enrich_revisiones r ON r.consulta_id = c.id")


def bitacora(conn: sqlite3.Connection, solo_por_revisar: bool = False) -> dict:
    donde = (" WHERE c.resultado IN ('fallo', 'control') AND r.id IS NULL" if solo_por_revisar else "")
    return {
        "corridas": conn.execute("SELECT id, iniciada_en, terminada_en, estado, en_cola, consultados, fallos,"
                                 " resumen_estado FROM enrich_runs ORDER BY id DESC LIMIT 15").fetchall(),
        "consultas": [Consulta(*f[:9], bool(f[9]), *f[10:]) for f in conn.execute(
            f"{_CONSULTA}{donde} ORDER BY c.id DESC LIMIT 100")],
        "retiros": conn.execute("SELECT nro_sicop, retirado_en, cierre, documentos, bytes FROM enrich_retiros"
                                " ORDER BY id DESC LIMIT 20").fetchall(),
        "por_revisar": conn.execute("SELECT count(*) FROM enrich_consultas c WHERE resultado IN ('fallo', 'control')"
                                    " AND NOT EXISTS (SELECT 1 FROM enrich_revisiones r WHERE r.consulta_id = c.id)"
                                    ).fetchone()[0],
    }


def consulta(conn: sqlite3.Connection, consulta_id: int) -> Consulta | None:
    f = conn.execute(f"{_CONSULTA} WHERE c.id = ?", (consulta_id,)).fetchone()
    return Consulta(*f[:9], bool(f[9]), *f[10:]) if f else None


def _carpeta(raiz: Path, c: Consulta) -> tuple[Path, str] | None:
    """Carpeta de la grabación dentro de raiz (RECORDINGS_DIR) y el prefijo de sus archivos («HHMMSS-»)."""
    if not c.grabacion or c.grabacion.count("/") != 2:
        return None
    dia, nro, hora = c.grabacion.split("/")
    base = raiz.resolve()
    carpeta = (base / dia / nro).resolve()
    if not carpeta.is_relative_to(base) or not re.fullmatch(r"\d{6}", hora):
        return None
    return carpeta, f"{hora}-"


def archivos_grabacion(raiz: Path, c: Consulta) -> tuple[str | None, list[str]]:
    """(video, capturas en orden) de la grabación que siguen en disco; (None, []) si ya se borró."""
    lugar = _carpeta(raiz, c)
    if lugar is None or not lugar[0].is_dir():
        return None, []
    carpeta, prefijo = lugar
    nombres = sorted(p.name for p in carpeta.iterdir()
                     if p.is_file() and p.name.startswith(prefijo) and ARCHIVO_GRABACION.match(p.name))
    video = next((n for n in nombres if n.endswith(".webm")), None)
    return video, [n for n in nombres if n.endswith(".png")]


def archivo_grabacion(raiz: Path, c: Consulta, nombre: str) -> Path | None:
    """Un archivo de la grabación de ESA consulta; None si el nombre no es de ella o no está."""
    lugar = _carpeta(raiz, c)
    if lugar is None or not ARCHIVO_GRABACION.match(nombre) or not nombre.startswith(lugar[1]):
        return None
    ruta = (lugar[0] / nombre).resolve()
    return ruta if ruta.parent == lugar[0] and ruta.is_file() else None


def marcar_revisada(conn: sqlite3.Connection, consulta_id: int, quien: Quien, ahora: datetime) -> None:
    c = consulta(conn, consulta_id)
    if c is None:
        raise RevisionInvalida("Esa consulta no está en la bitácora.")
    if c.resultado not in ("fallo", "control"):
        raise RevisionInvalida("Solo se marcan revisadas las grabaciones de un FALLO o un CAPTCHA.")
    if c.revisada_por is not None:
        raise RevisionInvalida(f"Ya la revisó {c.revisada_por}.")
    with transaccion(conn):
        conn.execute("INSERT INTO enrich_revisiones (consulta_id, user_id, nombre, revisada_en) VALUES (?, ?, ?, ?)",
                     (consulta_id, quien.user_id, quien.nombre, ahora.isoformat(timespec="seconds")))
