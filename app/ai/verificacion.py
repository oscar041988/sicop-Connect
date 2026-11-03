"""Lista de verificación del cartel (asistente de elegibilidad, lección 2; migración 0030).

* Cada requerimiento del último resumen con IA (ok o revisar) se convierte en algo comprobable: qué tipo de respuesta
  lo demuestra (tipo_evidencia), el mínimo exigido y sus citas. El requisito, su tipo y si es excluyente salen del
  RESUMEN; la IA solo agrega evidencia, mínimo, unidad y citas.
* A la IA se le mandan los requerimientos numerados (R1, R2…) y el expediente (decisión de Ivania, 2026-11-02),
  con el prompt config/prompts/lista_verificacion_<VERSION>.md. NUNCA datos del perfil de Hermatix.
* La app no deja pasar mínimos inventados: un número o una fecha que no aparece en el requerimiento ni en el
  expediente se descarta y el mínimo queda «no indicado».
* Un requerimiento que la IA no devuelva igual queda en la lista («texto», «no indicado»): ninguno se pierde.
* Volver a generar no toca lo que hizo una persona: lo corregido, lo agregado y lo quitado se quedan como están
  (se reconocen por «clave», el texto normalizado del requerimiento).
* La relación con el perfil la PROPONE la app (palabras de config/perfil.yaml o del título del elemento) y la
  confirma el usuario.
"""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import yaml

from app import historial
from app.ai import cliente as ia_cliente
from app.ai.cola import costo_de_hoy
from app.ai.expediente import armar_expediente
from app.ai.resumen import PROMPTS_DIR, TIPOS_REQUISITO, _lista, _objeto, _texto, normalizar
from app.config import PROJECT_ROOT, Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

VERSION = "v1"
NO_INDICADO = "no indicado"
EVIDENCIAS = {"numero": "Número", "si_no": "Sí o no", "fecha": "Fecha", "documento": "Documento", "texto": "Texto"}
TIPOS = {"tecnico": "Técnico", "legal": "Legal", "financiero": "Financiero", "experiencia": "Experiencia"}
PERFIL_YAML = PROJECT_ROOT / "config" / "perfil.yaml"
_NUMEROS_EN_PALABRAS = {"uno": 1, "una": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
                        "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15,
                        "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "cien": 100}
_VACIAS = {"de", "del", "la", "las", "el", "los", "y", "o", "en", "con", "por", "para", "al", "a", "un", "una",
           "que", "se", "su", "sus", "lo", "e"}


class VerificacionError(ValueError):
    """No se pudo generar o cambiar la lista; el mensaje es el que verá la persona."""


ESQUEMA = _objeto(items=_lista(_objeto(
    ref=_texto("El número del requerimiento: R1, R2…"),
    tipo_evidencia={"type": "string", "enum": list(EVIDENCIAS)},
    minimo=_texto("El mínimo en palabras, solo si el pliego lo dice; si no, «no indicado»"),
    minimo_numero=_texto("Solo el número si el mínimo es una cantidad (3); si no, «no indicado»"),
    minimo_fecha=_texto("AAAA-MM-DD si el mínimo es una fecha concreta; si no, «no indicado»"),
    unidad=_texto("Unidad del número (años, técnicos, meses), o «no indicado»"),
    igual_a=_texto("Ref de un requerimiento anterior que pide lo mismo (R2), o «ninguno»"),
    citas=_lista(_texto("Marca [DOC n · pág. p] o «SICOP»")))))
FORMATO = {"type": "json_schema", "name": "lista_verificacion", "schema": ESQUEMA, "strict": True}


@dataclass(frozen=True)
class Item:
    id: int
    orden: int
    clave: str
    requisito: str
    tipo: str
    tipo_evidencia: str
    minimo: str
    minimo_numero: str | None
    minimo_fecha: str | None
    unidad: str | None
    excluyente: bool
    citas: list[str]
    perfil_item_id: int | None
    perfil_titulo: str | None
    perfil_confirmado: bool
    origen: str
    editado: bool
    activo: bool
    editado_por: str | None
    editado_en: str | None

    @property
    def evidencia_texto(self) -> str:
        return EVIDENCIAS[self.tipo_evidencia]

    @property
    def tipo_texto(self) -> str:
        return TIPOS[self.tipo]


@dataclass(frozen=True)
class Generacion:
    id: int
    estado: str
    motivo: str | None
    items: int
    modelo: str | None
    huella: str | None
    generado_por: str
    creado_en: str


# --- Lectura -------------------------------------------------------------------------------------------------------

def normalizar_texto(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", sin_tildes.lower()))


def clave_de(requisito: str) -> str:
    return normalizar_texto(requisito)[:300] or "sin-texto"


_ITEM = ("SELECT i.id, i.orden, i.clave, i.requisito, i.tipo, i.tipo_evidencia, i.minimo, i.minimo_numero,"
         " i.minimo_fecha, i.unidad, i.excluyente, i.citas, i.perfil_item_id, p.titulo, i.perfil_confirmado, i.origen,"
         " i.editado, i.activo, i.editado_por_nombre, i.editado_en FROM eligibility_items i"
         " LEFT JOIN company_profile_items p ON p.id = i.perfil_item_id")


def _item(f) -> Item:
    return Item(f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], f[8], f[9], bool(f[10]), json.loads(f[11] or "[]"),
                f[12], f[13], bool(f[14]), f[15], bool(f[16]), bool(f[17]), f[18], f[19])


_CITA_DOC = re.compile(r"\[DOC (\d+)([^\]]*)\]")
_CITA_PAG = re.compile(r"pág\.\s*(\d+)")


def _lugar(item: Item) -> tuple:
    """Dónde está en el expediente: su primera cita [DOC n · pág. p]; luego las de solo «SICOP»; al final sin cita.
    Un requisito agregado a mano no tiene citas: vale la marca [DOC n · pág. p] que se haya escrito en su texto."""
    lugares = []
    for cita in item.citas or [item.requisito]:
        for m in _CITA_DOC.finditer(cita):
            pagina = _CITA_PAG.search(m.group(2))
            lugares.append((0, int(m.group(1)), int(pagina.group(1)) if pagina else 0))
    if not lugares:
        lugares.append((1 if item.citas else 2, 0, 0))
    return min(lugares) + (item.orden, item.id)


def listar(conn: sqlite3.Connection, nro_sicop: str, activos: bool = True) -> list[Item]:
    """La lista del cartel en el orden del pliego: DOC 1 de la primera a la última página, luego DOC 2…
    (pedido de Ivania, 2026-11-03: revisarla con el pliego abierto). Los excluyentes quedan en su lugar, marcados."""
    return sorted((_item(f) for f in conn.execute(f"{_ITEM} WHERE i.nro_sicop = ? AND i.activo = ?",
                                                  (nro_sicop, 1 if activos else 0))), key=_lugar)


def ultima_generacion(conn: sqlite3.Connection, nro_sicop: str) -> Generacion | None:
    f = conn.execute("SELECT id, estado, motivo, items, modelo, huella, generado_por_nombre, creado_en"
                     " FROM eligibility_generations WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1",
                     (nro_sicop,)).fetchone()
    return Generacion(*f) if f else None


def requerimientos(conn: sqlite3.Connection, nro_sicop: str) -> tuple[int | None, list[dict]]:
    """(id del resumen, sus requerimientos) del último resumen con contenido (ok o revisar)."""
    fila = conn.execute("SELECT id, resumen_json FROM ia_summaries WHERE nro_sicop = ? AND estado IN ('ok', 'revisar')"
                        " AND resumen_json IS NOT NULL ORDER BY id DESC LIMIT 1", (nro_sicop,)).fetchone()
    if fila is None:
        return None, []
    reqs = [r for r in json.loads(fila[1]).get("requerimientos") or []
            if isinstance(r, dict) and str(r.get("requisito") or "").strip()]
    return fila[0], reqs


# --- Relación con el perfil (la propone la app) -------------------------------------------------------------------

def _claves_perfil() -> dict[str, list[str]]:
    datos = yaml.safe_load(PERFIL_YAML.read_text(encoding="utf-8")) or {}
    return {normalizar_texto(t): [normalizar_texto(x) for x in frases or []]
            for t, frases in (datos.get("claves") or {}).items()}


def _palabras(texto: str) -> set[str]:
    return {p for p in normalizar_texto(texto).split() if len(p) > 3 and p not in _VACIAS}


def proponer_perfil(conn: sqlite3.Connection, requisito: str, claves: dict[str, list[str]] | None = None) -> int | None:
    """El elemento del perfil que mejor coincide con el requisito, o None. Solo una propuesta."""
    claves = _claves_perfil() if claves is None else claves
    texto = f" {normalizar_texto(requisito)} "
    palabras = _palabras(requisito)
    mejor, puntaje = None, 0
    for item_id, titulo in conn.execute("SELECT id, titulo FROM company_profile_items ORDER BY id"):
        frases = claves.get(normalizar_texto(titulo), [])
        if any(f" {f} " in texto for f in frases if f):
            puntos = 100
        else:
            comunes = len(palabras & _palabras(titulo))
            puntos = comunes if comunes >= 2 else 0
        if puntos > puntaje:
            mejor, puntaje = item_id, puntos
    return mejor


# --- Generación con IA --------------------------------------------------------------------------------------------

def cargar_prompt() -> str:
    return (PROMPTS_DIR / f"lista_verificacion_{VERSION}.md").read_text(encoding="utf-8")


def texto_para_ia(reqs: list[dict], expediente: str) -> str:
    lineas = ["REQUERIMIENTOS (del resumen del concurso):"]
    for n, r in enumerate(reqs, start=1):
        excluyente = "sí" if r.get("excluyente") else "no"
        lineas.append(f"R{n} · {r.get('tipo', '')} · excluyente: {excluyente} · {r['requisito']}"
                      f" · cita: {r.get('cita') or 'no encontrado'}")
    return "\n".join(lineas) + "\n\nEXPEDIENTE:\n" + expediente


def _valor(texto: str | None) -> str | None:
    texto = (texto or "").strip()
    return None if not texto or normalizar_texto(texto) in ("no indicado", "no encontrado", "ninguno") else texto


def _aparece_numero(numero: str, fuente: str) -> bool:
    try:
        valor = Decimal(numero.replace(",", "."))
    except InvalidOperation:
        return False
    entero = int(valor) if valor == valor.to_integral_value() else None
    if re.search(rf"(?<![\d.,]){re.escape(numero)}(?![\d])", fuente):
        return True
    if entero is not None and re.search(rf"(?<![\d.,]){entero}(?![\d])", fuente):
        return True
    return entero is not None and any(v == entero and re.search(rf"\b{p}\b", fuente)
                                      for p, v in _NUMEROS_EN_PALABRAS.items())


def _aparece_fecha(fecha: str, fuente: str) -> bool:
    try:
        d = date.fromisoformat(fecha)
    except ValueError:
        return False
    return any(x in fuente for x in (d.isoformat(), d.strftime("%d/%m/%Y"), f"{d.day}/{d.month}/{d.year}"))


def _minimo(ia: dict, requisito: str, expediente: str) -> dict:
    """Los campos del mínimo, sin dejar pasar números o fechas que no estén en el texto (mínimos inventados)."""
    fuente = f"{requisito}\n{expediente}"
    fuente_baja = normalizar_texto(fuente)
    minimo, numero, fecha = _valor(ia.get("minimo")), _valor(ia.get("minimo_numero")), _valor(ia.get("minimo_fecha"))
    if numero is not None:
        numero = numero.replace(" ", "")
        if not (_aparece_numero(numero, fuente) or _aparece_numero(numero, fuente_baja)):
            minimo = numero = None                                   # inventado: no indicado
        else:
            numero = str(Decimal(numero.replace(",", ".")))
    if fecha is not None and not _aparece_fecha(fecha, fuente):
        minimo = fecha = None
    return {"minimo": minimo or NO_INDICADO, "minimo_numero": numero, "minimo_fecha": fecha,
            "unidad": _valor(ia.get("unidad")) if numero else None}


def armar_items(reqs: list[dict], datos: dict, expediente: str) -> list[dict]:
    """Los ítems de la lista: uno por requerimiento (los repetidos se juntan con sus citas)."""
    de_la_ia = {str(x.get("ref", "")).strip().upper(): x for x in datos.get("items") or []}
    items: list[dict] = []
    por_ref: dict[str, dict] = {}
    for n, r in enumerate(reqs, start=1):
        ref = f"R{n}"
        ia = de_la_ia.get(ref, {})
        citas = [c for c in ia.get("citas") or [] if _valor(c)] if ia else []
        cita_resumen = _valor(r.get("cita"))
        if cita_resumen and cita_resumen not in citas:
            citas.insert(0, cita_resumen)
        igual = str(ia.get("igual_a") or "").strip().upper()
        if igual in por_ref:                                         # repetido: se junta con el primero
            destino = por_ref[igual]
            destino["citas"] += [c for c in citas if c not in destino["citas"]]
            destino["excluyente"] = destino["excluyente"] or bool(r.get("excluyente"))
            por_ref[ref] = destino
            continue
        evidencia = ia.get("tipo_evidencia") if ia.get("tipo_evidencia") in EVIDENCIAS else "texto"
        item = {"orden": n, "clave": clave_de(r["requisito"]), "requisito": r["requisito"].strip(),
                "tipo": r.get("tipo") if r.get("tipo") in TIPOS_REQUISITO else "tecnico",
                "tipo_evidencia": evidencia, "excluyente": bool(r.get("excluyente")), "citas": citas,
                **_minimo(ia, r["requisito"], expediente)}
        items.append(item)
        por_ref[ref] = item
    return items


def _guardar_generacion(conn, nro_sicop, resumen_id, uso_id, huella, modelo, estado, motivo, items, quien) -> int:
    return conn.execute(
        "INSERT INTO eligibility_generations (nro_sicop, ia_summary_id, ia_usage_id, huella, prompt_version, modelo,"
        " estado, motivo, items, generado_por, generado_por_nombre, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nro_sicop, resumen_id, uso_id, huella, VERSION, modelo, estado, motivo, items, quien.user_id, quien.nombre,
         _ahora())).lastrowid


def _ahora() -> str:
    return datetime.now(HORA_CR).isoformat(timespec="seconds")


def generar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, cliente=None,
            dormir=None) -> Generacion:
    """Genera (o vuelve a generar) la lista con IA. Lanza VerificacionError sin llamar a OpenAI si no corresponde."""
    resumen_id, reqs = requerimientos(conn, nro_sicop)
    if resumen_id is None:
        raise VerificacionError("Este cartel todavía no tiene resumen con IA: la lista sale de sus requerimientos.")
    if not reqs:
        raise VerificacionError("El resumen con IA de este cartel no trae requerimientos.")
    if settings.ai_mode != "openai":
        raise VerificacionError("La IA está apagada (AI_MODE=none): no se puede generar la lista.")
    if costo_de_hoy(conn, datetime.now(HORA_CR).date()) >= settings.ia_max_daily_cost:
        raise VerificacionError(f"Ya se usó el presupuesto de IA de hoy ({settings.ia_max_daily_cost} USD,"
                                " IA_MAX_DAILY_COST). Vuelve a intentarlo mañana.")
    exp = armar_expediente(conn, nro_sicop, settings.ia_max_input_tokens)
    if exp is None:
        raise VerificacionError(f"No hay un cartel con Número SICOP {nro_sicop}.")
    extra = {"dormir": dormir} if dormir is not None else {}
    try:
        r = ia_cliente.pedir(conn, settings, cargar_prompt(), texto_para_ia(reqs, exp.texto), "verificacion",
                             nro_sicop, cliente=cliente, formato=FORMATO, **extra)
    except (ia_cliente.IaApagada, ia_cliente.IaConfiguracion) as exc:
        raise VerificacionError(str(exc)) from None
    except ia_cliente.IaFallo as exc:
        with transaccion(conn):
            _guardar_generacion(conn, nro_sicop, resumen_id, exc.uso_id, exp.huella, settings.openai_model,
                                "fallido", exc.motivo, 0, quien)
        raise VerificacionError(f"OpenAI no respondió bien ({exc.motivo}). No se cambió la lista.") from None
    try:
        crudo = json.loads(r.texto) if r.resultado == "ok" else None
    except ValueError:
        crudo = None
    if not isinstance(crudo, dict):
        motivo = r.motivo or "la respuesta no es JSON válido"
        with transaccion(conn):
            _guardar_generacion(conn, nro_sicop, resumen_id, r.uso_id, exp.huella, r.modelo, "fallido", motivo, 0,
                                quien)
        raise VerificacionError(f"La respuesta de la IA no sirvió ({motivo}). No se cambió la lista.")
    items = armar_items(reqs, normalizar(crudo, ESQUEMA), exp.texto)
    claves = _claves_perfil()
    with transaccion(conn):
        generacion = _guardar_generacion(conn, nro_sicop, resumen_id, r.uso_id, exp.huella, r.modelo, "ok", None,
                                         len(items), quien)
        _aplicar(conn, nro_sicop, items, generacion, claves)
        historial.registrar(conn, quien, "generar_lista_verificacion", f"{nro_sicop}: {len(items)} requisitos")
    return ultima_generacion(conn, nro_sicop)


def _aplicar(conn: sqlite3.Connection, nro_sicop: str, items: list[dict], generacion: int,
             claves: dict[str, list[str]]) -> None:
    """Pone la lista nueva sin tocar lo que hizo una persona (corregido, agregado o quitado)."""
    existentes = {f[0]: f[1:] for f in conn.execute(
        "SELECT clave, id, origen, editado, activo, perfil_confirmado FROM eligibility_items WHERE nro_sicop = ?",
        (nro_sicop,))}
    nuevas = set()
    for it in items:
        nuevas.add(it["clave"])
        previo = existentes.get(it["clave"])
        campos = (it["orden"], it["requisito"], it["tipo"], it["tipo_evidencia"], it["minimo"], it["minimo_numero"],
                  it["minimo_fecha"], it["unidad"], int(it["excluyente"]), json.dumps(it["citas"], ensure_ascii=False))
        if previo is None:
            conn.execute(
                "INSERT INTO eligibility_items (nro_sicop, orden, clave, requisito, tipo, tipo_evidencia, minimo,"
                " minimo_numero, minimo_fecha, unidad, excluyente, citas, perfil_item_id, origen, generacion_id,"
                " creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ia', ?, ?)",
                (nro_sicop, it["orden"], it["clave"], *campos[1:], proponer_perfil(conn, it["requisito"], claves),
                 generacion, _ahora()))
            continue
        item_id, origen, editado, activo, confirmado = previo
        if origen == "usuario" or editado:
            continue                                                   # lo de una persona no se toca
        perfil = None if confirmado else proponer_perfil(conn, it["requisito"], claves)
        conn.execute(
            "UPDATE eligibility_items SET orden = ?, requisito = ?, tipo = ?, tipo_evidencia = ?, minimo = ?,"
            " minimo_numero = ?, minimo_fecha = ?, unidad = ?, excluyente = ?, citas = ?, activo = 1,"
            " generacion_id = ?" + ("" if confirmado else ", perfil_item_id = ?") + " WHERE id = ?",
            (*campos, generacion, *(() if confirmado else (perfil,)), item_id))
    # Lo que vino de una lista anterior y ya no está (sin tocar por nadie) se retira; no se borra.
    for clave, (item_id, origen, editado, activo, _) in existentes.items():
        if clave not in nuevas and origen == "ia" and not editado and activo:
            conn.execute("UPDATE eligibility_items SET activo = 0 WHERE id = ?", (item_id,))


# --- Cambios de una persona ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Cambios:
    requisito: str
    tipo: str
    tipo_evidencia: str
    minimo: str
    minimo_numero: str
    minimo_fecha: str
    unidad: str
    excluyente: bool


def _limpiar(c: Cambios) -> dict:
    requisito = " ".join(c.requisito.split())[:1000]
    if not requisito:
        raise VerificacionError("Escribe el requisito.")
    if c.tipo not in TIPOS:
        raise VerificacionError("Elige el tipo del requisito.")
    if c.tipo_evidencia not in EVIDENCIAS:
        raise VerificacionError("Elige qué tipo de respuesta lo demuestra.")
    numero = c.minimo_numero.strip().replace(" ", "")
    if numero:
        try:
            numero = str(Decimal(numero.replace(",", ".")))
        except InvalidOperation:
            raise VerificacionError(f"«{c.minimo_numero}» no es un número.") from None
    fecha = c.minimo_fecha.strip()
    if fecha:
        try:
            fecha = date.fromisoformat(fecha).isoformat()
        except ValueError:
            raise VerificacionError("La fecha mínima no es válida (AAAA-MM-DD).") from None
    return {"requisito": requisito, "tipo": c.tipo, "tipo_evidencia": c.tipo_evidencia,
            "minimo": " ".join(c.minimo.split())[:300] or NO_INDICADO, "minimo_numero": numero or None,
            "minimo_fecha": fecha or None, "unidad": " ".join(c.unidad.split())[:40] or None,
            "excluyente": int(c.excluyente)}


def _del_cartel(conn: sqlite3.Connection, nro_sicop: str, item_id: int) -> tuple:
    fila = conn.execute("SELECT id, requisito FROM eligibility_items WHERE id = ? AND nro_sicop = ?",
                        (item_id, nro_sicop)).fetchone()
    if fila is None:
        raise VerificacionError("Ese requisito no está en la lista de este cartel.")
    return fila


def corregir(conn: sqlite3.Connection, nro_sicop: str, item_id: int, cambios: Cambios, quien: Quien) -> None:
    _del_cartel(conn, nro_sicop, item_id)
    campos = _limpiar(cambios)
    with transaccion(conn):
        conn.execute(
            "UPDATE eligibility_items SET requisito = ?, tipo = ?, tipo_evidencia = ?, minimo = ?, minimo_numero = ?,"
            " minimo_fecha = ?, unidad = ?, excluyente = ?, editado = 1, editado_por_nombre = ?, editado_en = ?"
            " WHERE id = ?", (*campos.values(), quien.nombre, _ahora(), item_id))
        historial.registrar(conn, quien, "corregir_item_verificacion", f"{nro_sicop}: {campos['requisito'][:120]}")


def agregar(conn: sqlite3.Connection, nro_sicop: str, cambios: Cambios, quien: Quien) -> int:
    campos = _limpiar(cambios)
    orden = (conn.execute("SELECT max(orden) FROM eligibility_items WHERE nro_sicop = ?", (nro_sicop,)).fetchone()[0]
             or 0) + 1
    with transaccion(conn):
        item_id = conn.execute(
            "INSERT INTO eligibility_items (nro_sicop, orden, clave, requisito, tipo, tipo_evidencia, minimo,"
            " minimo_numero, minimo_fecha, unidad, excluyente, perfil_item_id, origen, editado, editado_por_nombre,"
            " editado_en, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'usuario', 1, ?, ?, ?)",
            (nro_sicop, orden, f"usuario-{secrets.token_hex(6)}", *campos.values(),
             proponer_perfil(conn, campos["requisito"]), quien.nombre, _ahora(), _ahora())).lastrowid
        historial.registrar(conn, quien, "agregar_item_verificacion", f"{nro_sicop}: {campos['requisito'][:120]}")
    return item_id


def quitar(conn: sqlite3.Connection, nro_sicop: str, item_id: int, quien: Quien) -> None:
    """Lo saca de la lista (no se borra) y queda marcado como decisión de una persona: no vuelve al regenerar."""
    _, requisito = _del_cartel(conn, nro_sicop, item_id)
    with transaccion(conn):
        conn.execute("UPDATE eligibility_items SET activo = 0, editado = 1, editado_por_nombre = ?, editado_en = ?"
                     " WHERE id = ?", (quien.nombre, _ahora(), item_id))
        historial.registrar(conn, quien, "quitar_item_verificacion", f"{nro_sicop}: {requisito[:120]}")


def volver_a_poner(conn: sqlite3.Connection, nro_sicop: str, item_id: int, quien: Quien) -> None:
    _, requisito = _del_cartel(conn, nro_sicop, item_id)
    with transaccion(conn):
        conn.execute("UPDATE eligibility_items SET activo = 1, editado = 1, editado_por_nombre = ?, editado_en = ?"
                     " WHERE id = ?", (quien.nombre, _ahora(), item_id))
        historial.registrar(conn, quien, "corregir_item_verificacion", f"{nro_sicop}: volvió «{requisito[:100]}»")


def elegir_perfil(conn: sqlite3.Connection, nro_sicop: str, item_id: int, perfil_item_id: int | None,
                  quien: Quien) -> None:
    """Confirma (o cambia, o quita) el elemento del perfil que prueba este requisito."""
    _, requisito = _del_cartel(conn, nro_sicop, item_id)
    if perfil_item_id is not None and conn.execute("SELECT 1 FROM company_profile_items WHERE id = ?",
                                                   (perfil_item_id,)).fetchone() is None:
        raise VerificacionError("Ese elemento del perfil no existe.")
    with transaccion(conn):
        conn.execute("UPDATE eligibility_items SET perfil_item_id = ?, perfil_confirmado = 1 WHERE id = ?",
                     (perfil_item_id, item_id))
        historial.registrar(conn, quien, "corregir_item_verificacion", f"{nro_sicop}: perfil de «{requisito[:100]}»")
