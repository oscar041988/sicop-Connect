"""Enriquecimiento automático (lección 4, entrega 4A): python -m app.cli enrich run.

La tarea programada de Windows lo corre a las 10:00, lunes a viernes, CON la ventana visible (deploy/windows/README.md).
Mientras el proyecto es solo local, guarda directo en la base local; la dirección con token para enviar al servidor se
hace al desplegar (decisión de Ivania, 2026-10-27).

* Desactivado por defecto (ENRICH_ENABLED=false). Un solo enrich run a la vez (bloqueo del sistema operativo).
* Cola: carteles con encaje alta o media en la evaluación vigente, plazo abierto, y que nunca se enriquecieron, o
  que los datos abiertos vieron después de la última ficha, o que cierran en NOTIFY_CLOSING_DAYS días o menos. Sin
  los ya consultados hoy; hasta ENRICH_MAX_PER_DAY por día. Primero los que cierran antes.
* Cada cartel con su ficha y sus documentos (lecciones 2 y 3), con pausa. Un FALLO no detiene la cola; un CAPTCHA o
  bloqueo detiene todo y manda una alerta inmediata.
* Bitácora (enrich_runs, enrich_consultas) y un resumen al terminar, con los días hábiles sin corrida.
* Videos y capturas: se borran después de RECORDINGS_KEEP_DAYS días, menos los de una consulta con FALLO.
* Alerta y resumen van a OBTAIN_ALERT_TO con las mismas reglas que los avisos: en dry-run, solo vista previa.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Callable

from app.bloqueo import bloqueo
from app.config import Settings
from app.database import connect, transaccion
from app.importers.comun import HORA_CR
from app.panel import version_vigente
from app.sources.sicop_tender_detail import Consulta, consultar_uno, registrar_consulta, revisar_base

DIA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NOMBRES = {"nueva": "ficha nueva", "sin_cambios": "sin cambios", "fallo": "FALLO", "control": "CAPTCHA o bloqueo"}


@dataclass(frozen=True)
class EnCola:
    nro_sicop: str
    descripcion: str
    cierre: str
    motivo: str


@dataclass
class Corrida:
    estado: str                       # desactivado · sin_cola · ok · con_fallos · detenida
    run_id: int | None = None
    en_cola: int = 0
    consultas: list[Consulta] = field(default_factory=list)
    grabaciones_borradas: int = 0
    resumen: str = ""                 # dónde quedó la vista previa o a quién se envió
    alerta: str = ""


def _ahora() -> datetime:
    return datetime.now(HORA_CR)


def _fecha(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        fecha = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=HORA_CR)


def consultados_hoy(conn: sqlite3.Connection, hoy: date) -> set[str]:
    return {n for (n,) in conn.execute("SELECT DISTINCT nro_sicop FROM enrich_consultas WHERE"
                                       " substr(iniciada_en, 1, 10) = ?", (hoy.isoformat(),))}


def cola(conn: sqlite3.Connection, settings: Settings, ahora: datetime) -> list[EnCola]:
    """Todos los carteles que hoy tocaría enriquecer, en orden de cierre (sin aplicar el máximo del día)."""
    version = version_vigente(conn)
    if version is None:
        return []
    hoy = consultados_hoy(conn, ahora.date())
    filas = conn.execute(
        "SELECT t.nro_sicop, t.descripcion, t.fecha_cierre_recepcion, t.last_seen, d.cierre_recepcion,"
        "       d.consultado_en"
        " FROM tenders t"
        " JOIN (SELECT DISTINCT nro_sicop FROM opportunity_assessments"
        "       WHERE rules_version = ? AND encaje IN ('alta', 'media')) a ON a.nro_sicop = t.nro_sicop"
        " LEFT JOIN (SELECT nro_sicop, max(id) AS id FROM tender_details GROUP BY nro_sicop) u"
        "        ON u.nro_sicop = t.nro_sicop"
        " LEFT JOIN tender_details d ON d.id = u.id", (version,)).fetchall()
    pronto = timedelta(days=settings.notify_closing_days)
    lista = []
    for nro, descripcion, cierre_datos, visto, cierre_ficha, consultado in filas:
        if nro in hoy:
            continue
        cierre_iso = cierre_ficha or cierre_datos  # la ficha es más reciente que los datos abiertos
        cierre = _fecha(cierre_iso)
        if cierre is None or cierre <= ahora:
            continue
        if consultado is None:
            motivo = "nunca enriquecido"
        elif (_fecha(visto) or ahora) > (_fecha(consultado) or ahora):
            motivo = "los datos abiertos lo vieron después de la última ficha"
        elif cierre - ahora <= pronto:
            motivo = f"cierra en {settings.notify_closing_days} días o menos"
        else:
            continue
        lista.append(EnCola(nro, descripcion or "", cierre_iso, motivo))
    return sorted(lista, key=lambda e: _fecha(e.cierre))


def cupo_de_hoy(conn: sqlite3.Connection, settings: Settings, ahora: datetime, maximo: int | None = None) -> int:
    restante = max(0, settings.enrich_max_per_day - len(consultados_hoy(conn, ahora.date())))
    return restante if maximo is None else min(restante, maximo)


def limpiar_grabaciones(conn: sqlite3.Connection, settings: Settings, hoy: date) -> int:
    """Borra las grabaciones de más de RECORDINGS_KEEP_DAYS días, menos las de una consulta con FALLO o CAPTCHA.
    Solo toca carpetas de día (AAAA-MM-DD) dentro de RECORDINGS_DIR. Devuelve cuántas carpetas de cartel borró."""
    raiz = settings.recordings_dir
    if not raiz.is_dir():
        return 0
    conservar = {"/".join(g.split("/")[:2]) for (g,) in conn.execute(
        "SELECT grabacion FROM enrich_consultas WHERE resultado IN ('fallo', 'control') AND grabacion IS NOT NULL")}
    limite = hoy - timedelta(days=settings.recordings_keep_days)
    borradas = 0
    for dia in raiz.iterdir():
        if not dia.is_dir() or not DIA.match(dia.name) or date.fromisoformat(dia.name) >= limite:
            continue
        for cartel in dia.iterdir():
            if cartel.is_dir() and f"{dia.name}/{cartel.name}" not in conservar:
                shutil.rmtree(cartel)
                borradas += 1
        if not any(dia.iterdir()):
            dia.rmdir()
    return borradas


def dias_habiles_sin_corrida(conn: sqlite3.Connection, hoy: date, run_id: int) -> list[date]:
    """Días hábiles (lunes a viernes) entre la corrida anterior y hoy en que no hubo corrida (equipo apagado…)."""
    fila = conn.execute("SELECT max(substr(iniciada_en, 1, 10)) FROM enrich_runs WHERE id < ? AND"
                        " substr(iniciada_en, 1, 10) < ?", (run_id, hoy.isoformat())).fetchone()
    if not fila or not fila[0]:
        return []
    dia, faltan = date.fromisoformat(fila[0]) + timedelta(days=1), []
    while dia < hoy:
        if dia.weekday() < 5:
            faltan.append(dia)
        dia += timedelta(days=1)
    return faltan


# --- Alerta y resumen -----------------------------------------------------------------------------------------

def texto_alerta(settings: Settings, c: Consulta) -> tuple[str, str]:
    cuerpo = "\n".join([
        "SICOP CONNECT · el enriquecimiento se DETUVO: SICOP mostró un CAPTCHA o un bloqueo.",
        "",
        f"Cartel que se estaba consultando: {c.nro_sicop} ({c.iniciada_en[:16].replace('T', ' a las ')}).",
        f"Motivo: {c.motivo}",
        f"Video y capturas: {settings.recordings_dir / (c.grabacion or '')}*",
        "",
        "No se reintenta ni se intenta evitar (docs/DECISION_OBTENCION.md §8, regla 2). Qué hacer:",
        "1. Mirar el video o la captura para ver qué mostró SICOP.",
        "2. No volver a correr el enriquecimiento hoy.",
        "3. Avisar a Oscar. Para pausar la tarea: ENRICH_ENABLED=false en .env (docs/OPERACION.md).",
        "",
        "No respondas este correo. Detalle: python -m app.cli enrich status.",
    ])
    return f"SICOP CONNECT · enriquecimiento DETENIDO por CAPTCHA o bloqueo ({c.nro_sicop})", cuerpo


def texto_resumen(settings: Settings, corrida: Corrida, ahora: datetime, faltaron: list[date]) -> tuple[str, str]:
    fallos = [c for c in corrida.consultas if c.resultado in ("fallo", "control")]
    titulo = f"{len(corrida.consultas)} consultados, {len(fallos)} FALLO" if corrida.consultas else "sin consultas"
    lineas = [f"SICOP CONNECT · enriquecimiento del {ahora:%d/%m/%Y}: {titulo}.", ""]
    if faltaron:
        lineas += [f"ATENCIÓN: no hubo corrida {len(faltaron)} día(s) hábil(es) antes de hoy "
                   f"({', '.join(f'{d:%d/%m}' for d in faltaron)}). ¿El equipo de consulta estuvo apagado o con la "
                   "sesión cerrada? La cola esperó: no se perdió nada.", ""]
    if corrida.estado == "sin_cola":
        lineas.append("No había carteles en la cola (o ya se llegó al máximo del día).")
    for c in corrida.consultas:
        documentos = c.documentos or []
        guardados = sum(d.estado == "guardado" for d in documentos)
        con_fallo = sum(d.estado == "fallo" for d in documentos)
        linea = f"- {c.nro_sicop} · {NOMBRES.get(c.resultado, c.resultado)}"
        if c.campos:
            cierre = _fecha(c.campos.get("cierre_recepcion"))
            linea += (f" · {c.campos.get('estado_concurso') or ''} · cierre "
                      f"{f'{cierre:%d/%m/%Y %H:%M}' if cierre else 'sin dato'}")
        if documentos:
            linea += f" · documentos: {guardados} guardados" + (f", {con_fallo} con FALLO" if con_fallo else "")
        lineas.append(linea)
        if c.resultado in ("fallo", "control"):
            lineas.append(f"    {c.motivo}")
            lineas.append(f"    Video y capturas: {settings.recordings_dir / (c.grabacion or '')}*")
    if corrida.grabaciones_borradas:
        lineas += ["", f"Se borraron {corrida.grabaciones_borradas} grabaciones de más de "
                       f"{settings.recordings_keep_days} días."]
    lineas += ["", "No respondas este correo. Detalle: python -m app.cli enrich status."]
    return f"SICOP CONNECT · enriquecimiento del {ahora:%d/%m}: {titulo}", "\n".join(lineas)


def _html(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _avisar(settings: Settings, asunto: str, cuerpo: str, nombre: str, proveedor: Callable | None,
            marcar: Callable[[str], None]) -> str:
    """Vista previa en EXPORTS_DIR, o envío real si se permite (mismas reglas que automatico._alertar)."""
    real = settings.notifications_enabled and not settings.notifications_dry_run and settings.obtain_alert_to
    if not real or proveedor is None:
        ruta = settings.exports_dir / f"{nombre}.txt"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(f"Para: {settings.obtain_alert_to or '(falta OBTAIN_ALERT_TO)'}\nAsunto: {asunto}\n\n"
                        f"{cuerpo}\n", encoding="utf-8")
        marcar("vista_previa")
        return f"vista previa en {ruta} (avisos en dry-run, no se envió)"
    marcar("incierta")  # antes de llamar a Gmail: si se cae, no se reenvía sola
    try:
        proveedor(settings).enviar(settings.obtain_alert_to, asunto, f"<pre>{_html(cuerpo)}</pre>", cuerpo)
    except Exception as exc:  # noqa: BLE001 — EnvioRechazado, EnvioIncierto u otro: se informa, no se reintenta
        rechazado = type(exc).__name__ == "EnvioRechazado"
        if rechazado:
            marcar("fallida")
        return (f"Gmail lo rechazó ({exc})" if rechazado else
                f"sin respuesta clara de Gmail ({type(exc).__name__}); revisar Gmail › Enviados")
    marcar("aceptada")
    return f"enviado a {settings.obtain_alert_to}"


# --- La corrida -------------------------------------------------------------------------------------------------

def correr(settings: Settings, *, maximo: int | None = None, reloj: Callable[[], datetime] = _ahora,
           dormir: Callable[[float], None] = time.sleep, avisar: Callable[[str], None] = lambda _: None,
           proveedor: Callable | None = None, **opciones) -> Corrida:
    """Una corrida de enrich run. Lanza app.bloqueo.CicloOcupado si ya hay otra, y ValueError si falta migrar."""
    if not settings.enrich_enabled:
        return Corrida("desactivado")
    inicio = reloj()
    with bloqueo(settings.database_path.parent / "enrich-run.lock", f"{inicio:%Y-%m-%d %H:%M:%S} · enrich run"), \
            closing(connect(settings.database_path)) as conn:
        revisar_base(conn, [], documentos=True)
        with transaccion(conn):
            run_id = conn.execute("INSERT INTO enrich_runs (iniciada_en, maximo) VALUES (?, ?)",
                                  (inicio.isoformat(timespec="seconds"), settings.enrich_max_per_day)).lastrowid
        corrida = Corrida("ok", run_id)
        corrida.grabaciones_borradas = limpiar_grabaciones(conn, settings, inicio.date())
        lista = cola(conn, settings, inicio)
        hoy = lista[:cupo_de_hoy(conn, settings, inicio, maximo)]
        corrida.en_cola = len(lista)
        avisar(f"En cola: {len(lista)} · se consultan hoy: {len(hoy)} (máximo {settings.enrich_max_per_day} por día).")
        for i, item in enumerate(hoy):
            if i:
                avisar(f"Pausa de {settings.enrich_delay_seconds} s antes del siguiente cartel…")
                dormir(settings.enrich_delay_seconds)
            avisar(f"[{i + 1}/{len(hoy)}] {item.nro_sicop} · {item.motivo}")
            c = consultar_uno(conn, settings, item.nro_sicop, documentos=True, dormir=dormir, reloj=reloj,
                              avisar=avisar, **opciones)
            consulta_id = registrar_consulta(conn, c, run_id)
            corrida.consultas.append(c)
            if c.resultado == "control":
                corrida.estado = "detenida"

                def marcar(estado, consulta_id=consulta_id):
                    with transaccion(conn):
                        conn.execute("UPDATE enrich_consultas SET aviso_estado = ? WHERE id = ?", (estado, consulta_id))
                asunto, cuerpo = texto_alerta(settings, c)
                corrida.alerta = _avisar(settings, asunto, cuerpo, f"alerta-enriquecimiento-{run_id}", proveedor,
                                         marcar)
                break
        fallos = sum(c.resultado in ("fallo", "control") for c in corrida.consultas)
        if corrida.estado != "detenida":
            corrida.estado = "sin_cola" if not hoy else ("con_fallos" if fallos else "ok")
        fin = reloj()
        with transaccion(conn):
            conn.execute("UPDATE enrich_runs SET terminada_en = ?, estado = ?, en_cola = ?, consultados = ?,"
                         " fallos = ?, motivo = ?, grabaciones_borradas = ? WHERE id = ?",
                         (fin.isoformat(timespec="seconds"), corrida.estado, corrida.en_cola, len(corrida.consultas),
                          fallos, next((c.motivo for c in corrida.consultas if c.resultado == "control"), None),
                          corrida.grabaciones_borradas, run_id))

        def marcar_resumen(estado):
            with transaccion(conn):
                conn.execute("UPDATE enrich_runs SET resumen_estado = ?, resumen_en = ? WHERE id = ?",
                             (estado, reloj().isoformat(timespec="seconds"), run_id))
        asunto, cuerpo = texto_resumen(settings, corrida, inicio, dias_habiles_sin_corrida(conn, inicio.date(), run_id))
        corrida.resumen = _avisar(settings, asunto, cuerpo, f"resumen-enriquecimiento-{run_id}", proveedor,
                                  marcar_resumen)
    return corrida
