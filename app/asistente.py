"""Asistente de elegibilidad (lección 3; migración 0031): recorre la lista de verificación y pregunta, sin suponer.

* Orden: primero los requisitos excluyentes y después el resto; dentro de cada grupo, el orden del pliego
  (verificacion.listar). «Multa / cláusula penal:» y «Condición de la institución:» no se preguntan: se muestran
  como información (son obligaciones del contrato, no requisitos para participar).
* La pregunta es la que redactó la IA (app/ai/asistente.py, una vez por cartel) o, si no hay, la que arma la app con
  el requisito, su mínimo y su cita. Siempre lleva la cita del pliego.
* Nada cuenta como respondido sin un clic de una persona: un dato del perfil vigente se MUESTRA y se confirma
  (confirmar_perfil); si venció, está pendiente o no existe, se pregunta.
* Las respuestas no se borran ni se modifican (triggers): cambiar una agrega otra y vale la última. La conversación
  se pausa sola y otra persona autorizada la retoma (quién puede entrar lo revisa la ruta: seguimiento.puede_entrar).
* Revisión rápida (migración 0034, decisión de Oscar del 2026-11-04): primero solo los excluyentes; el resto se abre
  con «Seguir con los demás requisitos» (ampliar). recorrido trae siempre todos; visibles dice qué se pregunta ahora.
* «Lo tiene · archivo pendiente» (migración 0032, solo documentos): Hermatix tiene el documento pero todavía no se
  sube (son delicados); se completa después con «Cambiar». El avance lo cuenta aparte.
* Archivos: PDF/PNG/JPG validados igual que en el perfil, en ASSISTANT_DOCS_DIR/<nro_sicop>/, fuera de Git; cada
  vista o descarga queda en audit_log. Con ASSISTANT_SEND_DOCUMENTS=false su texto nunca sale de la app (la IA no
  recibe archivos en ningún caso: con true se avisa que ese camino falta, decisión pendiente de Oscar).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO

from app import historial, perfil
from app.ai import verificacion
from app.archivos import ArchivoInvalido
from app.config import Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

INFORMATIVOS = ("multa clausula penal", "condicion de la institucion")    # normalizados (sin «/», tildes ni «:»)
ESTADOS = {"respondido": "Respondido", "archivo_pendiente": "Lo tiene · archivo pendiente",
           "no_lo_tiene": "Hermatix no lo tiene", "no_se": "Todavía no lo sé"}
SOLO_DOCUMENTO = ("archivo_pendiente", "no_lo_tiene")        # respuestas que solo tienen sentido para un documento
PERFIL_USABLE = ("vigente", "por_vencer")
LARGO_TEXTO = 2000


class AsistenteInvalido(ValueError):
    """Una respuesta no se acepta; el mensaje es el que verá la persona."""


@dataclass(frozen=True)
class Sesion:
    id: int
    nro_sicop: str
    iniciada_por: str
    creado_en: str
    ampliada_en: str | None = None          # «Seguir con los demás requisitos» (migración 0034)
    ampliada_por: str | None = None


@dataclass(frozen=True)
class Respuesta:
    id: int
    item_id: int
    requisito: str
    pregunta: str
    tipo_evidencia: str
    estado: str
    fuente: str
    perfil_version_id: int | None
    valor_texto: str | None
    valor_numero: str | None
    valor_fecha: str | None
    valor_si_no: bool | None
    unidad: str | None
    vence_el: str | None
    nota: str | None
    archivo_nombre: str | None
    archivo_extension: str | None
    archivo_tamano: int | None
    respondido_por: str
    creado_en: str

    @property
    def estado_texto(self) -> str:
        return ESTADOS[self.estado]

    @property
    def tiene_archivo(self) -> bool:
        return self.archivo_extension is not None

    @property
    def resumen(self) -> str:
        """La respuesta en palabras: «8 años», «Sí», «permiso.pdf · vence 15/01/2027»."""
        if self.estado == "archivo_pendiente":
            return " · ".join([self.estado_texto] + ([f"vence {perfil.dia(self.vence_el)}"] if self.vence_el else []))
        if self.estado != "respondido":
            return self.estado_texto
        partes = []
        if self.valor_numero is not None:
            partes.append(f"{self.valor_numero} {self.unidad or ''}".strip())
        if self.valor_fecha:
            partes.append(perfil.dia(self.valor_fecha))
        if self.valor_si_no is not None:
            partes.append("Sí" if self.valor_si_no else "No")
        if self.valor_texto:
            partes.append(self.valor_texto)
        if self.archivo_nombre:
            partes.append(self.archivo_nombre)
        if self.vence_el:
            partes.append(f"vence {perfil.dia(self.vence_el)}")
        if self.fuente == "perfil":
            partes.append("(dato del perfil, confirmado)")
        return " · ".join(partes) or self.estado_texto


@dataclass(frozen=True)
class Paso:
    """Un requisito del recorrido: su pregunta, su última respuesta y el dato del perfil que se puede confirmar."""
    item: verificacion.Item
    pregunta: str
    origen: str                          # «ia» o «app»: quién redactó la pregunta
    respuesta: Respuesta | None
    perfil: perfil.Elemento | None       # solo si está vigente o por vencer


@dataclass(frozen=True)
class Entrada:
    """Lo que se escribe en el formulario de una respuesta (se valida en responder)."""
    estado: str = "respondido"
    valor_texto: str = ""
    valor_numero: str = ""
    valor_fecha: str = ""
    valor_si_no: str = ""
    vence_el: str = ""
    nota: str = ""


# --- Lectura -------------------------------------------------------------------------------------------------------

def es_informativo(item: verificacion.Item) -> bool:
    texto = verificacion.normalizar_texto(item.requisito)
    return any(texto.startswith(p) for p in INFORMATIVOS)


def informativos(conn: sqlite3.Connection, nro_sicop: str) -> list[verificacion.Item]:
    return [i for i in verificacion.listar(conn, nro_sicop) if es_informativo(i)]


def sesion(conn: sqlite3.Connection, nro_sicop: str) -> Sesion | None:
    f = conn.execute("SELECT id, nro_sicop, iniciada_por_nombre, creado_en, ampliada_en, ampliada_por_nombre"
                     " FROM eligibility_sessions WHERE nro_sicop = ?", (nro_sicop,)).fetchone()
    return Sesion(*f) if f else None


_RESPUESTA = ("SELECT id, item_id, requisito, pregunta, tipo_evidencia, estado, fuente, perfil_version_id, valor_texto,"
              " valor_numero, valor_fecha, valor_si_no, unidad, vence_el, nota, archivo_nombre, archivo_extension,"
              " archivo_tamano, respondido_por_nombre, creado_en FROM eligibility_answers")


def _respuesta(f) -> Respuesta:
    return Respuesta(*f[:11], None if f[11] is None else bool(f[11]), *f[12:])


def ultimas_respuestas(conn: sqlite3.Connection, session_id: int) -> dict[int, Respuesta]:
    """La respuesta que vale de cada requisito: la última."""
    return {r.item_id: r for r in map(_respuesta, conn.execute(
        f"{_RESPUESTA} WHERE session_id = ? ORDER BY id", (session_id,)))}


def historial_de(conn: sqlite3.Connection, session_id: int, item_id: int) -> list[Respuesta]:
    """Todas las respuestas de un requisito, de la más nueva a la más vieja."""
    return [_respuesta(f) for f in conn.execute(f"{_RESPUESTA} WHERE session_id = ? AND item_id = ? ORDER BY id DESC",
                                                (session_id, item_id))]


def con_cita(texto: str, item: verificacion.Item) -> str:
    """La pregunta siempre cita el pliego: si no trae la marca, se le agrega la primera cita del requisito."""
    if not item.citas or "[DOC " in texto or "SICOP" in texto:
        return texto
    return f"{texto} {item.citas[0]}"


def pregunta_de_la_app(item: verificacion.Item) -> str:
    """La pregunta sin IA: el requisito tal cual, su mínimo y qué tipo de respuesta se necesita."""
    texto = f"El cartel pide: «{item.requisito}»"
    if item.minimo != verificacion.NO_INDICADO:
        texto += f" (mínimo: {item.minimo})"
    texto = con_cita(texto + ".", item)
    preguntas = {
        "numero": f"¿Cuántos {item.unidad} tiene Hermatix?" if item.unidad else "¿Qué número tiene Hermatix?",
        "fecha": "¿Qué fecha corresponde en el caso de Hermatix?",
        "si_no": "¿Hermatix lo puede ofrecer?" if verificacion.es_fila(item) else "¿Hermatix cumple con esto?",
        "documento": "¿Hermatix tiene este documento? Súbelo (PDF, PNG o JPG) y escribe hasta qué fecha vence.",
        "texto": "¿Cómo cumple Hermatix con esto? Escríbelo con tus palabras.",
    }
    return f"{texto} {preguntas[item.tipo_evidencia]}"


def _preguntas_ia(conn: sqlite3.Connection, session_id: int) -> dict[int, tuple[str, str]]:
    return {f[0]: (f[1], f[2]) for f in conn.execute(
        "SELECT item_id, requisito, texto FROM eligibility_questions WHERE session_id = ?", (session_id,))}


def recorrido(conn: sqlite3.Connection, nro_sicop: str, dia: date | None = None) -> list[Paso]:
    """Los requisitos que se preguntan, en orden: excluyentes primero y luego el resto, cada grupo como el pliego."""
    actual = sesion(conn, nro_sicop)
    respuestas = ultimas_respuestas(conn, actual.id) if actual else {}
    de_la_ia = _preguntas_ia(conn, actual.id) if actual else {}
    elementos = {e.id: e for e in perfil.listar(conn, dia)}
    items = [i for i in verificacion.listar(conn, nro_sicop) if not es_informativo(i)]
    pasos = []
    for item in sorted(items, key=lambda i: not i.excluyente):          # sorted es estable: conserva el orden
        redactada = de_la_ia.get(item.id)
        if redactada and redactada[0] == item.requisito:
            pregunta, origen = con_cita(redactada[1], item), "ia"
        else:                                    # sin pregunta de la IA, o el requisito se corrigió después
            pregunta, origen = pregunta_de_la_app(item), "app"
        elemento = elementos.get(item.perfil_item_id)
        pasos.append(Paso(item, pregunta, origen, respuestas.get(item.id),
                          elemento if elemento and elemento.estado in PERFIL_USABLE else None))
    return pasos


def ampliada(pasos: list[Paso], actual: Sesion | None) -> bool:
    """True si se pregunta todo: alguien pulsó «Seguir con los demás requisitos» o el cartel no tiene excluyentes."""
    return bool(actual and actual.ampliada_en) or not any(p.item.excluyente for p in pasos)


def visibles(pasos: list[Paso], actual: Sesion | None) -> list[Paso]:
    """Lo que se pregunta ahora: en la revisión rápida, solo los excluyentes (decisión de Oscar, 2026-11-04)."""
    return pasos if ampliada(pasos, actual) else [p for p in pasos if p.item.excluyente]


def siguiente(pasos: list[Paso]) -> Paso | None:
    """La próxima pregunta: el primer requisito sin ninguna respuesta («Todavía no lo sé» también avanza)."""
    return next((p for p in pasos if p.respuesta is None), None)


def avance(pasos: list[Paso]) -> dict[str, int]:
    excluyentes = [p for p in pasos if p.item.excluyente]
    return {"total": len(pasos), "respondidos": sum(p.respuesta is not None for p in pasos),
            "excluyentes": len(excluyentes), "excluyentes_respondidos": sum(p.respuesta is not None for p in excluyentes),
            "no_se": sum(p.respuesta is not None and p.respuesta.estado == "no_se" for p in pasos),
            "archivo_pendiente": sum(p.respuesta is not None and p.respuesta.estado == "archivo_pendiente"
                                     for p in pasos)}


def paso_de(pasos: list[Paso], item_id: int) -> Paso:
    paso = next((p for p in pasos if p.item.id == item_id), None)
    if paso is None:
        raise AsistenteInvalido("Ese requisito no está en el asistente de este cartel.")
    return paso


# --- Escritura -----------------------------------------------------------------------------------------------------

def _momento(ahora: datetime) -> str:
    return ahora.astimezone(HORA_CR).isoformat(timespec="seconds")


def empezar(conn: sqlite3.Connection, nro_sicop: str, quien: Quien, ahora: datetime) -> Sesion:
    """Abre la conversación del cartel (si ya existe, la devuelve: se retoma, no se duplica)."""
    if not verificacion.listar(conn, nro_sicop):
        raise AsistenteInvalido("Este cartel todavía no tiene lista de verificación: genérala primero.")
    verificacion.sincronizar_filas(conn, nro_sicop)          # las filas de «Qué piden» también se preguntan
    with transaccion(conn):
        cursor = conn.execute("INSERT OR IGNORE INTO eligibility_sessions (nro_sicop, iniciada_por, iniciada_por_nombre,"
                              " creado_en) VALUES (?, ?, ?, ?)", (nro_sicop, quien.user_id, quien.nombre, _momento(ahora)))
        if cursor.rowcount:
            historial.registrar(conn, quien, "empezar_asistente", nro_sicop)
    return sesion(conn, nro_sicop)


def ampliar(conn: sqlite3.Connection, nro_sicop: str, quien: Quien, ahora: datetime) -> Sesion:
    """«Seguir con los demás requisitos»: abre el resto del cuestionario. Una sola vez; lo respondido se conserva."""
    actual = sesion(conn, nro_sicop)
    if actual is None:
        raise AsistenteInvalido("El asistente de este cartel no se ha empezado.")
    verificacion.sincronizar_filas(conn, nro_sicop)
    if actual.ampliada_en is None:
        with transaccion(conn):
            conn.execute("UPDATE eligibility_sessions SET ampliada_en = ?, ampliada_por_nombre = ? WHERE id = ?"
                         " AND ampliada_en IS NULL", (_momento(ahora), quien.nombre, actual.id))
            historial.registrar(conn, quien, "ampliar_asistente", nro_sicop)
    return sesion(conn, nro_sicop)


def guardar_preguntas(conn: sqlite3.Connection, session_id: int, preguntas: dict[int, tuple[str, str]], uso_id: int,
                      version: str, ahora: datetime) -> None:
    """Las preguntas que redactó la IA: {item_id: (requisito, texto)}. Si el requisito se corrigió, se reemplaza."""
    with transaccion(conn):
        conn.executemany(
            "INSERT INTO eligibility_questions (session_id, item_id, requisito, texto, ia_usage_id, prompt_version,"
            " creado_en) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT (session_id, item_id) DO UPDATE SET"
            " requisito = excluded.requisito, texto = excluded.texto, ia_usage_id = excluded.ia_usage_id,"
            " prompt_version = excluded.prompt_version, creado_en = excluded.creado_en",
            [(session_id, item_id, req, texto[:1000], uso_id, version, _momento(ahora))
             for item_id, (req, texto) in preguntas.items()])


def _fecha(texto: str, campo: str) -> str | None:
    texto = texto.strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto).isoformat()
    except ValueError:
        raise AsistenteInvalido(f"«{campo}» no es una fecha válida (AAAA-MM-DD).") from None


def _valores(item: verificacion.Item, e: Entrada) -> dict:
    """Los valores de la respuesta según «Qué lo demuestra». Un dato que falta o no se entiende se vuelve a pedir."""
    if e.estado not in ESTADOS:
        raise AsistenteInvalido("Elige una respuesta.")
    nota = e.nota.strip()[:LARGO_TEXTO] or None
    vacio = {"valor_texto": None, "valor_numero": None, "valor_fecha": None, "valor_si_no": None, "unidad": None,
             "vence_el": None, "nota": nota}
    if e.estado in SOLO_DOCUMENTO and item.tipo_evidencia != "documento":
        raise AsistenteInvalido(f"«{ESTADOS[e.estado]}» es solo para documentos.")
    if e.estado == "archivo_pendiente":                  # sin archivo todavía: la fecha de vencimiento sí sirve
        return {**vacio, "vence_el": _fecha(e.vence_el, "Vence el")}
    if e.estado != "respondido":
        return vacio
    t = item.tipo_evidencia
    if t == "numero":
        numero = e.valor_numero.strip().replace(" ", "")
        try:
            numero = str(Decimal(numero.replace(",", "."))) if numero else ""
        except InvalidOperation:
            raise AsistenteInvalido(f"«{e.valor_numero}» no es un número: escribe solo la cantidad (por ejemplo 8)."
                                    ) from None
        if not numero:
            raise AsistenteInvalido("Escribe el número exacto (por ejemplo 8).")
        return {**vacio, "valor_numero": numero, "unidad": item.unidad}
    if t == "fecha":
        fecha = _fecha(e.valor_fecha, "Fecha")
        if fecha is None:
            raise AsistenteInvalido("Escribe la fecha.")
        return {**vacio, "valor_fecha": fecha}
    if t == "si_no":
        if e.valor_si_no not in ("1", "0"):
            raise AsistenteInvalido("Elige «Sí» o «No».")
        return {**vacio, "valor_si_no": int(e.valor_si_no)}
    if t == "texto":
        texto = e.valor_texto.strip()[:LARGO_TEXTO]
        if not texto:
            raise AsistenteInvalido("Escribe la respuesta.")
        return {**vacio, "valor_texto": texto}
    return {**vacio, "vence_el": _fecha(e.vence_el, "Vence el")}                # documento: el archivo, aparte


def _insertar(conn: sqlite3.Connection, session_id: int, paso: Paso, campos: dict, quien: Quien, ahora: datetime) -> int:
    campos = {"session_id": session_id, "item_id": paso.item.id, "requisito": paso.item.requisito,
              "pregunta": paso.pregunta, "tipo_evidencia": paso.item.tipo_evidencia, **campos,
              "respondido_por": quien.user_id, "respondido_por_nombre": quien.nombre, "creado_en": _momento(ahora)}
    return conn.execute(f"INSERT INTO eligibility_answers ({', '.join(campos)}) VALUES"
                        f" ({', '.join('?' for _ in campos)})", tuple(campos.values())).lastrowid


def _sesion_y_paso(conn: sqlite3.Connection, nro_sicop: str, item_id: int, dia: date) -> tuple[Sesion, Paso]:
    actual = sesion(conn, nro_sicop)
    if actual is None:
        raise AsistenteInvalido("El asistente de este cartel no se ha empezado.")
    return actual, paso_de(recorrido(conn, nro_sicop, dia), item_id)


def responder(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, item_id: int, entrada: Entrada,
              archivo: tuple[BinaryIO, str | None] | None, quien: Quien, ahora: datetime,
              guardar_en_perfil: bool = False) -> int:
    """Guarda la respuesta de una persona (si ya había una, esta la reemplaza; la anterior queda en el historial).
    guardar_en_perfil (solo administradores: lo revisa la ruta) crea además una versión nueva del elemento."""
    actual, paso = _sesion_y_paso(conn, nro_sicop, item_id, ahora.astimezone(HORA_CR).date())
    campos = _valores(paso.item, entrada)
    es_documento = paso.item.tipo_evidencia == "documento" and entrada.estado == "respondido"
    if es_documento and settings.assistant_send_documents:
        raise AsistenteInvalido("ASSISTANT_SEND_DOCUMENTS=true todavía no está construido (falta la decisión de"
                                " Oscar): ponlo en false. No se guardó ni se envió nada.")
    if es_documento and archivo is None:
        raise AsistenteInvalido("Sube el documento (PDF, PNG o JPG). Si Hermatix lo tiene pero lo subes después,"
                                " elige «Lo tiene · subo el archivo después»; si no, «Todavía no lo sé» o «Hermatix"
                                " no lo tiene».")
    if guardar_en_perfil and (paso.item.perfil_item_id is None or entrada.estado != "respondido"
                              or paso.item.tipo_evidencia == "si_no"):
        raise AsistenteInvalido("Esta respuesta no se puede guardar en el perfil: el requisito no tiene un elemento"
                                " del perfil o no trae un dato.")
    if es_documento:
        campos.update(perfil.guardar_documento(settings.assistant_docs_dir, nro_sicop, archivo[0], archivo[1],
                                               settings.assistant_doc_max_mb * 1024 * 1024, "En el asistente",
                                               "ASSISTANT_DOC_MAX_MB"))
    with transaccion(conn):
        respuesta_id = _insertar(conn, actual.id, paso, {"estado": entrada.estado, "fuente": "usuario", **campos},
                                 quien, ahora)
        # Como las notas del expediente: el contenido no va al historial, solo qué requisito se respondió.
        historial.registrar(conn, quien, "responder_asistente", f"{nro_sicop}: requisito #{item_id}")
    if guardar_en_perfil:
        _al_perfil(conn, settings, paso.item.perfil_item_id, campos, quien, ahora)
    return respuesta_id


def _al_perfil(conn: sqlite3.Connection, settings: Settings, elemento_id: int, campos: dict, quien: Quien,
               ahora: datetime) -> None:
    datos = perfil.Datos(valor=campos["valor_texto"] or (campos["valor_fecha"] or ""), numero=campos["valor_numero"]
                         or "", unidad=campos["unidad"] or "", vence_el=campos["vence_el"] or "",
                         nota=campos["nota"] or "")
    try:
        if campos.get("archivo_ruta"):
            with open(settings.assistant_docs_dir / campos["archivo_ruta"], "rb") as f:
                perfil.nueva_version(conn, settings.profile_docs_dir, elemento_id, datos, (f, campos["archivo_nombre"]),
                                     settings.profile_doc_max_mb * 1024 * 1024, quien, ahora)
        else:
            perfil.nueva_version(conn, settings.profile_docs_dir, elemento_id, datos, None,
                                 settings.profile_doc_max_mb * 1024 * 1024, quien, ahora)
    except (perfil.PerfilInvalido, ArchivoInvalido) as exc:
        raise AsistenteInvalido(f"La respuesta se guardó, pero no en el perfil: {exc}") from None


def confirmar_perfil(conn: sqlite3.Connection, nro_sicop: str, item_id: int, quien: Quien, ahora: datetime) -> int:
    """La persona confirmó que el dato vigente del perfil sigue siendo correcto: queda como su respuesta."""
    actual, paso = _sesion_y_paso(conn, nro_sicop, item_id, ahora.astimezone(HORA_CR).date())
    if paso.perfil is None:
        raise AsistenteInvalido("Este requisito no tiene un dato vigente en el perfil: respóndelo.")
    v = paso.perfil.vigente
    campos = {"estado": "respondido", "fuente": "perfil", "perfil_version_id": v.id, "valor_texto": v.valor,
              "valor_numero": v.numero, "unidad": v.unidad, "vence_el": v.vence_el, "nota": v.nota}
    with transaccion(conn):
        respuesta_id = _insertar(conn, actual.id, paso, campos, quien, ahora)
        historial.registrar(conn, quien, "confirmar_perfil_asistente",
                            f"{nro_sicop}: requisito #{item_id} con «{paso.perfil.titulo}»")
    return respuesta_id


# --- Archivos de las respuestas: ruta segura y registro de cada acceso -------------------------------------------

def documento(conn: sqlite3.Connection, base: Path, nro_sicop: str, respuesta_id: int) -> tuple[Path, Respuesta] | None:
    """La ruta en disco y la respuesta, solo si el archivo es de ESE cartel; o None."""
    fila = conn.execute(f"{_RESPUESTA.replace(' FROM', ', archivo_ruta FROM')} WHERE id = ? AND session_id ="
                        " (SELECT id FROM eligibility_sessions WHERE nro_sicop = ?)", (respuesta_id, nro_sicop)).fetchone()
    if fila is None or fila[-1] is None:
        return None
    ruta = base / fila[-1]
    if ruta.resolve().parent != (base / nro_sicop).resolve() or not ruta.is_file():
        return None
    return ruta, _respuesta(fila[:-1])


def registrar_acceso(conn: sqlite3.Connection, quien: Quien, accion: str, nro_sicop: str, r: Respuesta) -> None:
    with transaccion(conn):
        historial.registrar(conn, quien, accion, f"{nro_sicop}: «{r.archivo_nombre}» (respuesta #{r.id})")
