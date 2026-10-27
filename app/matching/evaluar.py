"""Evaluación de carteles con las reglas: encaje comercial, plazo y calidad de datos (guía, sección 16.4).

Cómo se decide el encaje de una familia en un cartel:
1. Se buscan sus términos en el título y en el nombre de catálogo de cada línea.
2. Una exclusión en el título anula la familia para todo el cartel (sin_coincidencia, con la evidencia).
   Una exclusión en una línea solo anula las señales de esa línea.
3. Con lo que queda: una señal alta → alta; una señal media junto a otra señal media distinta o a un
   término de contexto → media; una señal media sola → baja. Sin señales no se guarda nada.
4. Texto de los PDF de la ficha (entrega 4C): cada página de un documento guardado es una fuente más, como una
   línea (una exclusión en la página anula solo esa página). Del PDF cuentan las señales altas y medias, no el
   contexto (los pliegos repiten palabras genéricas), y solo la primera página de cada término va a la evidencia.
   Decisiones de Ivania (2026-10-27): para alta hace falta una señal alta en el título o en las líneas (el PDF
   sube como máximo a media); y si la familia no tiene ninguna señal en el título ni en las líneas, lo del PDF la
   deja como máximo en baja (se ve en el detalle, no sale en los avisos). En la base real, «trazabilidad» y
   «etiquetas» en el pliego de unos abarrotes la subían a media.

Las dimensiones van separadas: «alta» habla del encaje, no del plazo ni de si Hermatix puede ganar.
Reevaluar es idempotente: una fila por (cartel, familia, versión de reglas); si nada cambió, no se toca.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone

from app.matching.reglas import Coincidencia, Familia, Reglas, buscar

ENCAJES = ("alta", "media", "baja", "sin_coincidencia")
DIAS_POR_CERRAR = 7


@dataclass(frozen=True)
class Texto:
    fuente: str  # «título» o «línea 3»
    texto: str


@dataclass(frozen=True)
class Evaluacion:
    familia: str
    producto: str
    encaje: str
    regla: str       # términos del YAML que decidieron, con su tipo
    evidencia: str   # frases exactas del texto original, con su fuente


def _describir(pares: list[tuple[str, Coincidencia]]) -> tuple[str, str]:
    orden = {"exclusiones": 0, "senales_alta": 1, "senales_media": 2, "contexto": 3}
    pares = sorted(pares, key=lambda p: orden[p[1].tipo])
    regla = " + ".join(dict.fromkeys(f"{c.tipo}: {c.termino}" for _, c in pares))
    evidencia = " · ".join(dict.fromkeys(f"«{c.frase}» ({fuente})" for fuente, c in pares))
    return regla, evidencia


def fuente_pagina(documento: str, pagina: int) -> str:
    """«Pliego (v2).pdf», 3 → «Pliego v2.pdf, pág. 3». Sin paréntesis ni comillas: la fuente va entre paréntesis en
    la evidencia y panel.frases_de_evidencia la separa por ellos."""
    nombre = " ".join(documento.translate(str.maketrans("", "", "()«»")).split()) or "documento"
    return f"{nombre}, pág. {pagina}"


def evaluar_familia(familia: Familia, titulo: Texto, lineas: list[Texto],
                    paginas: list[Texto] | tuple[Texto, ...] = ()) -> Evaluacion | None:
    en_titulo = buscar(familia, titulo.texto)
    exclusiones = [(titulo.fuente, c) for c in en_titulo if c.tipo == "exclusiones"]
    senales = [(titulo.fuente, c) for c in en_titulo if c.tipo != "exclusiones"]
    for linea in lineas:
        en_linea = buscar(familia, linea.texto)
        if not any(c.tipo == "exclusiones" for c in en_linea):
            senales.extend((linea.fuente, c) for c in en_linea)
    alta_sin_pdf = any(c.tipo == "senales_alta" for _, c in senales)
    senal_sin_pdf = alta_sin_pdf or any(c.tipo == "senales_media" for _, c in senales)

    vistos: set[str] = set()  # del PDF, solo la primera página de cada término
    for pagina in paginas:
        en_pagina = buscar(familia, pagina.texto)
        if any(c.tipo == "exclusiones" for c in en_pagina):
            continue
        for c in en_pagina:
            if c.tipo in ("senales_alta", "senales_media") and c.termino not in vistos:
                vistos.add(c.termino)
                senales.append((pagina.fuente, replace(c, frase=" ".join(c.frase.split()))))

    alta = [p for p in senales if p[1].tipo == "senales_alta"]
    media = [p for p in senales if p[1].tipo == "senales_media"]
    contexto = [p for p in senales if p[1].tipo == "contexto"]
    if not alta and not media:
        return None  # el contexto solo no crea coincidencia

    if exclusiones:
        encaje, decisivos = "sin_coincidencia", exclusiones + alta + media
    elif alta:
        # Una señal alta que está solo en el PDF da como máximo media (regla 4).
        encaje, decisivos = ("alta" if alta_sin_pdf else "media"), alta + media + contexto
    elif len({c.termino for _, c in media}) >= 2 or contexto:
        encaje, decisivos = "media", media + contexto
    else:
        encaje, decisivos = "baja", media
    if encaje in ("alta", "media") and not senal_sin_pdf:
        encaje = "baja"  # solo el PDF, sin señal en el título ni en las líneas: se ve, pero no es candidato
    regla, evidencia = _describir(decisivos)
    return Evaluacion(familia.nombre, familia.producto, encaje, regla, evidencia)


def evaluar_textos(reglas: Reglas, titulo: str, lineas: list[Texto] | None = None,
                   paginas: list[Texto] | None = None) -> list[Evaluacion]:
    """Evaluación de un cartel con todas las familias; solo devuelve las que tuvieron señales."""
    t = Texto("título", titulo or "")
    resultado = (evaluar_familia(f, t, lineas or [], paginas or ()) for f in reglas.familias)
    return [e for e in resultado if e is not None]


def plazo_estado(cierre: str | None, ahora: datetime) -> str:
    """abierto · cierra_7_dias · vencido · por_verificar (sin fecha o fecha ilegible)."""
    if not cierre:
        return "por_verificar"
    try:
        fecha = datetime.fromisoformat(cierre)
    except ValueError:
        return "por_verificar"
    if fecha.tzinfo is None:
        return "por_verificar"  # sin zona no se puede comparar con seguridad
    if fecha <= ahora:
        return "vencido"
    if fecha - ahora <= timedelta(days=DIAS_POR_CERRAR):
        return "cierra_7_dias"
    return "abierto"


def calidad_datos(total_lineas: int, sin_catalogo: int) -> str:
    """completo · sin_lineas · codigo_sin_catalogo. («archivo_parcial» aún no se puede detectar.)"""
    if total_lineas == 0:
        return "sin_lineas"
    if sin_catalogo:
        return "codigo_sin_catalogo"
    return "completo"


@dataclass
class ResultadoEvaluacion:
    version: str
    carteles: int = 0
    nuevas: int = 0
    actualizadas: int = 0
    sin_cambios: int = 0
    retiradas: int = 0  # familias que ya no coinciden con esta versión (se marcan, no se borran)
    por_encaje: dict[str, dict[str, int]] = field(default_factory=dict)  # familia → encaje → n


def evaluar_base(conn: sqlite3.Connection, reglas: Reglas, ahora: datetime | None = None,
                 nro_sicop: str | None = None) -> ResultadoEvaluacion:
    """Evalúa todos los carteles (o uno) y guarda en opportunity_assessments, en una sola transacción."""
    ahora = ahora or datetime.now(timezone.utc)
    instante = ahora.isoformat(timespec="seconds")
    filtro, params = ("WHERE nro_sicop = ?", (nro_sicop,)) if nro_sicop else ("", ())

    lineas: dict[str, list[Texto]] = defaultdict(list)
    conteo: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # total, sin catálogo
    for nro, numero, nombre, estado in conn.execute(
        f"SELECT nro_sicop, numero_linea, nombre_catalogo, estado_catalogo FROM v_tender_lines {filtro}"
        " ORDER BY nro_sicop, CAST(numero_linea AS INTEGER)", params
    ):
        conteo[nro][0] += 1
        if estado != "en_catalogo":
            conteo[nro][1] += 1
        elif nombre:
            lineas[nro].append(Texto(f"línea {numero}", nombre))

    # Texto de los PDF guardados de la ficha (regla 4). Solo existe para los carteles enriquecidos.
    paginas: dict[str, list[Texto]] = defaultdict(list)
    for nro, documento, pagina, texto in conn.execute(
        "SELECT d.nro_sicop, coalesce(nullif(x.archivo_interno, ''), d.nombre_documento, d.nombre_original, d.server_file),"
        "       x.pagina, x.texto FROM tender_document_text x JOIN tender_documents d ON d.id = x.documento_id"
        f" WHERE d.estado = 'guardado' {'AND d.nro_sicop = ?' if nro_sicop else ''}"
        " ORDER BY d.nro_sicop, d.id, x.archivo_interno, x.pagina", params
    ):
        paginas[nro].append(Texto(fuente_pagina(documento, pagina), texto))

    previas: dict[tuple[str, str], tuple] = {}
    # Familias evaluadas antes, por cartel: así cada cartel revisa solo las suyas (antes recorría todas las
    # previas de la base por cada cartel, y con miles de carteles eso se volvía lento).
    familias_previas: dict[str, list[str]] = defaultdict(list)
    for fila in conn.execute(
        f"SELECT nro_sicop, familia, producto, encaje, regla, evidencia, plazo_estado, calidad_datos"
        f" FROM opportunity_assessments WHERE rules_version = ? {filtro.replace('WHERE', 'AND')}",
        (reglas.version, *params),
    ):
        previas[(fila[0], fila[1])] = tuple(fila[2:])
        familias_previas[fila[0]].append(fila[1])

    r = ResultadoEvaluacion(reglas.version)
    carteles = conn.execute(f"SELECT nro_sicop, descripcion, fecha_cierre_recepcion FROM tenders {filtro}",
                            params).fetchall()
    conn.execute("BEGIN")
    try:
        for nro, descripcion, cierre in carteles:
            r.carteles += 1
            plazo = plazo_estado(cierre, ahora)
            total, sin_cat = conteo.get(nro, (0, 0))
            calidad = calidad_datos(total, sin_cat)
            vigentes = set()
            for e in evaluar_textos(reglas, descripcion, lineas.get(nro), paginas.get(nro)):
                vigentes.add(e.familia)
                r.por_encaje.setdefault(e.familia, {}).setdefault(e.encaje, 0)
                r.por_encaje[e.familia][e.encaje] += 1
                _guardar(conn, r, previas, nro, e.familia,
                         (e.producto, e.encaje, e.regla, e.evidencia, plazo, calidad), reglas.version, instante)
            for familia in familias_previas.get(nro, []):
                previa = previas[(nro, familia)]
                if familia not in vigentes and previa[1:3] != ("sin_coincidencia", "sin señales"):
                    _guardar(conn, r, previas, nro, familia,
                             (previa[0], "sin_coincidencia", "sin señales", "—", plazo, calidad),
                             reglas.version, instante, retirada=True)
        if nro_sicop is None:  # solo una evaluación completa deja al día lo importado (ver migración 0008)
            conn.execute("INSERT INTO evaluation_runs (rules_version, evaluated_at, carteles) VALUES (?, ?, ?)",
                         (reglas.version, instante, r.carteles))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return r


def _guardar(conn, r: ResultadoEvaluacion, previas, nro, familia, valores, version, instante, retirada=False):
    previa = previas.get((nro, familia))
    if previa == valores:
        r.sin_cambios += 1
        return
    if previa is None:
        r.nuevas += 1
    elif retirada:
        r.retiradas += 1
    else:
        r.actualizadas += 1
    # Fila nueva o actualización en su lugar (no se borra: un aviso puede apuntar a ella).
    conn.execute(
        "INSERT INTO opportunity_assessments (nro_sicop, familia, producto, encaje, regla, evidencia,"
        " plazo_estado, calidad_datos, rules_version, evaluated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (nro_sicop, familia, rules_version) DO UPDATE SET producto = excluded.producto,"
        " encaje = excluded.encaje, regla = excluded.regla, evidencia = excluded.evidencia,"
        " plazo_estado = excluded.plazo_estado, calidad_datos = excluded.calidad_datos,"
        " evaluated_at = excluded.evaluated_at",
        (nro, familia, *valores, version, instante),
    )
