"""Fase 2 · el servidor recibe el enriquecimiento que hace la PC (docs/ENVIO_ENRIQUECIMIENTO.md, 2026-11-09).

La PC de Ivania consulta SICOP con su navegador (con ventana) y el servidor guarda. Tres pasos, como enrich run:

1. abrir_corrida: el borrado al cierre, la cola del día y una corrida en enrich_runs (origen 'remoto') con los
   Números SICOP que se le dan a la PC (cola_json, migración 0040).
2. aplicar_consulta, una vez por cartel: la PC manda la ficha tal cual llegó de SICOP, los archivos que bajó y la
   bitácora de la consulta. El servidor REPITE los guardados de siempre (guardar_ficha, guardar_documento con su
   revisión y el texto de los PDF, registrar_consulta) y reevalúa el cartel. No se copian filas de otra base: los
   números internos son los del servidor. Repetir un envío no duplica nada (huella de la ficha, archivo ya guardado).
3. cerrar_corrida: el estado final que dice la PC (ok, con_fallos o detenida por un CAPTCHA).

Lo que la PC no puede decidir: si la ficha es nueva o sin cambios (lo dice la base del servidor), qué carteles se
consultan (solo los de cola_json) ni qué archivos se aceptan (la misma revisión de tipo y tamaño de siempre). Los
datos de personas se vuelven a quitar de la ficha aunque la PC ya los haya quitado.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from decimal import Decimal

from app.config import Settings
from app.database import transaccion
from app.sources import enriquecimiento as en
from app.sources import sicop_documentos as sd
from app.sources.sicop_tender_detail import Consulta, Ficha, _limpiar, guardar_ficha, registrar_consulta

RESULTADOS = ("nueva", "sin_cambios", "fallo", "control")   # los de enrich_consultas
CIERRES = ("ok", "con_fallos", "detenida")
MB = 1024 * 1024


class RemotoError(ValueError):
    """La petición de la PC no se puede aplicar. estado: el código HTTP que se le devuelve."""

    def __init__(self, mensaje: str, estado: int = 400):
        super().__init__(mensaje)
        self.estado = estado


# --- 1. Abrir ------------------------------------------------------------------------------------------------------

def abrir_corrida(conn: sqlite3.Connection, settings: Settings, ahora: datetime) -> dict:
    """Borrado al cierre, cola del día y corrida nueva. Una corrida remota que quedó abierta (la PC se apagó a la
    mitad) se cierra como «detenida»: lo que alcanzó a mandar ya está guardado."""
    en.revisar_base(conn, [], documentos=True)
    momento = ahora.isoformat(timespec="seconds")
    with transaccion(conn):
        conn.execute("UPDATE enrich_runs SET estado = 'detenida', terminada_en = ?, motivo = coalesce(motivo,"
                     " 'la PC no cerró la corrida') WHERE origen = 'remoto' AND estado = 'en_curso'", (momento,))
        run_id = conn.execute("INSERT INTO enrich_runs (iniciada_en, maximo, origen) VALUES (?, ?, 'remoto')",
                              (momento, settings.enrich_max_per_day)).lastrowid
    retiros = en.retirar(conn, settings, ahora, run_id)
    borrados = [r.nro_sicop for r in retiros if r.hasta_detalle_id is not None]
    if borrados:
        en.reevaluar(conn, borrados)
    lista = en.cola(conn, settings, ahora)
    hoy = lista[:en.cupo_de_hoy(conn, settings, ahora)]
    with transaccion(conn):
        conn.execute("UPDATE enrich_runs SET en_cola = ?, cola_json = ?, estado = CASE WHEN ? THEN 'en_curso'"
                     " ELSE 'sin_cola' END, terminada_en = CASE WHEN ? THEN NULL ELSE ? END WHERE id = ?",
                     (len(lista), json.dumps([c.nro_sicop for c in hoy]), bool(hoy), bool(hoy), momento, run_id))
    guardados: dict[str, list[str]] = {}
    for c in hoy:
        guardados[c.nro_sicop] = [s for (s,) in conn.execute(
            "SELECT server_file FROM tender_documents WHERE nro_sicop = ? AND estado = 'guardado' ORDER BY id",
            (c.nro_sicop,))]
    return {
        "corrida": run_id, "en_cola": len(lista), "maximo": settings.enrich_max_per_day,
        "borrados_al_cierre": borrados,
        "carteles": [{"nro_sicop": c.nro_sicop, "descripcion": c.descripcion, "cierre": c.cierre,
                      "motivo": c.motivo, "encaje": c.encaje, "documentos_guardados": guardados[c.nro_sicop]}
                     for c in hoy],
    }


# --- 2. Una consulta -----------------------------------------------------------------------------------------------

def _corrida_abierta(conn: sqlite3.Connection, run_id: int) -> list[str]:
    fila = conn.execute("SELECT estado, origen, cola_json FROM enrich_runs WHERE id = ?", (run_id,)).fetchone()
    if fila is None or fila[1] != "remoto":
        raise RemotoError(f"No existe la corrida remota {run_id}.", 404)
    if fila[0] != "en_curso":
        raise RemotoError(f"La corrida {run_id} ya terminó ({fila[0]}): abre otra.", 409)
    return json.loads(fila[2] or "[]")


def _ficha(nro: str, respuestas_json: str) -> Ficha:
    try:
        respuestas = json.loads(respuestas_json, parse_float=Decimal)
    except ValueError:
        raise RemotoError("La ficha no es JSON.") from None
    if not isinstance(respuestas, dict) or not isinstance(respuestas.get("documentos", []), list):
        raise RemotoError("La ficha no tiene la forma de las respuestas de SICOP.")
    busqueda = respuestas.get("busqueda") or {}
    if str(busqueda.get("cartelNo", "")) != nro:
        raise RemotoError(f"La ficha es de otro cartel ({busqueda.get('cartelNo')!r}), no de {nro}.")
    quitados: set[str] = set()
    limpias = {nombre: _limpiar(valor, quitados) for nombre, valor in respuestas.items()}
    return Ficha(nro, limpias, tuple(sorted(quitados)))


def _documentos(conn: sqlite3.Connection, settings: Settings, nro: str, detalle_id: int, ficha: Ficha,
                informados: dict[str, dict], archivos: dict[str, bytes], ahora: datetime) -> list:
    """Repite, documento por documento de la ficha, lo que hace descargar_documentos con lo que bajó la PC."""
    resultados = []
    tope = settings.documents_max_mb_per_tender * MB
    for doc in ficha.respuestas.get("documentos") or []:
        seq, nombre = sd._t(doc.get("docFileSeqno")) or "", sd._t(doc.get("clientFileNm")) or ""
        server = sd._t(doc.get("serverFileNm")) or ""
        if not sd.SERVER_FILE.match(server):
            motivo = "el nombre del archivo en el servidor de SICOP no tiene la forma esperada: no se pide"
            sd._registrar(conn, nro, detalle_id, doc, server or "?", ahora, "rechazado", motivo)
            resultados.append(sd.ResultadoDocumento(seq, nombre, "rechazado", motivo=motivo))
            continue
        if conn.execute("SELECT 1 FROM tender_documents WHERE nro_sicop = ? AND server_file = ? AND"
                        " estado = 'guardado'", (nro, server)).fetchone():
            resultados.append(sd.ResultadoDocumento(seq, nombre, "ya_guardado", motivo="ya estaba guardado"))
            continue
        datos = archivos.get(server)
        if datos is None:
            # La PC no lo bajó: lo anota con el motivo que ella dio (omitido por tamaño, fallo de descarga…).
            info = informados.get(server) or {}
            estado = info.get("estado") if info.get("estado") in ("omitido_tamano", "omitido_tope", "fallo",
                                                                   "rechazado") else "fallo"
            motivo = str(info.get("motivo") or "la PC no mandó el archivo")[:500]
            sd._registrar(conn, nro, detalle_id, doc, server, ahora, estado, motivo)
            resultados.append(sd.ResultadoDocumento(seq, nombre, estado, motivo=motivo))
            continue
        ya = conn.execute("SELECT coalesce(sum(tamano_bytes), 0) FROM tender_documents WHERE nro_sicop = ? AND"
                          " estado = 'guardado'", (nro,)).fetchone()[0]
        if ya + len(datos) > tope:
            motivo = (f"el cartel ya tiene {ya / MB:.1f} MB guardados y con este pasaría el tope de "
                      f"{settings.documents_max_mb_per_tender} MB: no se guarda")
            sd._registrar(conn, nro, detalle_id, doc, server, ahora, "omitido_tope", motivo)
            resultados.append(sd.ResultadoDocumento(seq, nombre, "omitido_tope", motivo=motivo))
            continue
        resultados.append(sd.guardar_documento(conn, settings, nro, detalle_id, doc, datos, ahora))
    return resultados


def aplicar_consulta(conn: sqlite3.Connection, settings: Settings, run_id: int, consulta: dict,
                     archivos: dict[str, bytes], ahora: datetime) -> dict:
    """Guarda lo que la PC consultó de un cartel. `consulta`: nro_sicop, resultado, motivo, iniciada_en,
    duracion_s, grabacion, es_reintento, ficha (las respuestas de SICOP en JSON, o None si no llegó a abrirla) y
    documentos ({serverFileNm: {estado, motivo}} de lo que no bajó). `archivos`: {serverFileNm: bytes}."""
    cola = _corrida_abierta(conn, run_id)
    nro = str(consulta.get("nro_sicop") or "")
    if nro not in cola:
        raise RemotoError(f"El cartel {nro or '(sin número)'} no estaba en la cola de esta corrida.", 403)
    resultado = consulta.get("resultado")
    if resultado not in RESULTADOS:
        raise RemotoError(f"Resultado no válido: {resultado!r}.")
    guardado = campos = None
    documentos: list = []
    if consulta.get("ficha"):
        ficha = _ficha(nro, consulta["ficha"])
        with transaccion(conn):
            guardado, campos = guardar_ficha(conn, ficha, ahora)
        informados = consulta.get("documentos") or {}
        documentos = _documentos(conn, settings, nro, guardado.detalle_id, ficha,
                                 informados if isinstance(informados, dict) else {}, archivos, ahora)
        if resultado in ("nueva", "sin_cambios"):
            resultado = "nueva" if guardado.nueva else "sin_cambios"   # lo decide la base del servidor
    elif resultado in ("nueva", "sin_cambios"):
        raise RemotoError("Una consulta «nueva» o «sin cambios» tiene que traer la ficha.")
    c = Consulta(nro, resultado, str(consulta.get("motivo") or "")[:1000], guardado=guardado, campos=campos,
                 documentos=documentos)
    c.grabacion = str(consulta.get("grabacion") or "")[:100] or None
    c.duracion_s = float(consulta["duracion_s"]) if consulta.get("duracion_s") is not None else None
    c.iniciada_en = str(consulta.get("iniciada_en") or ahora.isoformat(timespec="seconds"))[:40]
    consulta_id = registrar_consulta(conn, c, run_id, es_reintento=bool(consulta.get("es_reintento")))
    if resultado in ("nueva", "sin_cambios"):
        en.reevaluar(conn, [nro])
    return {"consulta": consulta_id, "nro_sicop": nro, "resultado": resultado,
            "documentos": [{"nombre": d.nombre, "estado": d.estado, "motivo": d.motivo} for d in documentos]}


# --- 3. Cerrar -----------------------------------------------------------------------------------------------------

def cerrar_corrida(conn: sqlite3.Connection, run_id: int, estado: str, motivo: str | None, ahora: datetime) -> dict:
    _corrida_abierta(conn, run_id)
    if estado not in CIERRES:
        raise RemotoError(f"Estado final no válido: {estado!r} (ok, con_fallos o detenida).")
    consultados, fallos = conn.execute(
        "SELECT count(*), coalesce(sum(resultado IN ('fallo', 'control')), 0) FROM enrich_consultas"
        " WHERE run_id = ? AND es_reintento = 0", (run_id,)).fetchone()
    with transaccion(conn):
        conn.execute("UPDATE enrich_runs SET terminada_en = ?, estado = ?, consultados = ?, fallos = ?, motivo = ?"
                     " WHERE id = ?", (ahora.isoformat(timespec="seconds"), estado, consultados, fallos,
                                       (motivo or "")[:1000] or None, run_id))
    return {"corrida": run_id, "estado": estado, "consultados": consultados, "fallos": fallos}
