"""Enriquecimiento automático (lección 4, entrega 4A): python -m app.cli enrich run.

La tarea programada de Windows lo corre a las 10:00, lunes a viernes, CON la ventana visible (deploy/windows/README.md).
Mientras el proyecto es solo local, guarda directo en la base local; la dirección con token para enviar al servidor se
hace al desplegar (decisión de Ivania, 2026-10-27).

* Desactivado por defecto (ENRICH_ENABLED=false). Un solo enrich run a la vez (bloqueo del sistema operativo).
* Cola: los carteles del panel (encaje alta, media o baja en la evaluación vigente) con plazo abierto, y que nunca
  se enriquecieron, o que los datos abiertos vieron después de la última ficha, o que cierran en NOTIFY_CLOSING_DAYS
  días o menos. Sin los ya consultados hoy; hasta ENRICH_MAX_PER_DAY por día. Orden: Alta → Media → Baja y, dentro
  de cada uno, el que cierra antes (DECISION_OBTENCION.md §9, Oscar, 2026-10-27).
* Cada cartel con su ficha y sus documentos (lecciones 2 y 3), con pausa. Un FALLO no detiene la cola. Ante un
  CAPTCHA o bloqueo se espera ENRICH_RETRY_WAIT_MINUTES (15) con el navegador cerrado y se reintenta UNA vez (el
  CAPTCHA nunca se resuelve); si vuelve a salir, se detiene todo y se manda una alerta inmediata.
* Borrado al cierre: pasado el cierre de un cartel se borran su ficha, sus documentos y su texto, menos los marcados
  «Interesa» u «Ofertada» o con seguimiento. Cada borrado queda anotado en enrich_retiros (migración 0021).
* Bitácora (enrich_runs, enrich_consultas) y un resumen al terminar, con los días hábiles sin corrida.
* Videos y capturas: se borran después de RECORDINGS_KEEP_DAYS días, menos los de una consulta con FALLO que
  todavía nadie marcó revisada (panel › Bitácora de consultas).
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
from app.matching.evaluar import evaluar_base
from app.matching.reglas import cargar_reglas
from app.panel import version_vigente
from app.sources.sicop_tender_detail import Consulta, consultar_uno, registrar_consulta, revisar_base

DIA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUMERO = re.compile(r"^\d+$")
PRIORIDAD = {"alta": 0, "media": 1, "baja": 2}  # los encajes del panel, en el orden en que se consultan
ETIQUETAS = {"alta": "Alta", "media": "Media", "baja": "Baja"}
CONSERVAR = ("interesa", "ofertada")  # una revisión así en algún momento: no se borra al cierre
NOMBRES = {"nueva": "ficha nueva", "sin_cambios": "sin cambios", "fallo": "FALLO", "control": "CAPTCHA o bloqueo"}


@dataclass(frozen=True)
class EnCola:
    nro_sicop: str
    descripcion: str
    cierre: str
    motivo: str
    encaje: str = "alta"


@dataclass(frozen=True)
class Retiro:
    nro_sicop: str
    cierre: str
    hasta_detalle_id: int | None   # None: solo queda la carpeta (un borrado anterior no pudo con ella)
    fichas: int = 0
    documentos: int = 0
    paginas: int = 0
    bytes: int = 0


@dataclass
class Corrida:
    estado: str                       # desactivado · sin_cola · ok · con_fallos · detenida
    run_id: int | None = None
    en_cola: int = 0
    consultas: list[Consulta] = field(default_factory=list)
    grabaciones_borradas: int = 0
    retiros: list[Retiro] = field(default_factory=list)
    reintentada: Consulta | None = None  # la consulta con CAPTCHA o bloqueo que se repitió (una por corrida)
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
    """Todos los carteles que hoy tocaría enriquecer, Alta → Media → Baja y por cierre (sin aplicar el máximo)."""
    version = version_vigente(conn)
    if version is None:
        return []
    hoy = consultados_hoy(conn, ahora.date())
    filas = conn.execute(
        "SELECT t.nro_sicop, t.descripcion, t.fecha_cierre_recepcion, t.last_seen, d.cierre_recepcion,"
        "       d.consultado_en, a.rango"
        " FROM tenders t"
        " JOIN (SELECT nro_sicop, min(CASE encaje WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END) AS rango"
        "       FROM opportunity_assessments WHERE rules_version = ? AND encaje IN ('alta', 'media', 'baja')"
        "       GROUP BY nro_sicop) a ON a.nro_sicop = t.nro_sicop"
        " LEFT JOIN (SELECT nro_sicop, max(id) AS id FROM tender_details GROUP BY nro_sicop) u"
        "        ON u.nro_sicop = t.nro_sicop"
        " LEFT JOIN tender_details d ON d.id = u.id", (version,)).fetchall()
    pronto = timedelta(days=settings.notify_closing_days)
    lista = []
    encaje_de = {rango: encaje for encaje, rango in PRIORIDAD.items()}
    for nro, descripcion, cierre_datos, visto, cierre_ficha, consultado, rango in filas:
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
        lista.append(EnCola(nro, descripcion or "", cierre_iso, motivo, encaje_de[rango]))
    return sorted(lista, key=lambda e: (PRIORIDAD[e.encaje], _fecha(e.cierre)))


def cupo_de_hoy(conn: sqlite3.Connection, settings: Settings, ahora: datetime, maximo: int | None = None) -> int:
    restante = max(0, settings.enrich_max_per_day - len(consultados_hoy(conn, ahora.date())))
    return restante if maximo is None else min(restante, maximo)


def limpiar_grabaciones(conn: sqlite3.Connection, settings: Settings, hoy: date) -> int:
    """Borra las grabaciones de más de RECORDINGS_KEEP_DAYS días, menos las de una consulta con FALLO o CAPTCHA que
    nadie marcó revisada en el panel (migración 0022).
    Solo toca carpetas de día (AAAA-MM-DD) dentro de RECORDINGS_DIR. Devuelve cuántas carpetas de cartel borró."""
    raiz = settings.recordings_dir
    if not raiz.is_dir():
        return 0
    conservar = {"/".join(g.split("/")[:2]) for (g,) in conn.execute(
        "SELECT grabacion FROM enrich_consultas c WHERE resultado IN ('fallo', 'control') AND grabacion IS NOT NULL"
        "   AND NOT EXISTS (SELECT 1 FROM enrich_revisiones r WHERE r.consulta_id = c.id)")}
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


def _cierre_mas_tardio(*fechas: str | None) -> datetime | None:
    conocidas = [f for f in (_fecha(x) for x in fechas) if f is not None]
    return max(conocidas) if conocidas else None


def por_retirar(conn: sqlite3.Connection, settings: Settings, ahora: datetime) -> list[Retiro]:
    """Carteles cuya información de SICOP se borra al correr: el cierre más tardío conocido (la última ficha o los
    datos abiertos, por si se prorrogó) ya pasó, y nadie los marcó «Interesa» u «Ofertada» ni les dio seguimiento.
    También las carpetas que un borrado anterior no pudo quitar (hasta_detalle_id None)."""
    marcas = ", ".join("?" for _ in CONSERVAR)
    filas = conn.execute(
        "SELECT u.nro_sicop, u.hasta, d.cierre_recepcion, t.fecha_cierre_recepcion,"
        "       (SELECT count(*) FROM tender_details x WHERE x.nro_sicop = u.nro_sicop),"
        "       (SELECT count(*) FROM tender_documents x WHERE x.nro_sicop = u.nro_sicop),"
        "       (SELECT count(*) FROM tender_document_text x JOIN tender_documents y ON y.id = x.documento_id"
        "         WHERE y.nro_sicop = u.nro_sicop),"
        "       (SELECT coalesce(sum(tamano_bytes), 0) FROM tender_documents x"
        "         WHERE x.nro_sicop = u.nro_sicop AND x.estado = 'guardado')"
        " FROM (SELECT nro_sicop, max(id) AS hasta FROM tender_details GROUP BY nro_sicop) u"
        " JOIN tender_details d ON d.id = u.hasta"
        " JOIN tenders t ON t.nro_sicop = u.nro_sicop"
        f" WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.nro_sicop = u.nro_sicop AND r.decision IN ({marcas}))"
        "   AND NOT EXISTS (SELECT 1 FROM seguimientos s WHERE s.nro_sicop = u.nro_sicop)"
        " ORDER BY u.nro_sicop", CONSERVAR).fetchall()
    lista = []
    for nro, hasta, cierre_ficha, cierre_datos, fichas, documentos, paginas, tamano in filas:
        cierre = _cierre_mas_tardio(cierre_ficha, cierre_datos)
        if cierre is not None and cierre <= ahora:
            lista.append(Retiro(nro, cierre.isoformat(timespec="seconds"), hasta, fichas, documentos, paginas, tamano))
    raiz = settings.documents_dir
    if raiz.is_dir():
        for carpeta in sorted(raiz.iterdir()):
            if not carpeta.is_dir() or not NUMERO.match(carpeta.name):
                continue
            retiro = conn.execute("SELECT cierre FROM enrich_retiros WHERE nro_sicop = ? ORDER BY id DESC LIMIT 1",
                                  (carpeta.name,)).fetchone()
            guardados = conn.execute("SELECT 1 FROM tender_documents WHERE nro_sicop = ? AND estado = 'guardado'"
                                     " LIMIT 1", (carpeta.name,)).fetchone()
            if retiro and not guardados and all(r.nro_sicop != carpeta.name for r in lista):
                lista.append(Retiro(carpeta.name, retiro[0], None))
    return lista


def _borrar_carpeta(settings: Settings, nro: str) -> None:
    raiz = settings.documents_dir.resolve()
    carpeta = (raiz / nro).resolve()
    if NUMERO.match(nro) and carpeta.parent == raiz and carpeta.is_dir():
        shutil.rmtree(carpeta)


def retirar(conn: sqlite3.Connection, settings: Settings, ahora: datetime, run_id: int | None) -> list[Retiro]:
    """Borra la información de SICOP de los carteles de por_retirar (ficha, documentos, texto y su carpeta). Primero
    anota el retiro: sin él, los triggers de la migración 0021 no dejan borrar. No toca tenders, revisiones,
    seguimientos ni grabaciones. Si una carpeta no se puede borrar, la próxima corrida lo vuelve a intentar."""
    hechos = []
    for r in por_retirar(conn, settings, ahora):
        if r.hasta_detalle_id is not None:
            with transaccion(conn):
                conn.execute(
                    "INSERT INTO enrich_retiros (nro_sicop, retirado_en, run_id, cierre, hasta_detalle_id, fichas,"
                    " documentos, paginas, bytes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (r.nro_sicop, ahora.isoformat(timespec="seconds"), run_id, r.cierre, r.hasta_detalle_id,
                     r.fichas, r.documentos, r.paginas, r.bytes))
                conn.execute("UPDATE enrich_consultas SET detalle_id = NULL WHERE nro_sicop = ? AND detalle_id <= ?",
                             (r.nro_sicop, r.hasta_detalle_id))
                conn.execute("DELETE FROM tender_document_text WHERE documento_id IN (SELECT id FROM tender_documents"
                             " WHERE nro_sicop = ? AND detalle_id <= ?)", (r.nro_sicop, r.hasta_detalle_id))
                conn.execute("DELETE FROM tender_documents WHERE nro_sicop = ? AND detalle_id <= ?",
                             (r.nro_sicop, r.hasta_detalle_id))
                conn.execute("DELETE FROM tender_details WHERE nro_sicop = ? AND id <= ?",
                             (r.nro_sicop, r.hasta_detalle_id))
        try:
            _borrar_carpeta(settings, r.nro_sicop)
        except OSError:
            pass  # queda la carpeta sin filas en la base: por_retirar la vuelve a encontrar
        if r.hasta_detalle_id is not None or not (settings.documents_dir / r.nro_sicop).exists():
            hechos.append(r)
    return hechos


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

def texto_alerta(settings: Settings, c: Consulta, reintentada: Consulta | None = None) -> tuple[str, str]:
    minutos = settings.enrich_retry_wait_minutes
    if reintentada is None:
        reintento = "No hubo reintento."
    elif reintentada.nro_sicop == c.nro_sicop:
        reintento = (f"Ya se reintentó UNA vez, después de {minutos} min con el navegador cerrado, y SICOP volvió a "
                     "mostrarlo.")
    else:
        reintento = (f"El único reintento de la corrida ya se usó con {reintentada.nro_sicop}; este segundo "
                     "CAPTCHA o bloqueo detiene todo.")
    cuerpo = "\n".join([
        "SICOP CONNECT · el enriquecimiento se DETUVO: SICOP mostró un CAPTCHA o un bloqueo.",
        "",
        f"Cartel que se estaba consultando: {c.nro_sicop} ({c.iniciada_en[:16].replace('T', ' a las ')}).",
        f"Motivo: {c.motivo}",
        f"Video y capturas: {settings.recordings_dir / (c.grabacion or '')}*",
        reintento,
        "",
        "El CAPTCHA nunca se resuelve ni se intenta evitar (docs/DECISION_OBTENCION.md §9). Qué hacer:",
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
    if corrida.reintentada is not None:
        r = corrida.reintentada
        final = next((c for c in corrida.consultas if c.nro_sicop == r.nro_sicop), None)
        lineas += [f"CAPTCHA o bloqueo con {r.nro_sicop} ({r.motivo}). Se esperó "
                   f"{settings.enrich_retry_wait_minutes} min y se reintentó una vez: "
                   f"{NOMBRES.get(final.resultado, final.resultado) if final else 'sin resultado'}.",
                   f"    Video y capturas: {settings.recordings_dir / (r.grabacion or '')}*", ""]
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
    retirados = [r for r in corrida.retiros if r.hasta_detalle_id is not None]
    if retirados:
        megas = sum(r.bytes for r in retirados) / 1_000_000
        lineas += ["", f"Borrado al cierre: {len(retirados)} cartel(es) ya cerrado(s), sin «Interesa» ni seguimiento "
                       f"({sum(r.documentos for r in retirados)} documentos, {megas:.1f} MB):"]
        lineas += [f"- {r.nro_sicop} · cerró {_fecha(r.cierre):%d/%m/%Y %H:%M}" for r in retirados]
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

def reevaluar(conn: sqlite3.Connection, nros: list[str], avisar: Callable[[str], None] = lambda _: None) -> int:
    """Vuelve a evaluar con las reglas los carteles consultados o borrados al cierre (entrega 4C): así el panel
    muestra enseguida las señales del PDF, o deja de mostrarlas si el texto se borró. Si falla, la corrida no se
    pierde: lo deja dicho y el run-cycle del día siguiente evalúa todo. Devuelve cuántos reevaluó."""
    nros = list(dict.fromkeys(nros))
    if not nros:
        return 0
    try:
        reglas = cargar_reglas()
        for nro in nros:
            evaluar_base(conn, reglas, nro_sicop=nro)
    except Exception as exc:  # noqa: BLE001 — la corrida ya quedó registrada; evaluate se puede repetir
        avisar(f"No se pudieron reevaluar los carteles consultados ({exc}). Ejecuta python -m app.cli evaluate.")
        return 0
    avisar(f"Reevaluados con el texto de los PDF: {len(nros)} cartel(es).")
    return len(nros)


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
        corrida.retiros = retirar(conn, settings, inicio, run_id)
        borrados = [r.nro_sicop for r in corrida.retiros if r.hasta_detalle_id is not None]
        if borrados:
            avisar(f"Borrado al cierre: {len(borrados)} cartel(es) ({', '.join(borrados)}).")
        lista = cola(conn, settings, inicio)
        hoy = lista[:cupo_de_hoy(conn, settings, inicio, maximo)]
        corrida.en_cola = len(lista)
        avisar(f"En cola: {len(lista)} · se consultan hoy: {len(hoy)} (máximo {settings.enrich_max_per_day} por día).")
        for i, item in enumerate(hoy):
            if i:
                avisar(f"Pausa de {settings.enrich_delay_seconds} s antes del siguiente cartel…")
                dormir(settings.enrich_delay_seconds)
            avisar(f"[{i + 1}/{len(hoy)}] {item.nro_sicop} · {ETIQUETAS[item.encaje]} · {item.motivo}")
            c = consultar_uno(conn, settings, item.nro_sicop, documentos=True, dormir=dormir, reloj=reloj,
                              avisar=avisar, **opciones)
            consulta_id = registrar_consulta(conn, c, run_id)
            if c.resultado == "control" and corrida.reintentada is None:
                # Decisión de Oscar (§9): una sola vez por corrida, con el navegador cerrado; nunca se resuelve.
                corrida.reintentada = c
                minutos = settings.enrich_retry_wait_minutes
                avisar(f"SICOP mostró un CAPTCHA o bloqueo ({c.motivo}). Espero {minutos} min con el navegador "
                       "cerrado y reintento una vez…")
                dormir(minutos * 60)
                c = consultar_uno(conn, settings, item.nro_sicop, documentos=True, dormir=dormir, reloj=reloj,
                                  avisar=avisar, **opciones)
                consulta_id = registrar_consulta(conn, c, run_id, es_reintento=True)
            corrida.consultas.append(c)
            if c.resultado == "control":
                corrida.estado = "detenida"

                def marcar(estado, consulta_id=consulta_id):
                    with transaccion(conn):
                        conn.execute("UPDATE enrich_consultas SET aviso_estado = ? WHERE id = ?", (estado, consulta_id))
                asunto, cuerpo = texto_alerta(settings, c, corrida.reintentada)
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
        reevaluar(conn, [c.nro_sicop for c in corrida.consultas if c.resultado in ("nueva", "sin_cambios")] + borrados,
                  avisar)

        def marcar_resumen(estado):
            with transaccion(conn):
                conn.execute("UPDATE enrich_runs SET resumen_estado = ?, resumen_en = ? WHERE id = ?",
                             (estado, reloj().isoformat(timespec="seconds"), run_id))
        asunto, cuerpo = texto_resumen(settings, corrida, inicio, dias_habiles_sin_corrida(conn, inicio.date(), run_id))
        corrida.resumen = _avisar(settings, asunto, cuerpo, f"resumen-enriquecimiento-{run_id}", proveedor,
                                  marcar_resumen)
    return corrida
