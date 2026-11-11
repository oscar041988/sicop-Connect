"""El asistente de elegibilidad como chat (DECISION_IA.md §10, aprobado por Oscar el 2026-11-11; migración 0044).

Quién hace qué:
* La persona escribe (y puede subir un archivo). Su mensaje queda en asistente_chat.
* La IA lee el mensaje, la lista de requisitos y la conversación, y devuelve dos cosas (salida estructurada):
  un mensaje corto para la persona y las respuestas que trae el mensaje, cada una con su requisito (R1, R2…).
  Es la «lista cerrada de acciones» de §10.2: la IA no escribe en la base; propone.
* La app guarda cada respuesta con asistente.responder, con las mismas reglas que el formulario de siempre: un número
  tiene que ser un número, un documento «respondido» necesita el archivo, etc. Lo que no pasa se dice en el chat.
  Así, aunque alguien pida «ponle que sí», un documento no queda cumplido sin el archivo (§10.3, regla 2).
* La app confirma lo que guardó y hace la siguiente pregunta: la IA no lo hace, para que nunca diga algo que no pasó.
* Archivos: se guardan en ASSISTANT_DOCS_DIR como siempre, tal cual (sin modificarlos). Con
  ASSISTANT_SEND_DOCUMENTS=true la IA lee su texto (Oscar, §10.4); con false, solo el nombre.
* A la IA va: el cartel (número y objeto), los requisitos con su cita y su respuesta actual, la conversación y el
  mensaje. Nunca el perfil, contraseñas ni usuarios. Con la IA apagada o sin presupuesto, el chat lo dice y no llama.
* Pruebas siempre con IA SIMULADA (regla 7).
"""

from __future__ import annotations

import io
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app import asistente, historial
from app.ai import cliente as ia_cliente
from app.ai import verificacion
from app.ai.cola import costo_de_hoy
from app.ai.resumen import NO, PROMPTS_DIR, _lista, _objeto, _texto, normalizar
from app.archivos import ArchivoInvalido
from app.config import Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

VERSION = "v2"                  # v2 (2026-11-11, prueba de Ivania): trato de usted y cómo avanzar sin la respuesta
LARGO_MENSAJE = 4000            # lo que puede escribir la persona en un mensaje
LARGO_ARCHIVO = 15000           # caracteres del texto de un archivo que se mandan a la IA
CONVERSACION = 30               # mensajes anteriores que se mandan a la IA
NOTA = "Desde el chat del asistente."
ROLES = {"persona": "PERSONA", "asistente": "ASISTENTE", "app": "APP"}

ESQUEMA = _objeto(
    mensaje=_texto("La respuesta corta para el encargado (máximo tres oraciones)"),
    respuestas=_lista(_objeto(
        ref=_texto("El número del requisito: R1, R2…"),
        estado={"type": "string", "enum": list(asistente.ESTADOS),
                "description": "respondido · archivo_pendiente · no_lo_tiene · no_se"},
        valor=_texto("Número: solo la cifra · sí o no: «sí» o «no» · fecha: AAAA-MM-DD · texto: la respuesta · "
                     "documento: «»"),
        vence_el=_texto("AAAA-MM-DD si se sabe hasta cuándo vale el documento; si no, «»"),
        usa_archivo={"type": "boolean", "description": "true solo si el archivo de este mensaje prueba este requisito"},
    )))
FORMATO = {"type": "json_schema", "name": "chat_asistente", "schema": ESQUEMA, "strict": True}


class ChatInvalido(ValueError):
    """El mensaje no se acepta; el texto es el que ve la persona."""


@dataclass(frozen=True)
class Mensaje:
    id: int
    rol: str
    texto: str
    archivo_nombre: str | None
    autor_nombre: str | None
    creado_en: str


def cargar_prompt() -> str:
    return (PROMPTS_DIR / f"chat_asistente_{VERSION}.md").read_text(encoding="utf-8")


# --- Lectura -------------------------------------------------------------------------------------------------------

def mensajes(conn: sqlite3.Connection, session_id: int) -> list[Mensaje]:
    return [Mensaje(*f) for f in conn.execute(
        "SELECT id, rol, texto, archivo_nombre, autor_nombre, creado_en FROM asistente_chat WHERE session_id = ?"
        " ORDER BY id", (session_id,))]


# Una o más citas seguidas: «[DOC 1 · pág. 2]; [DOC 1 · pág. 3] [SICOP]…».
_CITA = r"\[(?:DOC \d+ · pág\. \d+|SICOP)\]"
_CITAS_SEGUIDAS = re.compile(rf"{_CITA}(?:\s*;?\s*{_CITA})+")
MAX_CITAS = 2


def pocas_citas(texto: str) -> str:
    """En el chat, como máximo 2 citas seguidas y «(y N citas más)»: la lista completa sigue en «Respuestas dadas» y
    en el resultado (prueba de Ivania, 2026-11-11: una pregunta traía 10 citas)."""
    def recortar(m: re.Match) -> str:
        citas = re.findall(_CITA, m.group(0))
        if len(citas) <= MAX_CITAS:
            return m.group(0)
        resto = len(citas) - MAX_CITAS
        return "; ".join(citas[:MAX_CITAS]) + f" (y {resto} {'cita más' if resto == 1 else 'citas más'})"
    return _CITAS_SEGUIDAS.sub(recortar, texto)


# Cómo avanzar sin la respuesta (prueba de Ivania, 2026-11-11: el chat se quedaba en la misma pregunta).
AYUDA_DOCUMENTO = (" Si lo tiene pero lo sube después, diga «lo subo después»; si Hermatix no lo tiene, «no lo "
                   "tenemos»; si no sabe, «no sé».")
AYUDA = " Si no sabe, diga «no sé» y seguimos con la siguiente."


def pregunta(paso: asistente.Paso) -> str:
    """La pregunta de un requisito, como la hace el asistente de siempre, y el dato del perfil si hay uno vigente."""
    texto = pocas_citas(paso.pregunta)
    if paso.perfil is not None:
        v = paso.perfil.vigente
        dato = " · ".join(x for x in (f"{v.numero} {v.unidad or ''}".strip() if v.numero else "", v.valor or "",
                                      v.archivo_nombre or "") if x)
        texto += f" En el perfil («{paso.perfil.titulo}») dice: {dato or 'sin dato'}. ¿Sigue siendo correcto?"
    return texto + (AYUDA_DOCUMENTO if paso.item.tipo_evidencia == "documento" else AYUDA)


def siguiente_mensaje(pasos: list[asistente.Paso], sesion: asistente.Sesion) -> str:
    """Lo que dice la app al final de cada vuelta: la pregunta siguiente o que ya está todo."""
    visibles = asistente.visibles(pasos, sesion)
    paso = asistente.siguiente(visibles)
    if paso is not None:
        av = asistente.avance(visibles)
        return f"Pregunta {av['respondidos'] + 1} de {av['total']}: {pregunta(paso)}"
    if not asistente.ampliada(pasos, sesion):
        return ("Ya están respondidos los requisitos excluyentes. Si el cartel interesa, pulse «Seguir con los demás "
                "requisitos» para responder el resto.")
    return ("Ya están respondidos todos los requisitos. Ya puede pedir la oferta completa con los documentos que se "
            "subieron (en PDF o en Word). Lo que no cumple o falta sale en rojo.")


def listo(pasos: list[asistente.Paso], sesion: asistente.Sesion | None) -> bool:
    """«Ya está lista la oferta»: el cuestionario completo está abierto y todo requisito tiene respuesta."""
    return bool(sesion and pasos and asistente.ampliada(pasos, sesion)
                and asistente.siguiente(asistente.visibles(pasos, sesion)) is None)


def presentacion(pasos: list[asistente.Paso], sesion: asistente.Sesion) -> str:
    """El primer mensaje del chat (lo dice la app, sin IA)."""
    visibles = asistente.visibles(pasos, sesion)
    faltan = sum(p.respuesta is None for p in visibles)
    primero = ("Primero los requisitos excluyentes: si alguno no se cumple, Hermatix queda fuera. "
               if not asistente.ampliada(pasos, sesion) else "")
    return (f"Hola. Leí los requisitos de este cartel: {faltan} sin responder. Le pregunto uno por uno; puede "
            f"contestar con sus palabras y subir los documentos aquí mismo. {primero}{siguiente_mensaje(pasos, sesion)}")


# --- Escritura -----------------------------------------------------------------------------------------------------

def _momento(ahora: datetime) -> str:
    return ahora.astimezone(HORA_CR).isoformat(timespec="seconds")


def _guardar(conn: sqlite3.Connection, session_id: int, rol: str, texto: str, ahora: datetime,
             quien: Quien | None = None, archivo: str | None = None, uso_id: int | None = None) -> None:
    with transaccion(conn):
        conn.execute("INSERT INTO asistente_chat (session_id, rol, texto, archivo_nombre, autor_id, autor_nombre,"
                     " ia_usage_id, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (session_id, rol, texto[:6000], archivo, quien.user_id if quien else None,
                      quien.nombre if quien else None, uso_id, _momento(ahora)))


# --- Lo que va a la IA ---------------------------------------------------------------------------------------------

def _requisitos(pasos: list[asistente.Paso]) -> str:
    lineas = ["REQUISITOS (del cartel):"]
    for n, p in enumerate(pasos, start=1):
        i = p.item
        tipo = verificacion.EVIDENCIAS[i.tipo_evidencia] + (f" ({i.unidad})" if i.unidad else "")
        actual = p.respuesta.resumen if p.respuesta else "sin responder"
        lineas.append(f"R{n} · excluyente: {'sí' if i.excluyente else 'no'} · tipo: {tipo} · mínimo: {i.minimo}"
                      f" · cita: {'; '.join(i.citas) or 'sin cita'} · requisito: «{i.requisito}»"
                      f" · respuesta actual: {actual}")
    return "\n".join(lineas)


def _texto_archivo(datos: bytes, nombre: str) -> str:
    """El texto de un PDF para la IA (las imágenes no tienen texto). Solo se lee: el archivo no cambia."""
    from app.sources.sicop_documentos import extraer_texto
    if Path(nombre).suffix.lower() != ".pdf":
        return "(imagen: la IA no lee su texto)"
    texto = extraer_texto(datos, ".pdf")
    contenido = "\n".join(t for (_, _, t) in texto.filas).strip()
    if not contenido:
        return "(el PDF no tiene texto que se pueda leer)"
    return contenido[:LARGO_ARCHIVO] + (" […recortado]" if len(contenido) > LARGO_ARCHIVO else "")


def texto_para_ia(compra, pasos: list[asistente.Paso], anteriores: list[Mensaje], texto: str,
                  archivo: tuple[bytes, str] | None, con_texto_archivo: bool) -> str:
    actual = asistente.siguiente(pasos)
    numero = next((n for n, p in enumerate(pasos, start=1) if p is actual), None)
    partes = [f"CARTEL: {compra.nro_sicop} · {compra.descripcion or 'sin objeto'}", "", _requisitos(pasos), "",
              f"PREGUNTA ACTUAL: {f'R{numero}' if numero else 'ninguna (todo respondido)'}", "", "CONVERSACIÓN:"]
    for m in anteriores[-CONVERSACION:]:
        extra = f" [archivo: {m.archivo_nombre}]" if m.archivo_nombre else ""
        partes.append(f"{ROLES[m.rol]}: {m.texto}{extra}")
    partes += ["", f"MENSAJE NUEVO: {texto or '(sin texto)'}"]
    if archivo is not None:
        datos, nombre = archivo
        partes.append(f"ARCHIVO: {nombre}")
        partes.append("TEXTO DEL ARCHIVO:\n" + _texto_archivo(datos, nombre) if con_texto_archivo
                      else "TEXTO DEL ARCHIVO: (no se envía: ASSISTANT_SEND_DOCUMENTS=false)")
    return "\n".join(partes)


# --- Lo que propone la IA, guardado por la app ---------------------------------------------------------------------

def _vacio(valor: str) -> str:
    return "" if valor == NO else valor.strip()


def _entrada(paso: asistente.Paso, r: dict) -> asistente.Entrada:
    valor, t = _vacio(r["valor"]), paso.item.tipo_evidencia
    campos = {"estado": r["estado"], "vence_el": _vacio(r["vence_el"]), "nota": NOTA}
    if r["estado"] == "respondido":
        if t == "numero":
            campos["valor_numero"] = valor
        elif t == "fecha":
            campos["valor_fecha"] = valor
        elif t == "si_no":
            campos["valor_si_no"] = {"sí": "1", "si": "1", "no": "0"}.get(valor.lower(), "")
        elif t == "texto":
            campos["valor_texto"] = valor
    return asistente.Entrada(**campos)


def _corto(texto: str, largo: int = 90) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= largo else texto[:largo - 1].rstrip() + "…"


def _aplicar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, visibles: list[asistente.Paso],
             propuestas: list[dict], archivo: tuple[bytes, str] | None, quien: Quien,
             ahora: datetime) -> tuple[list[str], bool]:
    """Guarda lo que propuso la IA con las reglas de siempre. Devuelve las líneas para el chat y si se usó el archivo."""
    por_ref = {f"R{n}": p for n, p in enumerate(visibles, start=1)}
    lineas, usado, vistos = [], False, set()
    for r in propuestas:
        paso = por_ref.get(str(r["ref"]).strip().upper())
        if paso is None or paso.item.id in vistos or r["estado"] == NO:
            continue                                     # requisito inventado, repetido o sin estado: se ignora
        vistos.add(paso.item.id)
        subir = None
        if r["usa_archivo"] and archivo is not None and not usado and paso.item.tipo_evidencia == "documento":
            subir = (io.BytesIO(archivo[0]), archivo[1])
        try:
            asistente.responder(conn, settings, nro_sicop, paso.item.id, _entrada(paso, r), subir, quien, ahora)
        except (asistente.AsistenteInvalido, ArchivoInvalido) as exc:
            lineas.append(f"No se guardó «{_corto(paso.item.requisito)}»: {exc}")
            continue
        usado = usado or subir is not None
        guardada = asistente.recorrido(conn, nro_sicop, ahora.astimezone(HORA_CR).date())
        respuesta = asistente.paso_de(guardada, paso.item.id).respuesta
        lineas.append(f"Guardado · {_corto(paso.item.requisito)}: {respuesta.resumen}")
    return lineas, usado


def _sin_presupuesto(conn: sqlite3.Connection, settings: Settings, ahora: datetime) -> str | None:
    hoy = costo_de_hoy(conn, ahora.astimezone(HORA_CR).date())
    if hoy >= settings.ia_max_daily_cost:
        return (f"Ya se usó el presupuesto de IA de hoy ({settings.ia_max_daily_cost} USD, IA_MAX_DAILY_COST). Su "
                "mensaje quedó guardado; el chat sigue mañana, o responda con el formulario de siempre.")
    return None


def enviar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, texto: str,
           archivo: tuple[bytes, str] | None, quien: Quien, ahora: datetime, cliente=None, dormir=None) -> None:
    """Una vuelta del chat: guarda el mensaje, le pregunta a la IA, guarda lo que se pueda y hace la siguiente
    pregunta. Lanza ChatInvalido si el mensaje no se acepta; nunca lanza por la IA (lo dice en el chat)."""
    from app.compras import detalle_compra
    sesion = asistente.sesion(conn, nro_sicop)
    if sesion is None:
        raise ChatInvalido("El asistente de este cartel no se ha empezado.")
    texto = " ".join((texto or "").split())[:LARGO_MENSAJE]
    if not texto and archivo is None:
        raise ChatInvalido("Escriba un mensaje o suba un archivo.")
    dia = ahora.astimezone(HORA_CR).date()
    pasos = asistente.recorrido(conn, nro_sicop, dia)
    anteriores = mensajes(conn, sesion.id)
    if not anteriores:                                   # la presentación queda en el registro de la conversación
        _guardar(conn, sesion.id, "app", presentacion(pasos, sesion), ahora)
        anteriores = mensajes(conn, sesion.id)
    _guardar(conn, sesion.id, "persona", texto or "(archivo)", ahora, quien, archivo[1] if archivo else None)
    with transaccion(conn):
        historial.registrar(conn, quien, "chat_asistente", nro_sicop + (f": «{archivo[1]}»" if archivo else ""))

    sin_archivo = (f" El archivo «{archivo[1]}» no se guardó: súbalo otra vez cuando la IA responda."
                   if archivo else "")
    if not settings.ia_activa:
        _guardar(conn, sesion.id, "app", "La IA está apagada (AI_MODE=none): el chat no puede responder." + sin_archivo,
                 ahora)
        return
    if (motivo := _sin_presupuesto(conn, settings, ahora)) is not None:
        _guardar(conn, sesion.id, "app", motivo + sin_archivo, ahora)
        return
    visibles = asistente.visibles(pasos, sesion)
    entrada = texto_para_ia(detalle_compra(conn, nro_sicop), visibles, anteriores, texto, archivo,
                            settings.assistant_send_documents)
    extra = {"dormir": dormir} if dormir is not None else {}
    try:
        r = ia_cliente.pedir(conn, settings, cargar_prompt(), entrada, "chat", nro_sicop, cliente=cliente,
                             formato=FORMATO, **extra)
        datos = normalizar(json.loads(r.texto), ESQUEMA) if r.resultado == "ok" else None
    except (ia_cliente.IaApagada, ia_cliente.IaConfiguracion) as exc:
        _guardar(conn, sesion.id, "app", f"{exc}{sin_archivo}", ahora)
        return
    except ia_cliente.IaFallo as exc:
        _guardar(conn, sesion.id, "app", f"La IA no respondió bien ({exc.motivo}). Su mensaje quedó guardado: "
                                         f"inténtelo de nuevo.{sin_archivo}", ahora)
        return
    except ValueError:
        datos = None
    if datos is None:
        _guardar(conn, sesion.id, "app", "La respuesta de la IA no sirvió. Su mensaje quedó guardado: inténtelo de "
                                         f"nuevo.{sin_archivo}", ahora)
        return

    if datos["mensaje"] != NO:
        _guardar(conn, sesion.id, "asistente", datos["mensaje"], ahora, uso_id=r.uso_id)
    lineas, usado = _aplicar(conn, settings, nro_sicop, visibles, datos["respuestas"], archivo, quien, ahora)
    if archivo is not None and not usado:
        lineas.append(f"El archivo «{archivo[1]}» no se guardó: no quedó claro a qué requisito corresponde. "
                      "Dígalo y súbalo otra vez.")
    if lineas:
        _guardar(conn, sesion.id, "app", "\n".join(lineas), ahora)
    _guardar(conn, sesion.id, "app", _sin_repetir(siguiente_mensaje(asistente.recorrido(conn, nro_sicop, dia),
                                                                    asistente.sesion(conn, nro_sicop)), anteriores),
             ahora)


def _sin_repetir(nuevo: str, anteriores: list[Mensaje]) -> str:
    """Si la pregunta siguiente es la misma que la app hizo la última vez, no se copia entera otra vez (prueba de
    Ivania, 2026-11-11: se repetía completa después de cada mensaje)."""
    ultima = next((m.texto for m in reversed(anteriores) if m.rol == "app" and "Pregunta " in m.texto), None)
    if ultima is not None and nuevo.startswith("Pregunta ") and nuevo in ultima:
        numero = nuevo.split(":", 1)[0]                   # «Pregunta 1 de 8»
        return f"Seguimos con la {numero[0].lower()}{numero[1:]} (arriba)."
    return nuevo
