"""Calidad de las reglas (A3, guía lección 13): precisión y cobertura por familia, con los errores y su evidencia.

Precisión: de las alertas, ¿cuántas eran correctas? Si es baja, el correo trae ruido.
Cobertura: de lo que sí interesaba, ¿cuánto se alertó? Si es baja, se pierden negocios.

Se mide con las reglas ACTUALES del YAML (se evalúan los textos en el momento, sin pasar por evaluate): así un
cambio en el YAML se ve en la siguiente medición. Dos fuentes de respuestas correctas:

* Golden set (`tests/golden/golden_set.csv` y sus líneas): etiquetas de Hermatix, con la familia esperada. Las
  filas provisionales (confirmada = no) no cuentan.
* Revisiones humanas: la última revisión de cada cartel. Encaja: «Interesa», «Revisar requisitos» u «Ofertada».
  No encaja: «No interesa» con el motivo «No encaja con el portafolio». El resto no cuenta, porque es una
  decisión de negocio, no de encaje (plazo, requisitos, presupuesto, «No se oferta»). Las revisiones no dicen la
  familia. Un cartel que está en el golden set no se cuenta otra vez por su revisión.

Una alerta es un cartel con encaje Alta o Media en una familia. Por familia:
* alertas: casos alertados en esa familia · verdaderos: de ellas, las correctas (el caso encaja y la familia es
  la esperada, o la revisión no dice familia) · precisión = verdaderos / alertas.
* relevantes: casos que encajan y esperan esa familia (solo el golden set dice la familia) · cubiertos: de
  ellos, los alertados en esa familia · cobertura = cubiertos / relevantes. Con varias familias esperadas,
  cualquiera cuenta como acierto (como en el golden set): el caso cuenta en las esperadas que sí se alertaron.
* Una alerta en otra familia de un cartel que sí encaja («otra familia») baja la precisión de esa familia, pero
  no es ruido en el correo: el cartel interesa.
El total cuenta por cartel: alertado en cualquier familia, y cubierto si se alertó en una familia esperada (o en
cualquiera, si la revisión no dice la familia).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.config import PROJECT_ROOT
from app.importers.csv_reader import read_csv
from app.matching.evaluar import Evaluacion, Texto, evaluar_textos
from app.matching.reglas import Reglas

GOLDEN_DIR = PROJECT_ROOT / "tests" / "golden"
CANDIDATO = ("alta", "media")
ENCAJA = ("interesa", "revisar_requisitos", "ofertada")
NO_ENCAJA_MOTIVO = "no_encaja"   # solo «No interesa» con este motivo cuenta como «no encaja»
TOTAL = ""


@dataclass
class Caso:
    nro_sicop: str
    titulo: str
    fuente: str                   # golden · revisión
    encaja: bool
    esperadas: frozenset[str]     # familias esperadas; vacío = no se sabe (revisiones)
    evaluaciones: list[Evaluacion] = field(default_factory=list)

    @property
    def alertadas(self) -> set[str]:
        return {e.familia for e in self.evaluaciones if e.encaje in CANDIDATO}

    def correcta(self, familia: str) -> bool:
        """¿Es correcta una alerta de esta familia?"""
        return self.encaja and (not self.esperadas or familia in self.esperadas)


@dataclass
class Conteo:
    alertas: int = 0
    verdaderos: int = 0
    relevantes: int = 0
    cubiertos: int = 0

    @property
    def precision(self) -> Decimal | None:
        return _porcentaje(self.verdaderos, self.alertas)

    @property
    def cobertura(self) -> Decimal | None:
        return _porcentaje(self.cubiertos, self.relevantes)


@dataclass
class Error:
    # falsa_alerta: el cartel no encaja (baja la precisión) · otra_familia: el cartel encaja, pero se alertó
    # también en una familia que no es la suya (baja la precisión de esa familia) · no_alertado: encajaba y no se
    # alertó en su familia (baja la cobertura)
    tipo: str
    familia: str
    caso: Caso


@dataclass
class Medicion:
    version: str
    casos: list[Caso]
    por_familia: dict[str, Conteo]   # TOTAL = '' es el total por cartel
    errores: list[Error]

    def contar(self, fuente: str) -> int:
        return sum(1 for c in self.casos if c.fuente == fuente)


def _porcentaje(parte: int, total: int) -> Decimal | None:
    """Porcentaje con un decimal (Decimal: sin errores de redondeo). None si no hay con qué medir."""
    if total == 0:
        return None
    return (Decimal(100) * parte / total).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def casos_golden(golden_dir: Path = GOLDEN_DIR) -> list[tuple[Caso, list[Texto]]]:
    """Filas confirmadas del golden set, con el nombre de catálogo de sus líneas."""
    lineas: dict[str, list[Texto]] = {}
    archivo_lineas = golden_dir / "golden_lineas.csv"
    if archivo_lineas.is_file():
        csv_lineas = read_csv(archivo_lineas)
        for _, valores in csv_lineas.rows:
            f = dict(zip(csv_lineas.header, valores))
            lineas.setdefault(f["nro_sicop"], []).append(Texto(f"línea {f['numero_linea']}", f["nombre_catalogo"]))
    archivo = read_csv(golden_dir / "golden_set.csv")
    casos = []
    for _, valores in archivo.rows:
        f = dict(zip(archivo.header, valores))
        if f["confirmada"] != "sí":
            continue
        encaja = f["etiqueta"] == "interesa"
        esperadas = frozenset(x for x in f["familia_esperada"].split(";") if x) if encaja else frozenset()
        casos.append((Caso(f["nro_sicop"], f["titulo"], "golden", encaja, esperadas), lineas.get(f["nro_sicop"], [])))
    return casos


def casos_revisados(conn: sqlite3.Connection, excluir: set[str]) -> list[tuple[Caso, list[Texto]]]:
    """Última revisión de cada cartel que dice algo del encaje, con el título y las líneas del cartel."""
    filas = conn.execute(
        "SELECT r.nro_sicop, t.descripcion, r.decision, r.motivo FROM reviews r"
        " JOIN tenders t ON t.nro_sicop = r.nro_sicop"
        " WHERE r.id = (SELECT max(id) FROM reviews WHERE nro_sicop = r.nro_sicop) ORDER BY r.nro_sicop").fetchall()
    casos = []
    for nro, titulo, decision, motivo in filas:
        if nro in excluir:
            continue
        if decision in ENCAJA:
            encaja = True
        elif decision == "no_interesa" and motivo == NO_ENCAJA_MOTIVO:
            encaja = False
        else:
            continue
        lineas = [Texto(f"línea {n}", nombre) for n, nombre in conn.execute(
            "SELECT numero_linea, nombre_catalogo FROM v_tender_lines WHERE nro_sicop = ?"
            " AND estado_catalogo = 'en_catalogo' AND nombre_catalogo IS NOT NULL"
            " ORDER BY CAST(numero_linea AS INTEGER)", (nro,))]
        casos.append((Caso(nro, titulo or "", "revisión", encaja, frozenset()), lineas))
    return casos


def medir(reglas: Reglas, conn: sqlite3.Connection | None = None, golden_dir: Path = GOLDEN_DIR) -> Medicion:
    """Evalúa los casos con las reglas dadas y cuenta por familia. No escribe nada."""
    pendientes = casos_golden(golden_dir)
    if conn is not None:
        pendientes += casos_revisados(conn, {c.nro_sicop for c, _ in pendientes})
    casos = []
    for caso, lineas in pendientes:
        caso.evaluaciones = evaluar_textos(reglas, caso.titulo, lineas)
        casos.append(caso)

    familias = [f.nombre for f in reglas.familias]
    conteos = {TOTAL: Conteo(), **{f: Conteo() for f in familias}}
    errores: list[Error] = []
    for caso in casos:
        alertadas = caso.alertadas
        for familia in alertadas:
            if familia not in conteos:
                continue
            conteos[familia].alertas += 1
            if caso.correcta(familia):
                conteos[familia].verdaderos += 1
            else:
                errores.append(Error("otra_familia" if caso.encaja else "falsa_alerta", familia, caso))
        # Con varias familias esperadas, cualquiera cuenta como acierto (tests/golden/README.md): el caso se
        # atribuye a las esperadas que sí se alertaron; si no se alertó ninguna, falta en todas.
        for familia in (caso.esperadas & alertadas) or caso.esperadas:
            if familia not in conteos:
                continue
            conteos[familia].relevantes += 1
            if familia in alertadas:
                conteos[familia].cubiertos += 1
            else:
                errores.append(Error("no_alertado", familia, caso))
        total = conteos[TOTAL]
        if alertadas:
            total.alertas += 1
            total.verdaderos += any(caso.correcta(f) for f in alertadas)
        if caso.encaja:
            total.relevantes += 1
            cubierto = bool(alertadas & caso.esperadas) if caso.esperadas else bool(alertadas)
            total.cubiertos += cubierto
            if not cubierto and not caso.esperadas:
                errores.append(Error("no_alertado", TOTAL, caso))
    errores.sort(key=lambda e: (e.familia, e.tipo, e.caso.nro_sicop))
    return Medicion(reglas.version, casos, conteos, errores)


def guardar(conn: sqlite3.Connection, m: Medicion, ahora: datetime) -> tuple[int, bool]:
    """Guarda la medición. Si la última guardada tiene la misma versión y los mismos conteos, no repite:
    devuelve (id de esa medición, False). Si no, (id nuevo, True)."""
    filas = {f: (c.alertas, c.verdaderos, c.relevantes, c.cubiertos) for f, c in m.por_familia.items()}
    ultima = conn.execute("SELECT id, rules_version, casos_golden, casos_revision FROM rule_score_runs"
                          " ORDER BY id DESC LIMIT 1").fetchone()
    if ultima and ultima[1:] == (m.version, m.contar("golden"), m.contar("revisión")):
        anteriores = {f: tuple(v) for f, *v in conn.execute(
            "SELECT familia, alertas, verdaderos, relevantes, cubiertos FROM rule_scores WHERE run_id = ?",
            (ultima[0],))}
        if anteriores == filas:
            return ultima[0], False
    conn.execute("BEGIN")
    try:
        run_id = conn.execute(
            "INSERT INTO rule_score_runs (rules_version, measured_at, casos_golden, casos_revision)"
            " VALUES (?, ?, ?, ?)",
            (m.version, ahora.isoformat(timespec="seconds"), m.contar("golden"), m.contar("revisión"))).lastrowid
        conn.executemany(
            "INSERT INTO rule_scores (run_id, familia, alertas, verdaderos, relevantes, cubiertos)"
            " VALUES (?, ?, ?, ?, ?, ?)", [(run_id, f, *v) for f, v in filas.items()])
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return run_id, True


@dataclass
class Historial:
    id: int
    version: str
    fecha: str
    casos_golden: int
    casos_revision: int
    total: Conteo


def historial(conn: sqlite3.Connection, limite: int = 20) -> list[Historial]:
    """Las últimas mediciones guardadas, con su total, de la más reciente a la más vieja."""
    return [Historial(i, v, f, g, r, Conteo(a, ve, re, cu)) for i, v, f, g, r, a, ve, re, cu in conn.execute(
        "SELECT m.id, m.rules_version, m.measured_at, m.casos_golden, m.casos_revision,"
        "       s.alertas, s.verdaderos, s.relevantes, s.cubiertos"
        " FROM rule_score_runs m JOIN rule_scores s ON s.run_id = m.id AND s.familia = ''"
        " ORDER BY m.id DESC LIMIT ?", (limite,))]
