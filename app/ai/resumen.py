"""Resumen ejecutivo de un cartel con IA (Reporte con IA, lección 3; docs/RESUMEN_IA.md §4).

* El modelo lee el expediente (lección 1) con el prompt versionado de config/prompts/resumen_cartel_<versión>.md
  y responde con SALIDA ESTRUCTURADA estricta: un JSON que cumple ESQUEMA, siempre con los mismos campos.
* Lo que no está en el expediente dice «no encontrado» (NO). Si falta un campo en la respuesta, se completa así.
* Las fechas de cierre y apertura, el monto estimado y las cantidades por línea que diga el resumen se comparan con
  los datos de SICOP de la base. Si alguno no coincide, el resumen queda «revisar» con la diferencia.
* Se guarda en ia_summaries (migración 0026). Mismo expediente (huella) y misma versión del prompt con un resumen
  ok o revisar = no se vuelve a llamar a OpenAI.
* Rechazo del modelo, respuesta incompleta, JSON inválido o error = «fallido» con su motivo, sin resumen.
* La recomendación es preliminar: no toca revisiones, decisiones ni seguimientos.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from app.ai import cliente as ia_cliente
from app.ai.expediente import Expediente, armar_expediente
from app.compras import detalle_compra
from app.config import Settings
from app.database import transaccion
from app.dinero import texto_decimal
from app.fichas_panel import informacion
from app.importers.comun import HORA_CR

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "config" / "prompts"
NO = "no encontrado"
RECOMENDACIONES = {"dar_seguimiento": "Dar seguimiento", "revisar_requisitos": "Revisar requisitos",
                   "descartar": "Descartar"}
TIPOS_REQUISITO = ("tecnico", "legal", "financiero", "experiencia")
ESTADOS = {"ok": "OK", "revisar": "Revisar", "fallido": "Fallido"}


class ResumenError(ValueError):
    """No se pudo pedir el resumen (sin llamar a OpenAI); el mensaje es el que verá la persona."""


# --- Esquema de la salida estructurada ---------------------------------------------------------------------------
# En modo estricto, OpenAI exige que cada objeto liste todos sus campos en «required» y no admita otros.

def _objeto(**campos) -> dict:
    return {"type": "object", "properties": campos, "required": list(campos), "additionalProperties": False}


def _texto(descripcion: str) -> dict:
    return {"type": "string", "description": descripcion}


def _lista(elemento: dict) -> dict:
    return {"type": "array", "items": elemento}


_CITA = _texto("Marca [DOC n · pág. p], «SICOP» si viene de CARTEL, LÍNEAS o FICHA SICOP, o «no encontrado»")
_DATO = _objeto(valor=_texto("El dato tal como lo dice el expediente, o «no encontrado»"), cita=_CITA)
_FECHA = _objeto(valor=_texto("AAAA-MM-DD o AAAA-MM-DD HH:MM (hora de Costa Rica), o «no encontrado»"), cita=_CITA)

ESQUEMA = _objeto(
    de_que_trata=_texto("2 o 3 frases en lenguaje sencillo: qué compra la institución y para qué"),
    que_piden=_lista(_objeto(
        linea=_texto("Número de línea del cartel, o «no encontrado»"),
        bien_o_servicio=_texto("Qué se compra"),
        cantidad=_texto("Solo el número, o «no encontrado»"),
        especificaciones_clave=_lista(_texto("Especificación técnica que más pesa")),
        cita=_CITA)),
    requerimientos=_lista(_objeto(
        requisito=_texto("Un requisito, separado de los demás"),
        tipo={"type": "string", "enum": list(TIPOS_REQUISITO)},
        excluyente={"type": "boolean", "description": "true si sin él la oferta se descarta"},
        cita=_CITA)),
    kpi_pliego=_objeto(
        plazo_entrega=_DATO, vigencia_contrato=_DATO, garantia_participacion_pct=_DATO,
        garantia_cumplimiento_pct=_DATO, peso_precio_pct=_DATO,
        nivel_riesgo=_objeto(valor={"type": "string", "enum": ["bajo", "medio", "alto", NO]}, cita=_CITA)),
    plazos=_objeto(
        cierre_recepcion=_FECHA, apertura_ofertas=_FECHA,
        otros=_lista(_objeto(plazo=_texto("Qué plazo es"), valor=_texto("El plazo o la fecha"), cita=_CITA))),
    monto_estimado=_objeto(
        valor=_texto("Solo dígitos y punto decimal, sin separador de miles (12500000.00), o «no encontrado»"),
        moneda=_texto("CRC, USD…, o «no encontrado»"), cita=_CITA),
    criterios_de_evaluacion=_lista(_objeto(criterio=_texto("El criterio"), peso=_texto("Su peso o puntaje"),
                                           cita=_CITA)),
    encaje_hermatix=_objeto(familia=_texto("Familia del portafolio, o «ninguna»"),
                            producto=_texto("Producto de Hermatix, o «ninguno»"),
                            por_que=_texto("Por qué encaja o por qué no")),
    riesgos_y_dudas=_lista(_objeto(riesgo=_texto("Lo que podría impedir ofertar"), cita=_CITA)),
    recomendacion={"type": "string", "enum": list(RECOMENDACIONES)},
    justificacion=_texto("Una o dos frases con datos del expediente; la decisión final es del encargado"),
)
FORMATO = {"type": "json_schema", "name": "resumen_cartel", "schema": ESQUEMA, "strict": True}


def cargar_prompt(version: str) -> str:
    ruta = PROMPTS_DIR / f"resumen_cartel_{version}.md"
    try:
        return ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ResumenError(f"No existe el prompt {ruta.name} en config/prompts (IA_PROMPT_VERSION={version}).") from None


def normalizar(valor, esquema: dict = ESQUEMA):
    """Completa lo que falte según el esquema: un texto ausente es «no encontrado» y una lista ausente, vacía."""
    tipo = esquema.get("type")
    if tipo == "object":
        valor = valor if isinstance(valor, dict) else {}
        return {campo: normalizar(valor.get(campo), sub) for campo, sub in esquema["properties"].items()}
    if tipo == "array":
        return [normalizar(v, esquema["items"]) for v in valor] if isinstance(valor, list) else []
    if tipo == "boolean":
        return valor if isinstance(valor, bool) else None
    if not isinstance(valor, str) or not valor.strip():
        return NO
    if "enum" in esquema and valor not in esquema["enum"]:
        return NO
    return valor.strip()


# --- Comparación con SICOP ----------------------------------------------------------------------------------------

_FECHA_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?")
_NUMERO_RE = re.compile(r"\d+(?:\.\d+)?")


def _fecha_sicop(iso: str | None) -> tuple[str, str] | None:
    if not iso:
        return None
    try:
        fecha = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(HORA_CR)
    return fecha.strftime("%Y-%m-%d"), fecha.strftime("%H:%M")


def _decimal(texto: str | None) -> Decimal | None:
    if not texto:
        return None
    hallado = _NUMERO_RE.search(texto.replace(" ", ""))
    try:
        return Decimal(hallado.group()) if hallado else None
    except InvalidOperation:
        return None


def comparar(conn: sqlite3.Connection, nro_sicop: str, datos: dict) -> list[dict]:
    """Las fechas, el monto y las cantidades del resumen que NO coinciden con la base: [{dato, resumen, sicop}]."""
    compra = detalle_compra(conn, nro_sicop)
    info = informacion(conn, nro_sicop)
    diferencias: list[dict] = []

    def fecha(dato: str, del_resumen: str, de_sicop: str | None) -> None:
        sicop = _fecha_sicop(de_sicop)
        hallada = _FECHA_RE.search(del_resumen) if del_resumen != NO else None
        if sicop is None or hallada is None:
            return  # sin dato en SICOP o «no encontrado» en el resumen: no hay nada que comparar
        dia, hora = hallada.groups()
        if dia != sicop[0] or (hora is not None and hora != sicop[1]):
            diferencias.append({"dato": dato, "resumen": del_resumen, "sicop": f"{sicop[0]} {sicop[1]}"})

    plazos = datos["plazos"]
    fecha("Cierre de recepción", plazos["cierre_recepcion"]["valor"],
          info.cierre if info and info.cierre else compra.fecha_cierre_recepcion)
    fecha("Apertura de ofertas", plazos["apertura_ofertas"]["valor"], info.apertura if info else None)

    monto = datos["monto_estimado"]
    if info and info.monto is not None and monto["valor"] != NO:
        del_resumen = _decimal(monto["valor"])
        moneda = monto["moneda"].strip().upper()
        if (del_resumen is not None and del_resumen.quantize(Decimal("0.01")) != info.monto.quantize(Decimal("0.01"))) \
                or (moneda != NO.upper() and info.moneda and moneda != info.moneda.upper()):
            diferencias.append({"dato": "Monto estimado", "resumen": f"{monto['valor']} {monto['moneda']}",
                                "sicop": f"{texto_decimal(info.monto)} {info.moneda}"})

    cantidades = {linea.numero_linea.strip(): linea.cantidad for linea in compra.lineas}
    for item in datos["que_piden"]:
        linea = (item["linea"] or "").strip()
        if linea not in cantidades or item["cantidad"] == NO:
            continue
        del_resumen, de_sicop = _decimal(item["cantidad"]), _decimal(cantidades[linea])
        if del_resumen is not None and de_sicop is not None and del_resumen != de_sicop:
            diferencias.append({"dato": f"Cantidad de la línea {linea}", "resumen": item["cantidad"],
                                "sicop": cantidades[linea]})
    return diferencias


# --- Pedir y guardar ----------------------------------------------------------------------------------------------

@dataclass
class Resultado:
    id: int
    nro_sicop: str
    estado: str                    # ok · revisar · fallido
    reutilizado: bool              # True: ya había uno de este expediente con este prompt; no se llamó a OpenAI
    creado_en: str
    modelo: str
    prompt_version: str
    huella: str
    datos: dict | None
    diferencias: list[dict] = field(default_factory=list)
    motivo: str | None = None
    costo: Decimal | None = None
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    expediente: Expediente | None = None


_COLUMNAS = ("id, nro_sicop, estado, creado_en, modelo, prompt_version, huella, resumen_json, diferencias_json, motivo,"
             " costo_estimado")


def _de_fila(fila, reutilizado: bool, expediente: Expediente | None = None) -> Resultado:
    (id_, nro, estado, creado, modelo, version, huella, resumen_json, diferencias_json, motivo, costo) = fila
    return Resultado(id_, nro, estado, reutilizado, creado, modelo, version, huella,
                     json.loads(resumen_json) if resumen_json else None,
                     json.loads(diferencias_json) if diferencias_json else [], motivo,
                     Decimal(costo) if costo else None, expediente=expediente)


def _guardar(conn: sqlite3.Connection, exp: Expediente, version: str, modelo: str, datos: dict | None, estado: str,
             motivo: str | None, diferencias: list[dict], costo: Decimal | None, uso_id: int | None) -> int:
    with transaccion(conn):
        return conn.execute(
            "INSERT INTO ia_summaries (nro_sicop, prompt_version, modelo, huella, resumen_json, estado, motivo,"
            " diferencias_json, costo_estimado, moneda, ia_usage_id, creado_en) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
            " ?, ?)",
            (exp.nro_sicop, version, modelo, exp.huella, json.dumps(datos, ensure_ascii=False) if datos else None,
             estado, motivo, json.dumps(diferencias, ensure_ascii=False) if diferencias else None,
             texto_decimal(costo) if costo is not None else None, "USD" if costo is not None else None, uso_id,
             datetime.now(HORA_CR).isoformat(timespec="seconds"))).lastrowid


def _cargar(conn: sqlite3.Connection, id_: int, exp: Expediente, r=None) -> Resultado:
    """El resumen recién guardado, leído de la base (con los tokens de la respuesta, si hubo)."""
    res = _de_fila(conn.execute(f"SELECT {_COLUMNAS} FROM ia_summaries WHERE id = ?", (id_,)).fetchone(), False, exp)
    if r is not None:
        res.tokens_entrada, res.tokens_salida = r.tokens_entrada, r.tokens_salida
    return res


def _costo_del_uso(conn: sqlite3.Connection, uso_id: int) -> Decimal | None:
    fila = conn.execute("SELECT costo_estimado FROM ia_usage WHERE id = ?", (uso_id,)).fetchone()
    return Decimal(fila[0]) if fila and fila[0] else None


def resumir(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, cliente=None,
            dormir: Callable[[float], None] | None = None) -> Resultado:
    """Pide (o reutiliza) el resumen del cartel. Lanza ResumenError, IaApagada o IaConfiguracion sin llamar.
    cliente y dormir solo se cambian en las pruebas (OpenAI SIMULADO)."""
    version = settings.ia_prompt_version
    instrucciones = cargar_prompt(version)
    exp = armar_expediente(conn, nro_sicop, settings.ia_max_input_tokens)
    if exp is None:
        raise ResumenError(f"No hay un cartel con Número SICOP {nro_sicop}.")
    anterior = conn.execute(
        f"SELECT {_COLUMNAS} FROM ia_summaries WHERE nro_sicop = ? AND huella = ? AND prompt_version = ?"
        " AND estado IN ('ok', 'revisar') ORDER BY id DESC LIMIT 1", (nro_sicop, exp.huella, version)).fetchone()
    if anterior:
        return _de_fila(anterior, reutilizado=True, expediente=exp)

    extra = {"dormir": dormir} if dormir is not None else {}
    try:
        r = ia_cliente.pedir(conn, settings, instrucciones, exp.texto, "resumen", nro_sicop, cliente=cliente,
                             formato=FORMATO, **extra)
    except ia_cliente.IaFallo as exc:
        costo = _costo_del_uso(conn, exc.uso_id)
        id_ = _guardar(conn, exp, version, settings.openai_model, None, "fallido", exc.motivo, [], costo, exc.uso_id)
        return _cargar(conn, id_, exp)

    def fallido(motivo: str) -> Resultado:
        return _cargar(conn, _guardar(conn, exp, version, r.modelo, None, "fallido", motivo, [], r.costo, r.uso_id),
                       exp, r)

    if r.resultado != "ok":
        return fallido(r.motivo or "respuesta incompleta")
    try:
        crudo = json.loads(r.texto)
    except ValueError:
        return fallido("la respuesta no es JSON válido")
    if not isinstance(crudo, dict):
        return fallido("la respuesta no es JSON válido")
    datos = normalizar(crudo)
    diferencias = comparar(conn, nro_sicop, datos)
    estado = "revisar" if diferencias else "ok"
    return _cargar(conn, _guardar(conn, exp, version, r.modelo, datos, estado, None, diferencias, r.costo, r.uso_id),
                   exp, r)


# --- Texto para leer (EXPORTS_DIR) --------------------------------------------------------------------------------

def _con_cita(texto: str, cita: str) -> str:
    if cita in (NO, ""):
        return texto
    return f"{texto} [SICOP]" if cita == "SICOP" else f"{texto} {cita}"


def legible(res: Resultado) -> str:
    """El resumen como texto, para revisarlo con Oscar. No es el reporte de 2 páginas (lección 4)."""
    lineas = [f"RESUMEN DEL CARTEL {res.nro_sicop} · generado con IA · PRELIMINAR",
              f"Estado: {ESTADOS[res.estado]} · prompt {res.prompt_version} · modelo {res.modelo}"
              f" · resumen #{res.id}{' (ya existía: no se llamó a OpenAI)' if res.reutilizado else ''}",
              f"Huella del expediente: {res.huella}", ""]
    if res.diferencias:
        lineas += ["== NO COINCIDE CON SICOP (revisar) =="]
        lineas += [f"- {d['dato']}: el resumen dice «{d['resumen']}», SICOP dice «{d['sicop']}»" for d in res.diferencias]
        lineas.append("")
    if res.datos is None:
        lineas.append(f"Sin resumen: {res.motivo}.")
        return "\n".join(lineas) + "\n"
    d = res.datos
    lineas += ["== DE QUÉ TRATA ==", d["de_que_trata"], "", "== QUÉ PIDEN =="]
    lineas += [_con_cita(f"- Línea {i['linea']} · {i['bien_o_servicio']} · cantidad {i['cantidad']}"
                         + (f" · {'; '.join(i['especificaciones_clave'])}" if i["especificaciones_clave"] else ""),
                         i["cita"])
               for i in d["que_piden"]] or [f"- {NO}"]
    lineas += ["", "== REQUERIMIENTOS =="]
    lineas += [_con_cita(f"- [{q['tipo']}{' · EXCLUYENTE' if q['excluyente'] else ''}] {q['requisito']}", q["cita"])
               for q in d["requerimientos"]] or [f"- {NO}"]
    k = d["kpi_pliego"]
    lineas += ["", "== INDICADORES DEL PLIEGO =="]
    for clave, nombre in (("plazo_entrega", "Plazo de entrega"), ("vigencia_contrato", "Vigencia del contrato"),
                          ("garantia_participacion_pct", "Garantía de participación"),
                          ("garantia_cumplimiento_pct", "Garantía de cumplimiento"),
                          ("peso_precio_pct", "Peso del precio"), ("nivel_riesgo", "Nivel de riesgo")):
        lineas.append(_con_cita(f"- {nombre}: {k[clave]['valor']}", k[clave]["cita"]))
    p = d["plazos"]
    lineas += ["", "== PLAZOS ==", _con_cita(f"- Cierre de recepción: {p['cierre_recepcion']['valor']}",
                                             p["cierre_recepcion"]["cita"]),
               _con_cita(f"- Apertura de ofertas: {p['apertura_ofertas']['valor']}", p["apertura_ofertas"]["cita"])]
    lineas += [_con_cita(f"- {o['plazo']}: {o['valor']}", o["cita"]) for o in p["otros"]]
    m = d["monto_estimado"]
    lineas += ["", "== MONTO ESTIMADO (según el resumen) ==", _con_cita(f"- {m['valor']} {m['moneda']}", m["cita"])]
    lineas += ["", "== CRITERIOS DE EVALUACIÓN =="]
    lineas += [_con_cita(f"- {c['criterio']}: {c['peso']}", c["cita"]) for c in d["criterios_de_evaluacion"]] \
        or [f"- {NO}"]
    e = d["encaje_hermatix"]
    lineas += ["", "== ENCAJE CON HERMATIX ==", f"- {e['familia']} · {e['producto']}: {e['por_que']}"]
    lineas += ["", "== RIESGOS Y DUDAS =="]
    lineas += [_con_cita(f"- {x['riesgo']}", x["cita"]) for x in d["riesgos_y_dudas"]] or [f"- {NO}"]
    lineas += ["", "== RECOMENDACIÓN PRELIMINAR (la decisión es del encargado) ==",
               f"{RECOMENDACIONES.get(d['recomendacion'], NO)}: {d['justificacion']}"]
    return "\n".join(lineas) + "\n"
