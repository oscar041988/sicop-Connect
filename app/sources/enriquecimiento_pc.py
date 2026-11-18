"""Fase 2 · enrich remoto: la PC consulta SICOP y manda el resultado al servidor (docs/ENVIO_ENRIQUECIMIENTO.md).

La base principal está en el servidor; la PC solo pone el navegador con ventana (decisión del 27/10). Una corrida:

1. Pide al servidor que abra la corrida (POST /api/enriquecimiento/corridas, con ENRICH_TOKEN): el servidor hace el
   borrado al cierre y le devuelve la cola del día, los documentos que ya tiene de cada cartel y qué grabaciones con
   FALLO todavía no se revisaron.
2. Limpia sus grabaciones viejas (RECORDINGS_DIR, en la PC) menos esas.
3. Arma una base de trabajo NUEVA en data/trabajo/ (se borra la anterior): solo los carteles de la cola, sin nada
   más. Ahí consulta cada cartel con el mismo código de enrich run (consultar_uno), sin volver a bajar lo que el
   servidor ya tiene, y manda al terminar cada uno la ficha tal cual, los archivos y la bitácora. Lo que vale es lo
   que guarda el servidor: la base de trabajo solo sirve para la corrida.
4. Ante un CAPTCHA o bloqueo, lo mismo que enrich run (DECISION_OBTENCION.md §9): espera con el navegador cerrado,
   reintenta UNA vez y, si vuelve a salir, se detiene. Al final avisa al servidor cómo terminó.

Si el servidor no responde, se reintenta un par de veces; si sigue sin responder, la corrida se detiene (lo ya
enviado queda guardado y lo que faltó entra en la cola del día siguiente). Las grabaciones se quedan en la PC.
"""

from __future__ import annotations

import io
import json
import secrets
import shutil
import sqlite3
import time
import urllib.error
import urllib.request
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from app.bloqueo import bloqueo
from app.config import Settings
from app.database import apply_migrations, connect
from app.sources import enriquecimiento as en
from app.sources.sicop_tender_detail import Consulta, consultar_uno

API = "/api/enriquecimiento"
REINTENTOS = 3
ESPERA_REINTENTO_S = 10


class ServidorError(RuntimeError):
    """El servidor rechazó la petición o no respondió. El mensaje es el que ve la persona."""


class Transporte(Protocol):
    def post(self, ruta: str, cuerpo: bytes, tipo: str) -> tuple[int, dict]:
        """(código HTTP, respuesta JSON). Lanza ServidorError si no se pudo hablar con el servidor."""


class TransporteHttp:
    """HTTPS con urllib (sin dependencias nuevas). El token va en la cabecera, nunca en la dirección."""

    def __init__(self, base: str, token: str, timeout_s: int = 300):
        self.base, self._token, self.timeout_s = base.rstrip("/"), token, timeout_s

    def post(self, ruta: str, cuerpo: bytes, tipo: str) -> tuple[int, dict]:
        pedido = urllib.request.Request(self.base + ruta, data=cuerpo, method="POST",
                                        headers={"Authorization": f"Bearer {self._token}", "Content-Type": tipo})
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout_s) as r:  # noqa: S310 — https (config.py)
                return r.status, _json(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, _json(exc.read())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ServidorError(f"no se pudo hablar con el servidor ({getattr(exc, 'reason', exc)})") from None


def _json(crudo: bytes) -> dict:
    try:
        datos = json.loads(crudo or b"{}")
    except ValueError:
        return {"error": crudo[:200].decode("utf-8", "replace")}
    return datos if isinstance(datos, dict) else {"error": "respuesta inesperada"}


def multipart(partes: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    """(cuerpo, Content-Type) de un formulario multipart: (campo, nombre del archivo, contenido, tipo) por parte."""
    frontera = secrets.token_hex(16)
    cuerpo = io.BytesIO()
    for campo, nombre, datos, tipo in partes:
        cuerpo.write(f"--{frontera}\r\nContent-Disposition: form-data; name=\"{campo}\"; filename=\"{nombre}\"\r\n"
                     f"Content-Type: {tipo}\r\n\r\n".encode())
        cuerpo.write(datos)
        cuerpo.write(b"\r\n")
    cuerpo.write(f"--{frontera}--\r\n".encode())
    return cuerpo.getvalue(), f"multipart/form-data; boundary={frontera}"


def _llamar(transporte: Transporte, ruta: str, cuerpo: bytes, tipo: str, dormir: Callable[[float], None],
            avisar: Callable[[str], None]) -> dict:
    """Una petición con reintentos si el servidor no responde o falla por dentro (5xx). Un 4xx no se reintenta:
    es una respuesta clara (token malo, corrida cerrada, cartel fuera de la cola…)."""
    ultimo = ""
    for intento in range(1, REINTENTOS + 1):
        try:
            estado, datos = transporte.post(ruta, cuerpo, tipo)
        except ServidorError as exc:
            ultimo = str(exc)
        else:
            if estado < 400:
                return datos
            if estado < 500:
                raise ServidorError(f"el servidor respondió {estado}: {datos.get('error') or 'sin detalle'}")
            ultimo = f"el servidor respondió {estado}: {datos.get('error') or 'error interno'}"
        if intento < REINTENTOS:
            avisar(f"  {ultimo}. Reintento en {ESPERA_REINTENTO_S * intento} s…")
            dormir(ESPERA_REINTENTO_S * intento)
    raise ServidorError(ultimo)


def _llamar_json(transporte, ruta, datos: dict, dormir, avisar) -> dict:
    return _llamar(transporte, ruta, json.dumps(datos).encode(), "application/json", dormir, avisar)


# --- La base de trabajo ---------------------------------------------------------------------------------------------

def preparar_trabajo(settings: Settings, carteles: list[dict], ahora: datetime) -> Settings:
    """data/trabajo/ nueva: su base (con los carteles de la cola) y su carpeta de documentos. Lo de antes se borra:
    lo que vale ya está en el servidor."""
    carpeta = settings.database_path.parent / "trabajo"
    shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(parents=True)
    trabajo = Settings({**settings.raw, "DATABASE_PATH": str(carpeta / "trabajo.db"),
                        "DOCUMENTS_DIR": str(carpeta / "documentos")}, settings.env_file_loaded)
    apply_migrations(trabajo.database_path)
    momento = ahora.isoformat(timespec="seconds")
    with closing(connect(trabajo.database_path)) as conn, conn:
        conn.executemany(
            "INSERT INTO tenders (nro_sicop, descripcion, fecha_cierre_recepcion, content_hash, first_seen, last_seen)"
            " VALUES (?, ?, ?, 'enrich-remoto', ?, ?)",
            [(c["nro_sicop"], c.get("descripcion"), c.get("cierre"), momento, momento) for c in carteles])
    return trabajo


def paquete(conn: sqlite3.Connection, trabajo: Settings, c: Consulta, es_reintento: bool) -> list:
    """Las partes del envío de una consulta: «consulta» (JSON) y un «archivo» por documento que se bajó."""
    consulta = {"nro_sicop": c.nro_sicop, "resultado": c.resultado, "motivo": c.motivo, "iniciada_en": c.iniciada_en,
                "duracion_s": c.duracion_s, "grabacion": c.grabacion, "es_reintento": es_reintento, "ficha": None,
                "documentos": {}}
    archivos = []
    if c.guardado is not None:
        (consulta["ficha"],) = conn.execute("SELECT copia_fiel FROM tender_details WHERE id = ?",
                                            (c.guardado.detalle_id,)).fetchone()
        for server, estado, motivo, ruta in conn.execute(
                "SELECT server_file, estado, motivo, ruta_local FROM tender_documents WHERE nro_sicop = ? AND"
                " detalle_id = ? ORDER BY id", (c.nro_sicop, c.guardado.detalle_id)):
            if estado == "guardado" and ruta:
                archivos.append(("archivo", server, (trabajo.documents_dir / ruta).read_bytes(),
                                 "application/octet-stream"))
            else:
                consulta["documentos"][server] = {"estado": estado, "motivo": motivo}
    return [("consulta", "consulta.json", json.dumps(consulta, ensure_ascii=False).encode(), "application/json"),
            *archivos]


# --- La corrida -----------------------------------------------------------------------------------------------------

@dataclass
class CorridaRemota:
    estado: str                                  # ok · con_fallos · detenida · sin_cola
    corrida_id: int | None = None
    en_cola: int = 0
    consultas: list[Consulta] = field(default_factory=list)
    respuestas: list[dict] = field(default_factory=list)   # lo que dijo el servidor de cada cartel
    reintentada: Consulta | None = None
    grabaciones_borradas: int = 0
    error: str | None = None                     # si se detuvo porque el servidor no respondió o rechazó algo


def correr_remoto(settings: Settings, transporte: Transporte, *, maximo: int | None = None,
                  reloj: Callable[[], datetime] = en._ahora, dormir: Callable[[float], None] = time.sleep,
                  avisar: Callable[[str], None] = lambda _: None, **opciones) -> CorridaRemota:
    """Una corrida de enrich remoto. Lanza app.bloqueo.CicloOcupado si ya hay otra corrida en esta PC y
    ServidorError si el servidor no abre la corrida (no se consultó nada)."""
    inicio = reloj()
    with bloqueo(settings.database_path.parent / "enrich-run.lock", f"{inicio:%Y-%m-%d %H:%M:%S} · enrich remoto"):
        abierta = _llamar_json(transporte, f"{API}/corridas", {}, dormir, avisar)
        corrida = CorridaRemota("ok", abierta["corrida"], abierta.get("en_cola", 0))
        corrida.grabaciones_borradas = en.limpiar_grabaciones(None, settings, inicio.date(),
                                                              set(abierta.get("grabaciones_conservar") or []))
        carteles = abierta.get("carteles") or []
        if maximo is not None:
            carteles = carteles[:maximo]
        avisar(f"Corrida #{corrida.corrida_id} en el servidor · en cola {corrida.en_cola} · se consultan hoy "
               f"{len(carteles)}.")
        if not carteles:
            # El servidor ya la cerró como «sin_cola» si no tenía nada; si solo fue --max 0, se cierra aquí.
            corrida.estado = "sin_cola"
            if abierta.get("carteles"):
                _cerrar(transporte, corrida, "ok", None, dormir, avisar)
            return corrida
        trabajo = preparar_trabajo(settings, carteles, inicio)
        try:
            with closing(connect(trabajo.database_path)) as conn:
                for i, cartel in enumerate(carteles):
                    if i:
                        avisar(f"Pausa de {settings.enrich_delay_seconds} s antes del siguiente cartel…")
                        dormir(settings.enrich_delay_seconds)
                    nro, ya = cartel["nro_sicop"], frozenset(cartel.get("documentos_guardados") or [])
                    avisar(f"[{i + 1}/{len(carteles)}] {nro} · {en.ETIQUETAS.get(cartel.get('encaje'), '')} · "
                           f"{cartel.get('motivo', '')}")
                    c = consultar_uno(conn, trabajo, nro, documentos=True, dormir=dormir, reloj=reloj, avisar=avisar,
                                      ya_guardados=ya, **opciones)
                    _mandar(transporte, conn, trabajo, corrida, c, False, dormir, avisar)
                    if c.resultado == "control" and corrida.reintentada is None:
                        corrida.reintentada = c
                        minutos = settings.enrich_retry_wait_minutes
                        avisar(f"SICOP mostró un CAPTCHA o bloqueo ({c.motivo}). Espero {minutos} min con el navegador"
                               " cerrado y reintento una vez…")
                        dormir(minutos * 60)
                        c = consultar_uno(conn, trabajo, nro, documentos=True, dormir=dormir, reloj=reloj,
                                          avisar=avisar, ya_guardados=ya, **opciones)
                        _mandar(transporte, conn, trabajo, corrida, c, True, dormir, avisar)
                    corrida.consultas.append(c)
                    if c.resultado == "control":
                        corrida.estado = "detenida"
                        break
        except ServidorError as exc:
            corrida.estado, corrida.error = "detenida", str(exc)
            avisar(f"Se detiene: {exc}. Lo ya enviado quedó guardado en el servidor.")
            try:
                _cerrar(transporte, corrida, "detenida", f"la PC no pudo seguir: {exc}", dormir, avisar)
            except ServidorError:
                pass  # al abrir la siguiente corrida, el servidor la cierra como detenida
            return corrida
        fallos = sum(c.resultado in ("fallo", "control") for c in corrida.consultas)
        if corrida.estado != "detenida":
            corrida.estado = "con_fallos" if fallos else "ok"
        motivo = next((c.motivo for c in corrida.consultas if c.resultado == "control"), None)
        _cerrar(transporte, corrida, corrida.estado, motivo, dormir, avisar)
    return corrida


def _mandar(transporte, conn, trabajo, corrida: CorridaRemota, c: Consulta, es_reintento: bool, dormir, avisar):
    cuerpo, tipo = multipart(paquete(conn, trabajo, c, es_reintento))
    respuesta = _llamar(transporte, f"{API}/corridas/{corrida.corrida_id}/consultas", cuerpo, tipo, dormir, avisar)
    corrida.respuestas.append(respuesta)
    guardados = sum(d.get("estado") == "guardado" for d in respuesta.get("documentos") or [])
    avisar(f"  Enviado al servidor: {respuesta.get('resultado')} · {guardados} documento(s) guardado(s).")


def _cerrar(transporte, corrida: CorridaRemota, estado: str, motivo: str | None, dormir, avisar) -> None:
    _llamar_json(transporte, f"{API}/corridas/{corrida.corrida_id}/cierre", {"estado": estado, "motivo": motivo},
                 dormir, avisar)
