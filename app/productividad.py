"""Productividad de la revisión (Ivania, 2026-11-17; maqueta aprobada por Ivania, opciones provisionales hasta Oscar).

Por semana (lunes 00:00 a domingo 23:59, hora de Costa Rica):
* Candidatos nuevos: carteles vistos por primera vez en la semana con prioridad Alta o Media en la versión vigente
  (igual que «Nuevas oportunidades» del resumen semanal). Un cartel cuenta una vez aunque tenga varias familias.
* Cada candidato queda en uno solo de estos grupos:
  revisado (su primera revisión fue antes del cierre, o no tiene cierre) · cerró sin revisión (el cierre ya pasó
  sin revisión antes de él) · abierto sin revisar.
* Por persona (solo administradores, en la página): primeras revisiones de candidatos hechas en la semana, a nombre
  de quien la hizo, con la decisión de esa revisión, los días desde que el cartel entró al panel y cuántas se
  hicieron el mismo día del cierre o después.

Los carteles no se asignan: «cerró sin revisión» es del equipo, no de una persona. Solo lee la base.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.importers.comun import HORA_CR

SEMANAS_HISTORIAL = 4
DIAS_CIERRE_PRONTO = 7
# Columnas de «Por persona»: la decisión de la primera revisión, agrupada.
GRUPOS = {"interesa": "interesa", "ofertada": "interesa", "revisar_requisitos": "revisar",
          "no_interesa": "no", "no_se_oferta": "no"}


@dataclass
class Escapado:
    nro_sicop: str
    titulo: str | None
    institucion: str | None
    encaje: str
    cierre: datetime
    dias_en_panel: int


@dataclass
class Semana:
    inicio: datetime        # lunes 00:00, hora de Costa Rica
    fin: datetime           # el lunes siguiente (no incluido)
    candidatos: int = 0
    revisados: int = 0
    escapados: list[Escapado] = field(default_factory=list)
    abiertos: int = 0
    abiertos_pronto: int = 0  # de los abiertos, los que cierran en 7 días o menos

    @property
    def ultimo_dia(self) -> date:
        return (self.fin - timedelta(days=1)).date()


@dataclass
class Persona:
    nombre: str
    revisados: int = 0
    interesa: int = 0
    revisar: int = 0
    no: int = 0
    al_cierre: int = 0
    _dias: list[Decimal] = field(default_factory=list)

    @property
    def dias_promedio(self) -> Decimal | None:
        if not self._dias:
            return None
        return (sum(self._dias) / len(self._dias)).quantize(Decimal("0.1"), ROUND_HALF_UP)


@dataclass
class Productividad:
    semana: Semana
    historial: list[Semana]   # las últimas SEMANAS_HISTORIAL, la más vieja primero (la elegida al final)
    personas: list[Persona]
    anterior: date            # lunes de la semana anterior
    siguiente: date | None    # lunes de la siguiente; None si la elegida es la semana en curso


def lunes(dia: date) -> datetime:
    """El lunes 00:00 (hora de Costa Rica) de la semana de ese día."""
    inicio = dia - timedelta(days=dia.weekday())
    return datetime(inicio.year, inicio.month, inicio.day, tzinfo=HORA_CR)


def _fecha(texto: str | None) -> datetime | None:
    """Fecha con zona; None si falta, es ilegible o no trae zona (no se compara sin zona)."""
    try:
        fecha = datetime.fromisoformat(texto) if texto else None
    except ValueError:
        return None
    return fecha if fecha is not None and fecha.tzinfo is not None else None


def _candidatos(conn: sqlite3.Connection, version: str, desde: datetime, hasta: datetime) -> list[tuple]:
    """(nro, título, institución, mejor encaje, primera vez, cierre) de los candidatos vistos por primera vez en el
    rango. El rango se compara con julianday: las fechas vienen en hora de Costa Rica o en UTC."""
    return conn.execute(
        "SELECT t.nro_sicop, t.descripcion, i.nombre,"
        "       CASE WHEN EXISTS (SELECT 1 FROM opportunity_assessments a WHERE a.nro_sicop = t.nro_sicop"
        "         AND a.rules_version = :version AND a.encaje = 'alta') THEN 'alta' ELSE 'media' END,"
        "       t.first_seen, t.fecha_cierre_recepcion"
        " FROM tenders t LEFT JOIN institutions i ON i.cedula = t.institution_cedula"
        " WHERE EXISTS (SELECT 1 FROM opportunity_assessments a WHERE a.nro_sicop = t.nro_sicop"
        "   AND a.rules_version = :version AND a.encaje IN ('alta', 'media'))"
        "   AND julianday(t.first_seen) >= julianday(:desde) AND julianday(t.first_seen) < julianday(:hasta)"
        " ORDER BY t.nro_sicop",
        {"version": version, "desde": desde.isoformat(), "hasta": hasta.isoformat()}).fetchall()


def _primeras_revisiones(conn: sqlite3.Connection) -> dict[str, tuple[datetime | None, str, str]]:
    """nro → (cuándo, decisión, quién) de la primera revisión de cada cartel. Nunca se borran (migración 0001)."""
    filas = conn.execute(
        "SELECT r.nro_sicop, r.created_at, r.decision, coalesce(u.nombre, r.responsable, 'Sin nombre')"
        " FROM reviews r LEFT JOIN users u ON u.id = r.user_id"
        " WHERE r.id IN (SELECT min(id) FROM reviews GROUP BY nro_sicop)").fetchall()
    return {nro: (_fecha(creada), decision, quien) for nro, creada, decision, quien in filas}


def calcular_semana(conn: sqlite3.Connection, version: str, inicio: datetime, ahora: datetime,
                    primeras: dict | None = None) -> Semana:
    primeras = _primeras_revisiones(conn) if primeras is None else primeras
    s = Semana(inicio, inicio + timedelta(days=7))
    for nro, titulo, institucion, encaje, primera_vez, cierre_texto in _candidatos(conn, version, s.inicio, s.fin):
        s.candidatos += 1
        cierre = _fecha(cierre_texto)
        revision = primeras.get(nro)
        cuando = revision[0] if revision else None
        if revision and (cierre is None or cuando is None or cuando <= cierre):
            s.revisados += 1
        elif cierre is not None and cierre <= ahora:
            visto = _fecha(primera_vez)
            dias = max(0, (cierre - visto).days) if visto else 0
            s.escapados.append(Escapado(nro, titulo, institucion, encaje, cierre, dias))
        else:
            s.abiertos += 1
            if cierre is not None and cierre - ahora <= timedelta(days=DIAS_CIERRE_PRONTO):
                s.abiertos_pronto += 1
    s.escapados.sort(key=lambda e: (e.cierre, e.nro_sicop))
    return s


def calcular_personas(conn: sqlite3.Connection, version: str, inicio: datetime, fin: datetime,
                      primeras: dict | None = None) -> list[Persona]:
    """Primeras revisiones hechas en la semana, de carteles Alta o Media (de cualquier semana), por persona."""
    primeras = _primeras_revisiones(conn) if primeras is None else primeras
    candidatos = {nro: (_fecha(vista), _fecha(cierre)) for nro, vista, cierre in conn.execute(
        "SELECT t.nro_sicop, t.first_seen, t.fecha_cierre_recepcion FROM tenders t"
        " WHERE EXISTS (SELECT 1 FROM opportunity_assessments a WHERE a.nro_sicop = t.nro_sicop"
        "   AND a.rules_version = ? AND a.encaje IN ('alta', 'media'))", (version,))}
    personas: dict[str, Persona] = {}
    for nro, (cuando, decision, quien) in primeras.items():
        if nro not in candidatos or cuando is None or not (inicio <= cuando < fin):
            continue
        visto, cierre = candidatos[nro]
        p = personas.setdefault(quien, Persona(quien))
        p.revisados += 1
        grupo = GRUPOS.get(decision)
        if grupo:
            setattr(p, grupo, getattr(p, grupo) + 1)
        if visto is not None:
            p._dias.append(Decimal(max(0, (cuando - visto).total_seconds())) / Decimal(86400))
        if cierre is not None and cuando.astimezone(HORA_CR).date() >= cierre.astimezone(HORA_CR).date():
            p.al_cierre += 1
    return sorted(personas.values(), key=lambda p: (-p.revisados, p.nombre))


def calcular(conn: sqlite3.Connection, version: str, ahora: datetime, semana: date | None = None) -> Productividad:
    """La semana elegida (por defecto, la última completa), su historial y las personas. Una semana futura se
    toma como la semana en curso."""
    actual = lunes(ahora.astimezone(HORA_CR).date())
    elegida = lunes(semana) if semana else actual - timedelta(days=7)
    elegida = min(elegida, actual)
    primeras = _primeras_revisiones(conn)
    historial = [calcular_semana(conn, version, elegida - timedelta(days=7 * n), ahora, primeras)
                 for n in range(SEMANAS_HISTORIAL - 1, -1, -1)]
    return Productividad(
        semana=historial[-1], historial=historial,
        personas=calcular_personas(conn, version, elegida, elegida + timedelta(days=7), primeras),
        anterior=(elegida - timedelta(days=7)).date(),
        siguiente=None if elegida >= actual else (elegida + timedelta(days=7)).date(),
    )
