"""Línea de comandos: python -m app.cli <comando>."""

from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Sequence

from app import __version__
from app.config import DEFAULTS, SENSITIVE_KEYS, Settings, load_settings
from app.database import MigrationError, apply_migrations, check_database, connect
from app.compras import Compra, detalle_compra
from app.importers.carteles import import_carteles
from app.importers import adjudicaciones, zip_pliegos
from app.importers.catalogo import import_catalogo
from app.importers.comun import HORA_CR, ORIGENES, ImportacionError, Resultado
from app.importers.instituciones import import_instituciones
from app.importers.lineas import import_lineas
from app.matching.evaluar import ENCAJES, ResultadoEvaluacion, evaluar_base
from app.matching.reglas import REGLAS_PATH, ReglasError, cargar_reglas
from app import avisos, calidad, ciclo, respaldo, resumen, usuarios
from app.usuarios import UsuarioInvalido, crear_usuario, validar_contrasena

MAX_RECHAZOS_VISIBLES = 20
EJEMPLOS_POR_ADVERTENCIA = 3
SEPARADORES = {";": "punto y coma", ",": "coma", "\t": "tabulador"}
IMPORTADORES = {
    "carteles": import_carteles,
    "lineas": import_lineas,
    "catalogo": import_catalogo,
    "instituciones": import_instituciones,
}
ESTADOS_CATALOGO = {
    "en_catalogo": "",
    "clasificacion_no_descargada": "SIN CATÁLOGO (clasificación no descargada)",
    "codigo_no_esta_en_catalogo": "SIN CATÁLOGO (el código no está en su clasificación)",
}
ETIQUETAS_ENCAJE = {"alta": "Alta", "media": "Media", "baja": "Baja", "sin_coincidencia": "Sin coincidencia"}
ETIQUETAS_PLAZO = {"abierto": "Abierto", "cierra_7_dias": "Cierra en 7 días o menos", "vencido": "Vencido",
                   "por_verificar": "Por verificar"}
ETIQUETAS_CALIDAD = {"completo": "Completo", "sin_lineas": "Sin líneas", "codigo_sin_catalogo": "Código sin catálogo",
                     "archivo_parcial": "Archivo parcial"}


def _describe(key: str, value: str) -> str:
    """Valor visible para variables normales; solo el estado para las sensibles."""
    if key in SENSITIVE_KEYS:
        return "configurado (oculto)" if value else "PENDIENTE"
    return value if value else "PENDIENTE"


def doctor(settings: Settings) -> int:
    print(f"SICOP CONNECT {__version__} - diagnóstico")
    origen = ".env + entorno del proceso" if settings.env_file_loaded else "entorno del proceso y valores por defecto (sin .env)"
    print(f"Origen de la configuración: {origen}")
    print()
    pendientes = []
    for key in DEFAULTS:
        value = settings.get(key)
        description = _describe(key, value)
        if not value:
            pendientes.append(key)
        print(f"  {key:<24} {description}")
    print()
    db = check_database(settings.database_path)
    print(f"Base de datos: {db['status']} - {db['detail']}")
    print(f"Avisos: {'habilitados' if settings.notifications_enabled else 'deshabilitados'}"
          f" (dry-run: {'sí' if settings.notifications_dry_run else 'no'})")
    def existe(path):
        return "PENDIENTE" if path is None else ("existe" if path.is_file() else "NO EXISTE")
    if settings.mail_provider == "gmail_api":
        print(f"Gmail: archivo del cliente {existe(settings.google_client_file)}"
              f" · token {existe(settings.google_token_file)} (el contenido nunca se muestra)")
    if settings.google_read_token_file is not None or settings.sicop_request_email:
        print(f"Gmail lectura: archivo del cliente {existe(settings.google_client_file)}"
              f" · token de lectura {existe(settings.google_read_token_file)} (el contenido nunca se muestra)")
    print(f"Programador: {'habilitado' if settings.scheduler_enabled else 'deshabilitado'}")
    print(f"Pendientes: {', '.join(pendientes) if pendientes else 'ninguno'}")
    return 0


def migrate(settings: Settings) -> int:
    print(f"Base de datos: {settings.get('DATABASE_PATH')}")
    try:
        aplicadas = apply_migrations(settings.database_path)
    except MigrationError as exc:
        print(f"Error de migración: {exc}", file=sys.stderr)
        return 1
    if aplicadas:
        print("Migraciones aplicadas:")
        for nombre in aplicadas:
            print(f"  {nombre}")
    else:
        print("La base ya está al día; no se aplicó nada.")
    return 0


def _imprimir_resultado(r: Resultado) -> None:
    separador = SEPARADORES.get(r.delimiter, repr(r.delimiter))
    print(f"Archivo: {r.archivo}")
    print(f"Hash SHA-256: {r.file_hash[:16]}…  ·  codificación {r.encoding}  ·  separador {separador}")
    for aviso in r.avisos_archivo:
        print(f"Aviso: {aviso}")
    if r.ya_importado is not None:
        print(f"Este archivo ya se importó (importación #{r.ya_importado}): 0 filas nuevas, no se cambió nada.")
        return
    print(f"Copia del original: {r.copia_original}")
    print(f"Filas leídas: {r.leidas}")
    print(f"Aceptadas: {r.aceptadas} (nuevas {r.nuevas} · actualizadas {r.actualizadas} · sin cambios {r.sin_cambios}"
          f" · huérfanas {r.huerfanas})")
    print(f"Rechazadas: {len(r.rechazos)}")
    for rechazo in r.rechazos[:MAX_RECHAZOS_VISIBLES]:
        print(f"  línea {rechazo.linea}: {rechazo.motivo}")
    if len(r.rechazos) > MAX_RECHAZOS_VISIBLES:
        print(f"  … y {len(r.rechazos) - MAX_RECHAZOS_VISIBLES} más")
    total_adv = sum(len(lineas) for lineas in r.advertencias.values())
    print(f"Advertencias: {total_adv} (las filas se aceptaron)")
    for tipo, lineas in r.advertencias.items():
        ejemplos = ", ".join(str(n) for n in lineas[:EJEMPLOS_POR_ADVERTENCIA])
        print(f"  {tipo}: {len(lineas)} (p. ej. líneas {ejemplos})")
    print(f"Importación #{r.import_id} registrada.")


def importar(settings: Settings, path: Path, report: str, origen: str) -> int:
    if not path.is_file():
        print(f"Error: no existe el archivo {path}", file=sys.stderr)
        return 1
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}). Ejecuta python -m app.cli migrate", file=sys.stderr)
        return 1
    try:
        with closing(connect(settings.database_path)) as conn:
            if report == "adjudicaciones":
                partes = adjudicaciones.import_zip(conn, path, origen, settings.raw_data_dir)
            else:
                partes = [(report, IMPORTADORES[report](conn, path, origen, settings.raw_data_dir))]
    except (ImportacionError, zip_pliegos.ZipInvalido) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for i, (parte, resultado) in enumerate(partes):
        if i:
            print()
        print(f"Reporte: {parte}  ·  origen de los datos: {origen}")
        _imprimir_resultado(resultado)
    return 0


def _imprimir_compra(c: Compra) -> None:
    print(f"Compra {c.nro_sicop} · procedimiento {c.nro_procedimiento}")
    print(f"  {c.descripcion}")
    comprador = c.institucion if c.institucion is not None else "SIN DATOS (cédula no está en instituciones)"
    print(f"Comprador: {comprador} · cédula {c.institution_cedula}")
    print(f"Publicación: {c.fecha_publicacion} · cierre de recepción: {c.fecha_cierre_recepcion or 'sin fecha'}")
    print(f"Líneas: {len(c.lineas)}")
    for l in c.lineas:
        nombre = l.nombre_catalogo or ESTADOS_CATALOGO[l.estado_catalogo]
        print(f"  {l.numero_linea:>3}. {l.codigo_identificacion}  {nombre}")
        print(f"       {l.cantidad} × {l.precio_unitario} = {l.estimado.valor} {l.estimado.moneda}")
    totales = " · ".join(f"{m.valor} {moneda}" for moneda, m in c.estimado_por_moneda.items())
    print(f"Estimación (cantidad × precio, por moneda; no es presupuesto ni adjudicación): {totales or '—'}")


def compra(settings: Settings, nro_sicop: str) -> int:
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}).", file=sys.stderr)
        return 1
    with closing(connect(settings.database_path)) as conn:
        resultado = detalle_compra(conn, nro_sicop)
    if resultado is None:
        print(f"No hay un cartel con Número SICOP {nro_sicop}.", file=sys.stderr)
        return 1
    _imprimir_compra(resultado)
    return 0


def _imprimir_evaluacion(r: ResultadoEvaluacion) -> None:
    print(f"Carteles evaluados: {r.carteles}")
    print(f"Filas: nuevas {r.nuevas} · actualizadas {r.actualizadas} · sin cambios {r.sin_cambios}"
          f" · ya no coinciden {r.retiradas}")
    print("Encaje por familia (" + " / ".join(ETIQUETAS_ENCAJE[e] for e in ENCAJES) + "):")
    for familia, cuentas in sorted(r.por_encaje.items()):
        print(f"  {familia:<24} " + " / ".join(str(cuentas.get(e, 0)) for e in ENCAJES))


def _imprimir_candidatos(conn, version: str, limite: int, nro_sicop: str | None) -> None:
    encajes = ("alta", "media", "baja", "sin_coincidencia") if nro_sicop else ("alta", "media")
    marcas = ", ".join("?" * len(encajes))
    filtro = " AND a.nro_sicop = ?" if nro_sicop else ""
    filas = conn.execute(
        "SELECT a.nro_sicop, t.descripcion, a.familia, a.producto, a.encaje, a.regla, a.evidencia,"
        " a.plazo_estado, a.calidad_datos FROM opportunity_assessments a JOIN tenders t USING (nro_sicop)"
        f" WHERE a.rules_version = ? AND a.encaje IN ({marcas}){filtro}"
        " ORDER BY a.encaje = 'alta' DESC, a.encaje = 'media' DESC, t.fecha_cierre_recepcion DESC LIMIT ?",
        (version, *encajes, *((nro_sicop,) if nro_sicop else ()), limite),
    ).fetchall()
    if not filas:
        print("Sin coincidencias para mostrar.")
        return
    print("Candidatos (Alta y Media):" if not nro_sicop else "Resultado del cartel:")
    for nro, desc, familia, producto, encaje, regla, evidencia, plazo, calidad in filas:
        print(f"  {nro} · {ETIQUETAS_ENCAJE[encaje]} · {familia} ({producto}) · {ETIQUETAS_PLAZO[plazo]}"
              f" · {ETIQUETAS_CALIDAD[calidad]}")
        print(f"      {desc}")
        print(f"      regla: {regla}")
        print(f"      evidencia: {evidencia}")


def evaluate(settings: Settings, nro_sicop: str | None, limite: int, reglas_path: Path = REGLAS_PATH) -> int:
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}). Ejecuta python -m app.cli migrate", file=sys.stderr)
        return 1
    try:
        reglas = cargar_reglas(reglas_path)
    except (ReglasError, OSError, ValueError) as exc:
        print(f"Error en las reglas ({reglas_path.name}): {exc}", file=sys.stderr)
        return 1
    with closing(connect(settings.database_path)) as conn:
        if nro_sicop and conn.execute("SELECT 1 FROM tenders WHERE nro_sicop = ?", (nro_sicop,)).fetchone() is None:
            print(f"No hay un cartel con Número SICOP {nro_sicop}.", file=sys.stderr)
            return 1
        try:
            resultado = evaluar_base(conn, reglas, nro_sicop=nro_sicop)
        except sqlite3.OperationalError as exc:
            print(f"Error: {exc}. ¿Falta aplicar migraciones? Ejecuta python -m app.cli migrate", file=sys.stderr)
            return 1
        print(f"Reglas: {reglas_path.name} · versión {reglas.version} · {len(reglas.familias)} familias")
        _imprimir_evaluacion(resultado)
        if limite > 0:
            _imprimir_candidatos(conn, reglas.version, limite, nro_sicop)
    return 0


def _base_de_usuarios(settings: Settings) -> bool:
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}). Ejecuta python -m app.cli migrate", file=sys.stderr)
    return db["status"] == "ok"


# Los cambios hechos desde la terminal quedan en el historial con el actor «terminal».

def create_user(settings: Settings, email: str | None, nombre: str | None, rol: str | None) -> int:
    if not _base_de_usuarios(settings):
        return 1
    email = email or input("Correo: ")
    nombre = nombre or input("Nombre: ")
    rol = rol or input("Nivel (admin o encargado): ").strip().lower()
    # getpass no muestra lo que se escribe. La contraseña no se imprime ni se registra en ningún momento.
    print(f"Contraseña: al menos {usuarios.MIN_CONTRASENA} caracteres. Consejo: {usuarios.CONSEJO_CONTRASENA}.")
    contrasena = getpass.getpass("Contraseña (no se muestra): ")
    try:
        validar_contrasena(contrasena)
        if getpass.getpass("Repite la contraseña: ") != contrasena:
            raise UsuarioInvalido("Las contraseñas no coinciden.")
        with closing(connect(settings.database_path)) as conn:
            crear_usuario(conn, email, nombre, contrasena, rol)
    except UsuarioInvalido as exc:
        print(f"Error: {exc} No se creó el usuario.", file=sys.stderr)
        return 1
    print(f"Usuario creado: {email.strip()} ({usuarios.NIVELES[rol]}). Ya puede iniciar sesión en el panel.")
    return 0


def set_password(settings: Settings, email: str | None) -> int:
    if not _base_de_usuarios(settings):
        return 1
    email = email or input("Correo: ")
    print(f"Contraseña: al menos {usuarios.MIN_CONTRASENA} caracteres. Consejo: {usuarios.CONSEJO_CONTRASENA}.")
    contrasena = getpass.getpass("Contraseña nueva (no se muestra): ")
    try:
        validar_contrasena(contrasena)
        if getpass.getpass("Repite la contraseña: ") != contrasena:
            raise UsuarioInvalido("Las contraseñas no coinciden.")
        with closing(connect(settings.database_path)) as conn:
            usuarios.cambiar_contrasena(conn, usuarios.buscar_id(conn, email), contrasena)
    except UsuarioInvalido as exc:
        print(f"Error: {exc} No se cambió la contraseña.", file=sys.stderr)
        return 1
    print(f"Contraseña cambiada: {email.strip()}. Sus sesiones abiertas se cerraron.")
    return 0


def set_active(settings: Settings, email: str, activo: bool) -> int:
    if not _base_de_usuarios(settings):
        return 1
    try:
        with closing(connect(settings.database_path)) as conn:
            cambio = usuarios.cambiar_estado(conn, usuarios.buscar_id(conn, email), activo)
    except UsuarioInvalido as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    estado = "activo" if activo else "desactivado"
    if not cambio:
        print(f"{email.strip()} ya estaba {estado}. No se cambió nada.")
    elif activo:
        print(f"Usuario activado: {email.strip()}. Ya puede iniciar sesión.")
    else:
        print(f"Usuario desactivado: {email.strip()}. Sus sesiones abiertas se cerraron; sus revisiones se conservan.")
    return 0


def set_role(settings: Settings, email: str, rol: str) -> int:
    if not _base_de_usuarios(settings):
        return 1
    try:
        with closing(connect(settings.database_path)) as conn:
            cambio = usuarios.cambiar_nivel(conn, usuarios.buscar_id(conn, email), rol)
    except UsuarioInvalido as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if cambio:
        print(f"Nivel cambiado: {email.strip()} ahora es {usuarios.NIVELES[rol]}. Aplica en su siguiente clic.")
    else:
        print(f"{email.strip()} ya era {usuarios.NIVELES[rol]}. No se cambió nada.")
    return 0


def list_users(settings: Settings) -> int:
    if not _base_de_usuarios(settings):
        return 1
    with closing(connect(settings.database_path)) as conn:
        lista = usuarios.listar(conn)
    if not lista:
        print("No hay usuarios. Crea uno con python -m app.cli create-user")
        return 0
    for u in lista:
        print(f"{u.email:<36} {u.nombre:<24} {usuarios.NIVELES[u.rol]:<14} "
              f"{'activo' if u.activo else 'desactivado':<12} creado {u.creado[:10]}")
    return 0


def _faltas_para_enviar(settings: Settings) -> list[str]:
    """Qué impide el envío real. Vacío = se puede enviar."""
    faltas = []
    if not settings.notifications_enabled:
        faltas.append("NOTIFICATIONS_ENABLED=true")
    if settings.notifications_dry_run:
        faltas.append("NOTIFICATIONS_DRY_RUN=false")
    if settings.mail_provider != "gmail_api":
        faltas.append("MAIL_PROVIDER=gmail_api")
    if not settings.mail_from:
        faltas.append("MAIL_FROM (la cuenta que envía)")
    return faltas


def _crear_proveedor(settings: Settings) -> avisos.Proveedor:
    """El proveedor real (Gmail). Las pruebas lo reemplazan por uno SIMULADO."""
    from app.notifications import gmail
    credenciales = gmail.cargar_credenciales(settings.google_token_file)
    return gmail.GmailProveedor(credenciales, settings.mail_from)


def google_auth(settings: Settings) -> int:
    from app.notifications import gmail
    try:
        cuenta = gmail.autorizar(settings.google_client_file, settings.google_token_file, settings.mail_from)
    except gmail.GmailError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Autorizado: {cuenta} puede enviar los avisos. Token guardado en GOOGLE_TOKEN_FILE (no se muestra).")
    return 0


def _crear_lector(settings: Settings):
    """El lector real de Gmail (solo lectura). Las pruebas lo reemplazan por uno SIMULADO."""
    from app.sources import gmail_reader
    return gmail_reader.crear_lector(settings)


def obtain_gmail_auth(settings: Settings) -> int:
    from app.sources import gmail_reader
    try:
        cuenta = gmail_reader.autorizar(settings)
    except gmail_reader.GmailError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Autorizado: la app puede LEER (no enviar ni borrar) el buzón de {cuenta}. "
          "Token guardado en GOOGLE_READ_TOKEN_FILE (no se muestra).")
    return 0


def obtain_check_mail(settings: Settings, dias: int) -> int:
    from app.sources import gmail_reader as gr
    if not 1 <= dias <= 30:
        print("Error: --dias debe estar entre 1 y 30.", file=sys.stderr)
        return 1
    try:
        correos = _crear_lector(settings).listar_recientes(dias)
    except gr.GmailError as exc:
        print(f"Error: {exc} No se leyó nada.", file=sys.stderr)
        return 1
    print(f"Correos de {gr.REMITENTE_SICOP} de los últimos {dias} días (solo lectura): {len(correos)}")
    for c in correos:
        if c.valor is None:
            resultado = "FORMATO DESCONOCIDO (comparar el correo con tests/fixtures y ajustar el patrón)"
        elif c.tipo == "codigo":
            resultado = f"código {gr.enmascarar_codigo(c.valor)}"
        else:
            resultado = f"enlace {gr.enmascarar_enlace(c.valor)}"
        print(f"  {c.recibido:%Y-%m-%d %H:%M} · {gr.ASUNTOS[c.tipo]} · {resultado}")
    print("El código y el enlace completos nunca se muestran.")
    return 0


def obtain_request(settings: Settings, ver: bool) -> int:
    from app.sources import gmail_reader as gr
    from app.sources import sicop_browser
    try:
        lector = _crear_lector(settings)
    except gr.GmailError as exc:
        print(f"Error: {exc} No se pidió nada a SICOP.", file=sys.stderr)
        return 1

    def avisar(texto: str) -> None:
        print(f"{datetime.now(HORA_CR):%H:%M:%S} · {texto}", flush=True)

    if ver:
        avisar("Mira la ventana de Chrome, pero NO la toques: un clic fuera del recuadro, Esc o la X cierran las "
               "ventanas de SICOP. Se guardan capturas de cada paso en EXPORTS_DIR.")
    try:
        r = sicop_browser.solicitar_reporte(settings, lector, ver=ver, avisar=avisar)
    except sicop_browser.YaSolicitadoHoy as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sicop_browser.FalloObtencion as exc:
        print(f"FALLO · {exc.motivo}", file=sys.stderr)
        if exc.captura:
            print(f"Captura: {exc.captura} (con los campos vaciados)", file=sys.stderr)
        return 1
    avisar(f"OK · código {gr.enmascarar_codigo(r.codigo)} aceptado · SICOP mostró «Procesando el reporte».")
    if r.process_id:
        avisar(f"La ventana traía el enlace: {gr.enmascarar_enlace('processId=' + r.process_id)}"
               " (guardado para la lección 3).")
    else:
        avisar("La ventana no traía el processId: se sabrá por el correo «Envío de reporte».")
    avisar("El correo con el enlace llega en unos minutos: revisarlo con obtain check-mail.")
    return 0


def obtain_poll(settings: Settings, seguir: bool) -> int:
    import time
    from app.bloqueo import CicloOcupado
    from app.sources import gmail_reader as gr
    from app.sources import obtencion
    try:
        lector = _crear_lector(settings)
    except gr.GmailError as exc:
        print(f"Error: {exc} No se revisó nada.", file=sys.stderr)
        return 1
    while True:
        hora = f"{datetime.now(HORA_CR):%H:%M:%S}"
        try:
            r = obtencion.sondear(settings, lector)
        except CicloOcupado as exc:
            print(f"Error: ya hay otro obtain poll en curso ({exc or 'sin detalle'}). No se hizo nada.", file=sys.stderr)
            return 2
        except obtencion.FalloObtencion as exc:
            print(f"Error: {exc.motivo}", file=sys.stderr)
            return 1
        except gr.GmailError as exc:
            print(f"{hora} · Error de Gmail: {exc} La solicitud sigue abierta; se reintenta en el próximo sondeo.",
                  file=sys.stderr)
            if not seguir:
                return 1
        else:
            if r.fallo:
                print(f"{hora} · FALLO · {r.mensaje}", file=sys.stderr)
                return 1
            print(f"{hora} · {r.mensaje}", flush=True)
            if r.estado in (None, "validado", "enlace_recibido") or not seguir:
                return 0
        time.sleep(settings.obtain_poll_minutes * 60)


def obtain_status(settings: Settings) -> int:
    from app.sources import obtencion
    try:
        filas = obtencion.ultimas(settings)
    except sqlite3.OperationalError:
        print("Error: la base no tiene la tabla solicitudes_sicop: ejecuta python -m app.cli migrate.", file=sys.stderr)
        return 1
    if not filas:
        print("Todavía no hay solicitudes automáticas (obtain request).")
        return 0
    horas = (("codigo_ingresado_en", "código"), ("esperando_enlace_en", "procesando"),
             ("enlace_recibido_en", "enlace"), ("descargado_en", "descargado"), ("validado_en", "validado"))
    for f in filas:
        pasos = " → ".join(f"{nombre} {f[col][11:16]}" for col, nombre in horas if f[col])
        turno = f" (turno {f['turno']})" if f.get("turno") else ""
        print(f"#{f['id']} · {f['solicitada_en'][:16].replace('T', ' ')}{turno} · {f['estado'].upper()}"
              f"{' · ' + pasos if pasos else ''}")
        if f["motivo"]:
            print(f"     motivo: {f['motivo']}")
        if f["archivo_entrada"]:
            print(f"     archivo: {Path(f['archivo_entrada']).name} (SHA-256 {f['archivo_sha256'][:16]}…)")
        if f.get("alerta_estado") and f["alerta_estado"] != "anterior":
            print(f"     alerta: {f['alerta_estado'].replace('_', ' ')} ({f['alerta_en'][11:16]})")
    return 0


def obtain_auto(settings: Settings) -> int:
    """Una vuelta de la obtención automática (la tarea programada, cada 15 min). 0 = ok · 1 = fallo · 2 = ocupado.
    No manda avisos de oportunidades: esos salen con el ciclo de las 8:00 (run-cycle --send)."""
    from app.bloqueo import CicloOcupado
    from app.sources import automatico
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}). Ejecuta python -m app.cli migrate", file=sys.stderr)
        return 1
    try:
        settings.source_mode, settings.obtain_request_hours, settings.obtain_download
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    hora = f"{datetime.now(HORA_CR):%Y-%m-%d %H:%M:%S}"
    try:
        v = automatico.vuelta(settings, crear_lector=lambda s: _crear_lector(s),
                              proveedor_alerta=lambda s: _crear_proveedor(s))
    except CicloOcupado as exc:
        print(f"{hora} · Otra vuelta de obtain auto sigue en curso ({exc or 'sin detalle'}). Esta no hizo nada.",
              file=sys.stderr)
        return 2
    for linea in v.lineas:
        print(f"{hora} · {linea}", file=sys.stderr if linea.startswith("FALLO") else sys.stdout, flush=True)
    return 1 if v.fallo else 0


def notify(settings: Settings, dry_run: bool, solo: str | None = None, semanal: bool = False) -> int:
    if not _base_de_usuarios(settings):
        return 1
    proveedor = None
    if not dry_run:
        faltas = _faltas_para_enviar(settings)
        if faltas:
            print("Error: el envío real está desactivado. Para enviar, en .env: " + ", ".join(faltas) + ".",
                  file=sys.stderr)
            return 1
        from app.notifications.gmail import GmailError
        try:
            proveedor = _crear_proveedor(settings)
        except GmailError as exc:
            print(f"Error: {exc} No se envió nada.", file=sys.stderr)
            return 1
    ahora = datetime.now(HORA_CR)
    if semanal:
        try:
            with closing(connect(settings.database_path)) as conn:
                r = resumen.notify(conn, settings, ahora, dry_run=dry_run, proveedor=proveedor)
        except avisos.AvisoError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"{'DRY-RUN · no se envía nada' if dry_run else 'ENVÍO REAL'} · resumen semanal")
        return _imprimir_resumen(r, dry_run)
    try:
        dias = settings.notify_lookback_days
        with closing(connect(settings.database_path)) as conn:
            resultado = avisos.notify(conn, settings, ahora, dry_run=dry_run, proveedor=proveedor, solo=solo)
    except (avisos.AvisoError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    modo = "DRY-RUN · no se envía nada" if dry_run else "ENVÍO REAL"
    if solo:
        modo += f" · solo a {solo.strip().lower()}"
    print(f"{modo} · reglas {resultado.version_reglas} · versiones vistas en los últimos {dias} días")
    return _imprimir_avisos(resultado, dry_run)


def _imprimir_avisos(resultado: avisos.Resultado, dry_run: bool) -> int:
    try:
        if cargar_reglas().version != resultado.version_reglas:
            print("Aviso: las reglas cambiaron desde la última evaluación; ejecuta python -m app.cli evaluate.")
    except (ReglasError, OSError, ValueError):
        pass
    if resultado.destinatarios == 0:
        print("No hay destinatarios activos: agrégalos en el panel («Destinatarios»). No se preparó nada.")
        return 0
    print(f"Destinatarios activos: {resultado.destinatarios}")
    cierre = f" (de cierre próximo: {resultado.por_cerrar})" if resultado.por_cerrar else ""
    print(f"Avisos nuevos en la outbox: {resultado.nuevos}{cierre} · ya avisados antes (no se repiten): {resultado.ya_avisados}")
    total = sum(len(v) for v in resultado.preparados.values())
    print(f"Preparados {'esperando envío' if dry_run else 'para enviar'}: {total}")
    for para, lista in sorted(resultado.preparados.items()):
        print(f"  {para}: {len(lista)} — " + ", ".join(f"{o.nro_sicop} ({avisos.MOTIVOS[o.motivo]})" for o in lista))
    if dry_run:
        if resultado.vista_previa:
            print(f"Vista previa: {resultado.vista_previa[0].parent}")
        else:
            print("Nada que avisar: no hay vista previa.")
        return 0
    if not resultado.envios:
        print("Nada que avisar: no se envió ningún correo.")
        return 0
    print("Resultado del envío (aceptado = Gmail lo tomó; revisa la bandeja para saber si llegó):")
    for para, envio in sorted(resultado.envios.items()):
        print(f"  {para}: {envio.estado.upper()} · {envio.avisos} oportunidad(es) · {envio.detalle}")
    estados = {e.estado for e in resultado.envios.values()}
    if "incierto" in estados:
        print("Atención: hay envíos INCIERTOS. Quizá salieron: revisa la bandeja antes de reintentar; no se reenvían solos.")
    if "fallido" in estados:
        print("Atención: hay envíos FALLIDOS. Gmail los rechazó; revisa el motivo. No se reintentan solos.")
    return 0 if estados == {"aceptado"} else 1


def _imprimir_resumen(r: resumen.Resultado, dry_run: bool) -> int:
    if r.destinatarios == 0:
        print("No hay destinatarios activos: agrégalos en el panel («Destinatarios»). No se preparó nada.")
        return 0
    print(f"Resumen semanal {r.id_semana}: nuevos en la outbox {r.nuevos} · por enviar {len(r.preparados)}")
    if not r.preparados:
        print("El resumen de esta semana ya se envió (o se intentó): no se repite.")
        return 0
    print(f"Asunto: {r.asunto}")
    if dry_run:
        print(f"Vista previa: {r.vista_previa[0].parent}")
        return 0
    for para, envio in sorted(r.envios.items()):
        print(f"  {para}: {envio.estado.upper()} · {envio.detalle}")
    return 0 if {e.estado for e in r.envios.values()} == {"aceptado"} else 1


ETIQUETAS_ARCHIVO = {"importado": "IMPORTADO", "ya_importado": "YA IMPORTADO", "error": "ERROR",
                     "en_espera": "EN ESPERA", "ignorado": "IGNORADO"}


def run_cycle(settings: Settings, origen: str, dry_run: bool) -> int:
    """Recoger → importar → evaluar → avisar. 0 = ok · 1 = fallo (queda registrado) · 2 = otro ciclo en curso."""
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}). Ejecuta python -m app.cli migrate", file=sys.stderr)
        return 1
    proveedor = None
    if not dry_run:  # las mismas habilitaciones que notify --send, revisadas antes de tocar nada
        faltas = _faltas_para_enviar(settings)
        if faltas:
            print("Error: el envío real está desactivado. Para enviar, en .env: " + ", ".join(faltas) + ".",
                  file=sys.stderr)
            return 1
        from app.notifications.gmail import GmailError
        try:
            proveedor = _crear_proveedor(settings)
        except GmailError as exc:
            print(f"Error: {exc} No se hizo nada.", file=sys.stderr)
            return 1
    ahora = datetime.now(HORA_CR)
    try:
        c = ciclo.run_cycle(settings, origen, dry_run=dry_run, ahora=ahora, proveedor=proveedor)
    except ciclo.CicloOcupado as exc:
        quien = str(exc)
        try:
            ciclo.registrar_ocupado(settings, origen, quien, ahora)
        except sqlite3.Error:
            pass  # la base está ocupada por el otro ciclo: el mensaje de abajo basta
        print(f"Error: ya hay un ciclo en curso{f' ({quien})' if quien else ''}. Este no hizo nada; "
              "espera a que termine.", file=sys.stderr)
        return 2
    except Exception as exc:  # run_cycle ya lo registró como fallo en source_runs
        print(f"Error: el ciclo se detuvo ({type(exc).__name__}: {exc}). Quedó registrado como fallo.",
              file=sys.stderr)
        return 1
    modo = "DRY-RUN · no se envía nada" if dry_run else "ENVÍO REAL"
    print(f"Ciclo #{c.id} · {modo} · origen de los datos: {origen}")
    print(f"Archivos en {settings.incoming_dir}: {len(c.archivos)}")
    for a in c.archivos:
        reporte = f" ({a.reporte})" if a.reporte else ""
        detalle = a.detalle or f"importación #{a.import_id}: aceptadas {a.aceptadas} · rechazadas {a.rechazadas}"
        print(f"  {ETIQUETAS_ARCHIVO[a.resultado]}{reporte} {a.archivo}: {detalle}")
    if c.periodo[0]:
        print(f"Cobertura: carteles publicados del {c.periodo[0]} al {c.periodo[1]}")
    if c.evaluacion:
        e = c.evaluacion
        print(f"Evaluación: reglas {e.version} · {e.carteles} carteles · nuevas {e.nuevas} · actualizadas {e.actualizadas}")
    if c.aviso_omitido:
        print(f"Avisos: NO se avisó ({c.aviso_omitido}).")
    if c.avisos:
        _imprimir_avisos(c.avisos, dry_run)
    if c.resumen:
        _imprimir_resumen(c.resumen, dry_run)
    if c.estado == "ok":
        print(f"Ciclo #{c.id}: OK.")
        return 0
    print(f"Ciclo #{c.id}: FALLO · {c.error}", file=sys.stderr)
    return 1


TIPOS_ERROR = {"falsa_alerta": "FALSA ALERTA (no encaja)", "otra_familia": "OTRA FAMILIA (el cartel sí encaja)",
               "no_alertado": "NO ALERTADO (encajaba)"}


def _pct(valor) -> str:
    return "—" if valor is None else f"{valor} %"


def _fila_calidad(nombre: str, c) -> str:
    precision = f"{_pct(c.precision)} ({c.verdaderos}/{c.alertas})"
    cobertura = f"{_pct(c.cobertura)} ({c.cubiertos}/{c.relevantes})"
    return f"  {nombre:24}{precision:>20}{cobertura:>20}"


def score_rules(settings: Settings, mostrar: int, reglas_path: Path = REGLAS_PATH) -> int:
    """A3: precisión y cobertura por familia con las reglas actuales del YAML; guarda la medición."""
    db = check_database(settings.database_path)
    if db["status"] != "ok":
        print(f"Error: la base no está lista ({db['detail']}). Ejecuta python -m app.cli migrate", file=sys.stderr)
        return 1
    try:
        reglas = cargar_reglas(reglas_path)
    except (ReglasError, OSError, ValueError) as exc:
        print(f"Error en las reglas ({reglas_path.name}): {exc}", file=sys.stderr)
        return 1
    with closing(connect(settings.database_path)) as conn:
        m = calidad.medir(reglas, conn)
        medicion_id, nueva = calidad.guardar(conn, m, datetime.now(HORA_CR))
    print(f"Reglas: {reglas_path.name} · versión {m.version}")
    print(f"Casos: {m.contar('golden')} del golden set · {m.contar('revisión')} de revisiones humanas"
          " (las que dicen si encaja)")
    print(f"  {'Familia':24}{'Precisión':>20}{'Cobertura':>20}")
    for familia, c in m.por_familia.items():
        if familia == calidad.TOTAL or not (c.alertas or c.relevantes):
            continue
        print(_fila_calidad(familia, c))
    sin_casos = [f for f, c in m.por_familia.items() if f != calidad.TOTAL and not (c.alertas or c.relevantes)]
    if sin_casos:
        print(f"  Sin casos para medir: {', '.join(sin_casos)}")
    print(_fila_calidad("TOTAL (por cartel)", m.por_familia[calidad.TOTAL]))
    print(f"Errores: {len(m.errores)}" + (" (ninguno)" if not m.errores else ""))
    for e in m.errores[:mostrar]:
        print(f"  {TIPOS_ERROR[e.tipo]} · {e.familia or 'cualquier familia'} · {e.caso.nro_sicop} ({e.caso.fuente})")
        print(f"      {e.caso.titulo}")
        for ev in e.caso.evaluaciones:
            print(f"      obtenido: {ev.familia} → {ev.encaje} · {ev.regla} · {ev.evidencia}")
        if not e.caso.evaluaciones:
            print("      obtenido: ninguna señal")
    if len(m.errores) > mostrar:
        print(f"  … y {len(m.errores) - mostrar} más (usa --mostrar)")
    print(f"Medición #{medicion_id} guardada." if nueva else
          f"Sin cambios desde la medición #{medicion_id} (misma versión y mismos resultados): no se guarda otra.")
    return 0


def backup(settings: Settings, output: Path) -> int:
    try:
        r = respaldo.respaldar(settings.database_path, output, datetime.now(HORA_CR))
    except respaldo.RespaldoError as exc:
        print(f"Error: {exc}. No se hizo el respaldo.", file=sys.stderr)
        return 1
    d = r.datos
    print(f"Respaldo: {r.base}")
    print(f"Manifiesto: {r.manifiesto}")
    print(f"Commit {d['commit'][:12]} · esquema {d['version_esquema']} · integridad {d['integridad']}"
          f" · SHA-256 {d['sha256'][:16]}…")
    print("Filas: " + " · ".join(f"{t} {n}" for t, n in d["filas"].items()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="SICOP CONNECT")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Muestra la configuración disponible y pendiente, sin secretos")
    sub.add_parser("migrate", help="Crea o actualiza el esquema de la base (repetible)")
    imp = sub.add_parser("import", help="Importa un reporte de SICOP (repetible: el mismo archivo no duplica)")
    imp.add_argument("--path", required=True, type=Path,
                     help="Ruta del CSV (o del ZIP, para catalogo y adjudicaciones)")
    imp.add_argument("--report", required=True, choices=[*IMPORTADORES, "adjudicaciones"],
                     help="Tipo de reporte (importar carteles antes que lineas y adjudicaciones;"
                          " adjudicaciones = el ZIP «Reporte de adjudicaciones en firme» tal como llega)")
    imp.add_argument("--origen", required=True, choices=ORIGENES,
                     help="Origen de los datos: real, sintetico o simulado")
    com = sub.add_parser("compra", help="Muestra un cartel con su comprador y sus líneas")
    com.add_argument("nro_sicop", help="Número SICOP (texto, con ceros iniciales si los tiene)")
    ev = sub.add_parser("evaluate", help="Evalúa los carteles con config/hermatix_rules.yaml (repetible)")
    ev.add_argument("--nro", dest="nro_sicop", help="Evaluar y mostrar solo este Número SICOP")
    ev.add_argument("--mostrar", type=int, default=20, help="Cuántos candidatos mostrar (por defecto 20)")
    sc = sub.add_parser("score-rules", help="Precisión y cobertura de las reglas por familia (golden set y "
                                            "revisiones); guarda la medición")
    sc.add_argument("--mostrar", type=int, default=20, help="Cuántos errores mostrar con su evidencia (por defecto 20)")
    cu = sub.add_parser("create-user", help="Crea un usuario del panel (pide la contraseña sin mostrarla)")
    cu.add_argument("--email", help="Correo con el que inicia sesión (si falta, se pregunta)")
    cu.add_argument("--nombre", help="Nombre visible en el panel (si falta, se pregunta)")
    cu.add_argument("--rol", choices=list(usuarios.NIVELES), help="Nivel: admin o encargado (si falta, se pregunta)")
    sr = sub.add_parser("set-role", help="Cambia el nivel de acceso de un usuario (admin o encargado)")
    sr.add_argument("--email", required=True, help="Correo del usuario")
    sr.add_argument("--rol", required=True, choices=list(usuarios.NIVELES), help="Nivel nuevo")
    sp = sub.add_parser("set-password", help="Pone una contraseña nueva (sin mostrarla) y cierra sus sesiones")
    sp.add_argument("--email", help="Correo del usuario (si falta, se pregunta)")
    for nombre, ayuda in (("deactivate-user", "Desactiva un usuario (no lo borra) y cierra sus sesiones"),
                          ("activate-user", "Vuelve a activar un usuario desactivado")):
        sub.add_parser(nombre, help=ayuda).add_argument("--email", required=True, help="Correo del usuario")
    sub.add_parser("list-users", help="Lista los usuarios del panel (correo, nombre, nivel, estado; nunca la contraseña)")
    no = sub.add_parser("notify", help="Prepara los avisos por correo y los envía o muestra (repetible: no duplica)")
    modo = no.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dry-run", action="store_true",
                      help="Prepara los avisos y escribe la vista previa en EXPORTS_DIR, sin enviar nada")
    modo.add_argument("--send", action="store_true",
                      help="Envío real por Gmail (exige NOTIFICATIONS_ENABLED=true y NOTIFICATIONS_DRY_RUN=false)")
    no.add_argument("--solo", metavar="CORREO", help="Solo a este destinatario activo (prueba controlada)")
    no.add_argument("--resumen-semanal", action="store_true",
                    help="El resumen ejecutivo de la semana anterior (el ciclo lo arma solo los lunes); uno por semana")
    sub.add_parser("google-auth", help="Autorización única de Gmail: entra como MAIL_FROM en el navegador")
    ob = sub.add_parser("obtain", help="Obtención automática de SICOP (por ahora: leer el buzón, sin cambiar nada)")
    ob_sub = ob.add_subparsers(dest="obtain_command", required=True)
    ob_sub.add_parser("gmail-auth", help="Autorización única de LECTURA de Gmail: entra como SICOP_REQUEST_EMAIL")
    cm = ob_sub.add_parser("check-mail", help="Lista los correos de SICOP recientes con código y enlace enmascarados")
    cm.add_argument("--dias", type=int, default=3, help="Días hacia atrás (1 a 30; por defecto 3)")
    rq = ob_sub.add_parser("request", help="UNA solicitud real del «Detalle pliego de condiciones» en CSV (una por día)")
    rq.add_argument("--ver", action="store_true", help="Mostrar la ventana del navegador (para la prueba supervisada)")
    po = ob_sub.add_parser("poll", help="Espera el correo con el enlace, descarga el ZIP, lo valida y lo deja en la entrada")
    po.add_argument("--seguir", action="store_true",
                    help="Repetir cada OBTAIN_POLL_MINUTES hasta validado, fallido o el plazo (Ctrl+C es seguro)")
    ob_sub.add_parser("status", help="Las últimas solicitudes automáticas con su estado y horas")
    ob_sub.add_parser("auto", help="Una vuelta de la obtención automática (tarea programada; solo con SOURCE_MODE=auto)")
    bk = sub.add_parser("backup", help="Respaldo consistente de la base (API de SQLite) con su manifiesto")
    bk.add_argument("--output", required=True, type=Path,
                    help="Carpeta del respaldo (otra que la de la base; idealmente otro disco)")
    rc = sub.add_parser("run-cycle", help="Ciclo completo: recoger INCOMING_DIR → importar → evaluar → avisar")
    rc.add_argument("--origen", required=True, choices=ORIGENES,
                    help="Origen de los datos de la carpeta de entrada: real, sintetico o simulado")
    modo_ciclo = rc.add_mutually_exclusive_group()
    modo_ciclo.add_argument("--dry-run", action="store_true", help="(por defecto) Avisos solo en vista previa")
    modo_ciclo.add_argument("--send", action="store_true",
                            help="Envío real de los avisos (las mismas exigencias que notify --send)")
    return parser


def main(argv: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = settings or load_settings()
    if args.command == "doctor":
        return doctor(settings)
    if args.command == "migrate":
        return migrate(settings)
    if args.command == "import":
        return importar(settings, args.path, args.report, args.origen)
    if args.command == "compra":
        return compra(settings, args.nro_sicop)
    if args.command == "evaluate":
        return evaluate(settings, args.nro_sicop, args.mostrar)
    if args.command == "score-rules":
        return score_rules(settings, args.mostrar)
    if args.command == "create-user":
        return create_user(settings, args.email, args.nombre, args.rol)
    if args.command == "set-role":
        return set_role(settings, args.email, args.rol)
    if args.command == "set-password":
        return set_password(settings, args.email)
    if args.command in ("deactivate-user", "activate-user"):
        return set_active(settings, args.email, args.command == "activate-user")
    if args.command == "list-users":
        return list_users(settings)
    if args.command == "notify":
        if args.resumen_semanal and args.solo:
            print("Error: --solo es solo para los avisos, no para el resumen semanal.", file=sys.stderr)
            return 1
        return notify(settings, args.dry_run, args.solo, args.resumen_semanal)
    if args.command == "google-auth":
        return google_auth(settings)
    if args.command == "obtain":
        if args.obtain_command == "gmail-auth":
            return obtain_gmail_auth(settings)
        if args.obtain_command == "request":
            return obtain_request(settings, args.ver)
        if args.obtain_command == "poll":
            return obtain_poll(settings, args.seguir)
        if args.obtain_command == "status":
            return obtain_status(settings)
        if args.obtain_command == "auto":
            return obtain_auto(settings)
        return obtain_check_mail(settings, args.dias)
    if args.command == "backup":
        return backup(settings, args.output)
    if args.command == "run-cycle":
        return run_cycle(settings, args.origen, dry_run=not args.send)
    return 1


if __name__ == "__main__":
    sys.exit(main())
