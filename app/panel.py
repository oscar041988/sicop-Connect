"""Consultas del panel web: lista de oportunidades, detalle y revisión humana. Sin HTML.

* Se muestra la última versión de reglas evaluada (la de `evaluate` más reciente).
* El plazo se calcula al mostrar, con la hora actual: el guardado al evaluar envejece.
* Una revisión nunca se borra ni se modifica: cada decisión es una fila nueva y la vigente es la última.
  Está ligada al Número SICOP, que no cambia al reimportar.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from markupsafe import Markup, escape

from app.compras import Compra, detalle_compra
from app.dinero import Monto, parse_decimal, totales_por_moneda
from app.importers.comun import HORA_CR
from app.matching.evaluar import DIAS_POR_CERRAR, plazo_estado

POR_PAGINA = 25
ENCAJES = {"alta": "Alta", "media": "Media", "baja": "Baja", "sin_coincidencia": "Sin coincidencia"}
PRIORIDADES = {  # opción del filtro → encajes que incluye
    "candidatos": ("alta", "media"),
    "alta": ("alta",),
    "media": ("media",),
    "baja": ("baja",),
    "sin_coincidencia": ("sin_coincidencia",),
    "todas": tuple(ENCAJES),
}
PLAZOS = {"cierra_7_dias": "Cierra en 7 días o menos", "abierto": "Abierto", "por_verificar": "Por verificar",
          "vencido": "Vencido"}
CALIDADES = {"completo": "Completo", "sin_lineas": "Sin líneas", "codigo_sin_catalogo": "Código sin catálogo",
             "archivo_parcial": "Archivo parcial"}
DECISIONES = {"interesa": "Interesa", "no_interesa": "No interesa", "revisar_requisitos": "Revisar requisitos"}
MOTIVOS = {"no_encaja": "No encaja con el portafolio", "plazo": "Plazo", "requisitos": "Requisitos",
           "presupuesto": "Presupuesto", "otro": "Otro"}
NOMBRES_FAMILIA = {  # solo para mostrar; las claves son las del YAML
    "gps_flotas": "GPS y gestión de flotas",
    "videotelematica": "Videotelemática",
    "seguridad_vial": "Seguridad vial",
    "conteo_pasajeros": "Conteo de pasajeros",
    "transporte_corporativo": "Transporte corporativo",
    "rastreo_activos": "Rastreo de activos",
    "mantenimiento_flotas": "Mantenimiento de flotas",
    "iot_frio": "IoT y cadena de frío",
    "camaras_corporales": "Cámaras corporales",
}
CANDIDATOS = PRIORIDADES["candidatos"]
MAX_COMENTARIO = 2000

# Mismos cortes que plazo_estado (app/matching/evaluar.py). julianday() entiende el «-06:00» de las fechas;
# una fecha sin zona horaria queda «por verificar», igual que en Python.
_PLAZO_SQL = f"""
    CASE
        WHEN t.fecha_cierre_recepcion IS NULL
          OR t.fecha_cierre_recepcion NOT GLOB '*[+-][0-9][0-9]:[0-9][0-9]'
          OR julianday(t.fecha_cierre_recepcion) IS NULL THEN 'por_verificar'
        WHEN julianday(t.fecha_cierre_recepcion) <= julianday(:ahora) THEN 'vencido'
        WHEN julianday(t.fecha_cierre_recepcion) - julianday(:ahora) <= {DIAS_POR_CERRAR} THEN 'cierra_7_dias'
        ELSE 'abierto'
    END"""


class RevisionInvalida(ValueError):
    """La revisión no se guarda; el mensaje es el que verá la persona."""


@dataclass
class Filtros:
    prioridad: str = "candidatos"
    familia: str = ""
    institucion: str = ""
    plazo: str = ""
    revisado: str = ""   # "" · "si" · "no" · o una decisión: "interesa", "no_interesa", "revisar_requisitos"
    tipo: str = ""
    q: str = ""          # búsqueda en título, institución o Número SICOP
    pagina: int = 1

    def limpios(self) -> Filtros:
        """Descarta valores que no existen en las listas, para no fallar con una URL editada a mano."""
        return Filtros(
            prioridad=self.prioridad if self.prioridad in PRIORIDADES else "candidatos",
            familia=self.familia, institucion=self.institucion,
            plazo=self.plazo if self.plazo in PLAZOS else "",
            revisado=self.revisado if self.revisado in ("si", "no", *DECISIONES) else "",
            tipo=self.tipo,
            q=self.q.strip()[:100],
            pagina=max(1, self.pagina),
        )


@dataclass
class FilaLista:
    nro_sicop: str
    descripcion: str | None
    institucion: str | None
    familia: str
    producto: str | None
    encaje: str
    plazo: str
    fecha_cierre: str | None
    tipo_procedimiento: str | None
    decision: str | None  # última revisión, si hay
    nro_procedimiento: str | None
    fecha_publicacion: str | None
    regla: str | None
    evidencia: str
    es_nuevo: bool        # apareció por primera vez en la última importación de carteles
    estimado: dict[str, Monto] = field(default_factory=dict)  # total de las líneas, por moneda

    @property
    def frases(self) -> list[str]:
        """Frases exactas que coincidieron, sin repetir: «MONITOREO GPS», «flotilla»…"""
        vistas: list[str] = []
        for lista in frases_de_evidencia(self.evidencia).values():
            vistas.extend(x for x in lista if x.lower() not in {v.lower() for v in vistas})
        return vistas


@dataclass
class Pagina:
    filas: list[FilaLista]
    total: int
    pagina: int
    paginas: int


@dataclass
class Evaluacion:
    familia: str
    producto: str | None
    encaje: str
    regla: str | None
    evidencia: str
    calidad_datos: str | None


@dataclass
class Revision:
    decision: str
    motivo: str | None
    comentario: str | None
    responsable: str
    fecha: str
    escrito_a_mano: bool  # antes del login (lección 6) el responsable se escribía a mano; no hay user_id


@dataclass
class Cobertura:
    origen: str | None          # real · sintetico · simulado
    archivo: str | None
    importado: str | None
    primera_vez: str
    ultima_vez: str


@dataclass
class Detalle:
    compra: Compra
    tipo_procedimiento: str | None
    plazo: str
    evaluaciones: list[Evaluacion]
    revisiones: list[Revision]
    cobertura: Cobertura
    frases: dict[str, list[str]] = field(default_factory=dict)  # fuente («título», «línea 2») → frases


def version_vigente(conn: sqlite3.Connection) -> str | None:
    fila = conn.execute("SELECT rules_version FROM opportunity_assessments ORDER BY id DESC LIMIT 1").fetchone()
    return fila[0] if fila else None


def _base_sql() -> str:
    return f"""
        WITH base AS (
            SELECT a.nro_sicop, t.descripcion, i.nombre AS institucion, t.institution_cedula AS cedula,
                   a.familia, a.producto, a.encaje, {_PLAZO_SQL} AS plazo,
                   t.fecha_cierre_recepcion AS cierre, t.tipo_procedimiento AS tipo,
                   (SELECT r.decision FROM reviews r WHERE r.nro_sicop = a.nro_sicop ORDER BY r.id DESC LIMIT 1)
                       AS decision,
                   t.nro_procedimiento, t.fecha_publicacion, a.regla, a.evidencia,
                   t.first_import_id IS NOT NULL AND t.first_import_id = (
                       SELECT max(id) FROM imports WHERE report = 'carteles') AS es_nuevo
            FROM opportunity_assessments a
            JOIN tenders t ON t.nro_sicop = a.nro_sicop
            LEFT JOIN institutions i ON i.cedula = t.institution_cedula
            WHERE a.rules_version = :version
        )"""


def listar(conn: sqlite3.Connection, version: str, filtros: Filtros, ahora: datetime) -> Pagina:
    f = filtros.limpios()
    encajes = PRIORIDADES[f.prioridad]
    condiciones = [f"encaje IN ({', '.join(f':e{n}' for n in range(len(encajes)))})"]
    params: dict[str, object] = {"version": version, "ahora": ahora.isoformat(timespec="seconds"),
                                 **{f"e{n}": e for n, e in enumerate(encajes)}}
    for campo, valor in (("familia", f.familia), ("cedula", f.institucion), ("plazo", f.plazo), ("tipo", f.tipo)):
        if valor:
            condiciones.append(f"{campo} = :{campo}")
            params[campo] = valor
    if f.revisado == "si":
        condiciones.append("decision IS NOT NULL")
    elif f.revisado == "no":
        condiciones.append("decision IS NULL")
    elif f.revisado:
        condiciones.append("decision = :decision")
        params["decision"] = f.revisado
    if f.q:
        # LIKE sin distinguir mayúsculas (solo letras sin tilde); los comodines del usuario se toman literales.
        condiciones.append("(descripcion LIKE :q ESCAPE '!' OR institucion LIKE :q ESCAPE '!'"
                           " OR nro_sicop LIKE :q ESCAPE '!')")
        params["q"] = "%" + re.sub(r"([!%_])", r"!\1", f.q) + "%"
    donde = " AND ".join(condiciones)

    total = conn.execute(f"{_base_sql()} SELECT count(*) FROM base WHERE {donde}", params).fetchone()[0]
    paginas = max(1, -(-total // POR_PAGINA))
    pagina = min(f.pagina, paginas)
    filas = conn.execute(
        f"""{_base_sql()}
        SELECT nro_sicop, descripcion, institucion, familia, producto, encaje, plazo, cierre, tipo, decision,
               nro_procedimiento, fecha_publicacion, regla, evidencia, es_nuevo
        FROM base WHERE {donde}
        ORDER BY CASE plazo WHEN 'cierra_7_dias' THEN 0 WHEN 'abierto' THEN 1 WHEN 'por_verificar' THEN 2 ELSE 3 END,
                 CASE WHEN plazo = 'vencido' THEN -julianday(cierre) ELSE julianday(cierre) END,
                 nro_sicop, familia
        LIMIT :limite OFFSET :desde""",
        {**params, "limite": POR_PAGINA, "desde": (pagina - 1) * POR_PAGINA},
    ).fetchall()
    resultado = [FilaLista(*fila[:-1], es_nuevo=bool(fila[-1])) for fila in filas]
    montos = estimados(conn, [f.nro_sicop for f in resultado])
    for fila in resultado:
        fila.estimado = montos.get(fila.nro_sicop, {})
    return Pagina(resultado, total, pagina, paginas)


def estimados(conn: sqlite3.Connection, nros: list[str]) -> dict[str, dict[str, Monto]]:
    """Suma de cantidad × precio de las líneas de cada cartel, separada por moneda (en Python, con Decimal)."""
    if not nros:
        return {}
    marcas = ", ".join("?" * len(nros))
    por_cartel: dict[str, list[Monto]] = {}
    for nro, valor, moneda in conn.execute(
        f"SELECT nro_sicop, estimado_linea, moneda FROM tender_lines WHERE nro_sicop IN ({marcas})"
        " AND estimado_linea IS NOT NULL AND moneda IS NOT NULL", nros,
    ):
        por_cartel.setdefault(nro, []).append(Monto(parse_decimal(valor), moneda))
    return {nro: totales_por_moneda(m) for nro, m in por_cartel.items()}


def cuenta_regresiva(cierre: str | None, ahora: datetime) -> str:
    """Texto corto para el plazo: «Cierra en 3 días», «Cierra hoy», «Cerró hace 12 días»."""
    try:
        fecha = datetime.fromisoformat(cierre) if cierre else None
    except ValueError:
        fecha = None
    if fecha is None or fecha.tzinfo is None:
        return "Sin fecha de cierre"
    falta = fecha - ahora
    if falta <= timedelta(0):
        dias = (-falta).days
        return "Cerró hoy" if dias == 0 else f"Cerró hace {dias} día{'s' if dias != 1 else ''}"
    if falta < timedelta(days=1):
        horas = int(falta.total_seconds() // 3600)
        return f"Cierra en {horas} h" if horas else "Cierra en menos de 1 h"
    dias = falta.days
    return f"Cierra en {dias} día{'s' if dias != 1 else ''}"


def opciones_filtros(conn: sqlite3.Connection, version: str) -> dict[str, list[tuple[str, str]]]:
    """Valores que existen en la versión vigente, para los menús del filtro: (valor, texto)."""
    familias = [(f, f) for (f,) in conn.execute(
        "SELECT DISTINCT familia FROM opportunity_assessments WHERE rules_version = ? ORDER BY familia", (version,))]
    instituciones = [(c, n or c) for c, n in conn.execute(
        "SELECT DISTINCT t.institution_cedula, i.nombre FROM opportunity_assessments a"
        " JOIN tenders t USING (nro_sicop) LEFT JOIN institutions i ON i.cedula = t.institution_cedula"
        " WHERE a.rules_version = ? AND t.institution_cedula IS NOT NULL ORDER BY coalesce(i.nombre, t.institution_cedula)",
        (version,))]
    tipos = [(t, t) for (t,) in conn.execute(
        "SELECT DISTINCT t.tipo_procedimiento FROM opportunity_assessments a JOIN tenders t USING (nro_sicop)"
        " WHERE a.rules_version = ? AND t.tipo_procedimiento IS NOT NULL ORDER BY 1", (version,))]
    return {"familias": familias, "instituciones": instituciones, "tipos": tipos}


_EVIDENCIA = re.compile(r"«(.+?)» \(([^()]+)\)")


def frases_de_evidencia(evidencia: str) -> dict[str, list[str]]:
    """«MONITOREO GPS» (título) · «GPS» (línea 1) → {"título": ["MONITOREO GPS"], "línea 1": ["GPS"]}."""
    frases: dict[str, list[str]] = {}
    for frase, fuente in _EVIDENCIA.findall(evidencia or ""):
        if frase not in frases.setdefault(fuente, []):
            frases[fuente].append(frase)
    return frases


# Siglas que se conservan al pasar un título en MAYÚSCULAS a mayúscula inicial (solo para mostrar).
SIGLAS = {
    "GPS", "RFID", "BLE", "IOT", "LCD", "LED", "USB", "CCTV", "DVR", "MDVR", "NVR", "ADAS", "DMS", "DSM", "HD", "UPS",
    "TI", "TIC", "AC", "LTE", "4G", "GNSS", "RTK", "LIDAR", "SLAM", "API", "PVC", "ISO", "IP", "SICOP", "CCSS", "ICE",
    "INS", "UCR", "TEC", "UNA", "UNED", "MOPT", "MEP", "MSP", "OIJ", "CNFL", "RECOPE", "AYA", "JAPDEVA", "INCOFER",
    "CTP", "ARESEP", "BCR", "BNCR", "CCDR", "CCDRSC", "CIBCM", "MICITT", "DINADECO", "URHN", "SGAB", "DGAB", "LANAMME",
    "LANAMMEUCR", "INA", "IMAS", "INVU", "COSEVI", "SENASA", "MAG", "MINAE", "CNE", "PANI", "SUTEL", "CR",
}
ESCRITURA_ESPECIAL = {"IOT": "IoT", "AYA": "AyA", "LANAMMEUCR": "LanammeUCR"}
_PALABRA = re.compile(r"[^\W_]+")
_ROMANO = re.compile(r"^(?:I{1,3}|IV|V|VI{0,3}|IX|X)$")


def _casi_todo_mayusculas(texto: str) -> bool:
    letras = [c for c in texto if c.isalpha()]
    return len(letras) >= 4 and sum(c.isupper() for c in letras) / len(letras) > 0.7


def formato_titulo(texto: str | None) -> str:
    """«COMPRA DE CÁMARAS CORPORALES PARA LA CCSS» → «Compra de cámaras corporales para la CCSS».

    Solo cambia títulos escritos casi todo en mayúsculas; conserva siglas conocidas, palabras con números
    (códigos como SM5697) y números romanos. Un título que ya trae minúsculas solo recibe mayúscula inicial
    (sus otras mayúsculas pueden ser nombres propios). Solo para mostrar.
    """
    texto = texto or ""
    salida = list(texto)
    if not _casi_todo_mayusculas(texto):
        return _mayuscula_inicial(salida)
    # Un bloque sin espacios que tenga números es un código (L-352-2026, SM5697, 2026LD-000001): se deja igual.
    codigos = [(m.start(), m.end()) for m in re.finditer(r"\S+", texto) if any(c.isdigit() for c in m.group(0))]
    for m in _PALABRA.finditer(texto):
        palabra = m.group(0)
        if any(a <= m.start() < b for a, b in codigos):
            continue
        if palabra.upper() in ESCRITURA_ESPECIAL:
            nuevo = ESCRITURA_ESPECIAL[palabra.upper()]
        elif palabra.upper() in SIGLAS or any(c.isdigit() for c in palabra) or _ROMANO.match(palabra):
            nuevo = palabra
        else:
            nuevo = palabra.lower()
        if len(nuevo) != len(palabra):  # algunas letras cambian de largo al pasar a minúscula: se deja igual
            nuevo = palabra
        salida[m.start():m.end()] = nuevo
    return _mayuscula_inicial(salida)


def _mayuscula_inicial(letras: list[str]) -> str:
    for i, c in enumerate(letras):
        if c.isalpha():
            if len(c.upper()) == 1:
                letras[i] = c.upper()
            break
    return "".join(letras)


def legible(texto: str | None) -> str:
    """Para mostrar: los espacios duros (NBSP) de SICOP pasan a espacios normales, así el navegador puede
    cortar la línea. El texto guardado no cambia."""
    return (texto or "").replace(" ", " ")


def resaltar(texto: str | None, frases: list[str] | None, titulo: bool = False) -> Markup:
    """Escapa el texto y marca las frases de la evidencia con <mark>. Nunca deja HTML del texto sin escapar.
    Las frases se buscan en el texto original; al mostrar, los espacios duros pasan a normales y, si es un
    título, se aplica formato_titulo (mismo largo, así las marcas caen en el mismo lugar)."""
    texto = texto or ""
    visible = formato_titulo(texto) if titulo else texto
    tramos: list[tuple[int, int]] = []
    for frase in sorted(set(frases or []), key=len, reverse=True):
        inicio = texto.find(frase)
        while frase and inicio != -1:
            fin = inicio + len(frase)
            if not any(a < fin and inicio < b for a, b in tramos):
                tramos.append((inicio, fin))
            inicio = texto.find(frase, fin)
    partes, cursor = [], 0
    for a, b in sorted(tramos):
        partes.append(escape(legible(visible[cursor:a])))
        partes.append(Markup("<mark>") + escape(legible(visible[a:b])) + Markup("</mark>"))
        cursor = b
    partes.append(escape(legible(visible[cursor:])))
    return Markup("").join(partes)


def detalle(conn: sqlite3.Connection, nro_sicop: str, version: str | None, ahora: datetime) -> Detalle | None:
    compra = detalle_compra(conn, nro_sicop)
    if compra is None:
        return None
    tipo, primera, ultima, origen, archivo, importado = conn.execute(
        "SELECT t.tipo_procedimiento, t.first_seen, t.last_seen, i.data_origin, i.file_name, i.imported_at"
        " FROM tenders t LEFT JOIN imports i ON i.id = t.last_import_id WHERE t.nro_sicop = ?", (nro_sicop,)
    ).fetchone()
    evaluaciones = [Evaluacion(*fila) for fila in conn.execute(
        "SELECT familia, producto, encaje, regla, evidencia, calidad_datos FROM opportunity_assessments"
        " WHERE nro_sicop = ? AND rules_version = ?"
        " ORDER BY CASE encaje WHEN 'alta' THEN 0 WHEN 'media' THEN 1 WHEN 'baja' THEN 2 ELSE 3 END, familia",
        (nro_sicop, version),
    )]
    revisiones = [Revision(*fila) for fila in conn.execute(
        "SELECT decision, motivo, comment, responsable, created_at, user_id IS NULL FROM reviews"
        " WHERE nro_sicop = ? ORDER BY id DESC",
        (nro_sicop,),
    )]
    frases: dict[str, list[str]] = {}
    for e in evaluaciones:
        for fuente, lista in frases_de_evidencia(e.evidencia).items():
            frases.setdefault(fuente, []).extend(x for x in lista if x not in frases.get(fuente, []))
    return Detalle(compra, tipo, plazo_estado(compra.fecha_cierre_recepcion, ahora), evaluaciones, revisiones,
                   Cobertura(origen, archivo, importado, primera, ultima), frases)


def guardar_revision(conn: sqlite3.Connection, nro_sicop: str, decision: str, motivo: str, comentario: str,
                     user_id: int, ahora: datetime) -> None:
    """Agrega una revisión (nunca cambia ni borra las anteriores). Lanza RevisionInvalida si falta algo.

    El responsable es el usuario de la sesión (user_id); su nombre se copia en «responsable» para que el
    historial diga quién decidió aunque después cambie el nombre del usuario.
    """
    decision, motivo, comentario = decision.strip(), motivo.strip(), comentario.strip()
    usuario = conn.execute("SELECT coalesce(nombre, email) FROM users WHERE id = ? AND active = 1",
                           (user_id,)).fetchone()
    if usuario is None:
        raise RevisionInvalida("Tu usuario no existe o está desactivado. Vuelve a iniciar sesión.")
    if conn.execute("SELECT 1 FROM tenders WHERE nro_sicop = ?", (nro_sicop,)).fetchone() is None:
        raise RevisionInvalida(f"No existe el cartel {nro_sicop}.")
    if decision not in DECISIONES:
        raise RevisionInvalida("Elige una decisión: Interesa, No interesa o Revisar requisitos.")
    if decision == "no_interesa":
        if motivo not in MOTIVOS:
            raise RevisionInvalida("Para «No interesa» hay que elegir el motivo.")
    else:
        motivo = ""  # el motivo solo se guarda con «No interesa»
    if len(comentario) > MAX_COMENTARIO:
        raise RevisionInvalida(f"El comentario admite hasta {MAX_COMENTARIO} caracteres.")
    conn.execute(
        "INSERT INTO reviews (nro_sicop, user_id, responsable, decision, motivo, comment, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nro_sicop, user_id, usuario[0], decision, motivo or None, comentario or None,
         ahora.astimezone(HORA_CR).isoformat(timespec="seconds")),
    )


def fecha_cr(iso: str | None) -> str:
    """«2026-10-12T10:00:00-06:00» → «12/10/2026 10:00», en hora de Costa Rica."""
    if not iso:
        return "—"
    try:
        fecha = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(HORA_CR)
    return fecha.strftime("%d/%m/%Y %H:%M")


def monto(valor, moneda: str | None) -> str:
    """Decimal con separador de miles (espacio) y su moneda: «565 920.00 CRC». Nunca convierte monedas."""
    if valor is None:
        return "—"
    return f"{valor:,.2f}".replace(",", " ") + (f" {moneda}" if moneda else "")
