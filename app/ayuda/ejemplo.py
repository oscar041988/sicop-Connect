"""Base de EJEMPLO para las capturas de la ayuda: datos inventados que llenan todas las pantallas de las misiones.

* Vive en su propia carpeta (por defecto data/ayuda_ejemplo/), con su base, documentos, expedientes y grabaciones.
  Se borra y se rehace cada vez; solo se borra una carpeta que tenga la marca de ejemplo.
* Nunca toca la base real: se niega si la base de ejemplo coincide con DATABASE_PATH.
* Todo va marcado: títulos «EJEMPLO · …», instituciones y usuarios «de Ejemplo», correos @ejemplo.test e
  importaciones con origen «sintetico».
* Usa las funciones reales de la app (importadores, evaluación, revisiones, seguimiento, expediente, resumen con
  un OpenAI SIMULADO que nunca llama a la red). Solo las tablas sin función de escritura (ficha y documentos de
  SICOP, bitácora) se llenan con INSERT, como en tests/test_panel_enriquecimiento.py.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app import avisos, destinatarios, expediente_archivos, panel, seguimiento, usuarios
from app.ai import resumen as ia_resumen
from app.ayuda import CARPETA_EJEMPLO, PROJECT_ROOT
from app.config import DEFAULTS, load_settings
from app.database import apply_migrations, connect
from app.historial import Quien
from app.importers import adjudicaciones
from app.importers.carteles import import_carteles
from app.importers.catalogo import import_catalogo
from app.importers.instituciones import import_instituciones
from app.importers.lineas import import_lineas
from app.matching.evaluar import evaluar_base
from app.matching.reglas import cargar_reglas

MARCA = ".ayuda_ejemplo"          # archivo que dice «esta carpeta es de ejemplo y se puede borrar»
ORIGEN = "sintetico"
CR = timezone(timedelta(hours=-6))
CONTRASENA = "contraseña de ejemplo para las capturas"
ADMIN = ("ana@ejemplo.test", "Ana Ejemplo")
ENCARGADO = ("luis@ejemplo.test", "Luis Ejemplo")
OTRA = ("sofia@ejemplo.test", "Sofía Ejemplo")
PDF_DE_EJEMPLO = PROJECT_ROOT / "tests" / "fixtures" / "documentos_simulados" / "con_texto.pdf"

PRINCIPAL = "20269990001"      # Alta, cierra en 4 días, sin revisar: ficha, documentos y resumen con IA
SEGUIDO = "20269990002"        # Interesa, en seguimiento con encargado, archivos y notas
SIN_ENCARGADO = "20269990003"  # en seguimiento, todavía sin encargado
NUEVO = "20269990004"          # llega en la última importación: etiqueta «Nuevo»
CON_GRABACION = "20269990006"  # su consulta a SICOP falló: grabación por revisar

INSTITUCIONES = [("3999000001", "INSTITUCIÓN DE EJEMPLO A"), ("3999000002", "MUNICIPALIDAD DE EJEMPLO B"),
                 ("3999000003", "MINISTERIO DE EJEMPLO C")]
CATALOGO = [  # clasificación (8) + identificación (8) = el código de 16 dígitos de las líneas
    ("99990001", "00000001", "EJEMPLO SERVICIO DE MONITOREO GPS DE VEHÍCULOS"),
    ("99990001", "00000002", "EJEMPLO DISPOSITIVO GPS PARA VEHÍCULO"),
    ("99990002", "00000001", "EJEMPLO CÁMARA CORPORAL PARA POLICÍA"),
    ("99990003", "00000001", "EJEMPLO SILLA DE OFICINA"),
]
GPS, EQUIPO, CAMARA, SILLA = (c + i for c, i, _ in CATALOGO)

GPS_ALTA = "Servicio de monitoreo GPS de vehículos"
GPS_MEDIA = "Alquiler de GPS para la flotilla"
CAMARAS = "Cámaras corporales para policía"
TIPOS = ["Licitación Reducida", "Licitación Menor", "Procedimiento por Excepción"]


@dataclass(frozen=True)
class Cartel:
    nro: str
    titulo: str
    cedula: str
    tipo: str
    dias: int | None          # días hasta el cierre (None: sin fecha, «por verificar»)
    lineas: tuple[tuple[str, str, str, str], ...] = ((GPS, "1", "250000.00", "CRC"),)  # código, cantidad, precio, moneda


def _carteles() -> tuple[list[Cartel], list[Cartel]]:
    """(primera importación, última importación). Más de 25 candidatos para que el panel tenga 2 páginas."""
    a, b, c = (ced for ced, _ in INSTITUCIONES)
    primera = [
        Cartel(PRINCIPAL, f"EJEMPLO · {GPS_ALTA} de la flotilla institucional", a, TIPOS[0], 4,
               ((GPS, "12", "180000.00", "CRC"), (EQUIPO, "40", "95000.00", "CRC"), (EQUIPO, "5", "210.00", "USD"))),
        Cartel(SEGUIDO, f"EJEMPLO · {GPS_ALTA} municipales", b, TIPOS[1], 20,
               ((GPS, "1", "4500000.00", "CRC"),)),
        Cartel(SIN_ENCARGADO, f"EJEMPLO · {CAMARAS} municipal", b, TIPOS[0], 10,
               ((CAMARA, "30", "310000.00", "CRC"),)),
        Cartel("20269990005", f"EJEMPLO · {GPS_ALTA} (concurso cerrado)", c, TIPOS[0], -5),
        Cartel(CON_GRABACION, f"EJEMPLO · {GPS_MEDIA} de bomberos", c, TIPOS[1], 15),
        Cartel("20269990007", "EJEMPLO · Compra de GPS", a, TIPOS[1], 18, ((EQUIPO, "3", "60000.00", "CRC"),)),
        Cartel("20269990008", f"EJEMPLO · {CAMARAS} de tránsito", c, TIPOS[2], None, ((CAMARA, "8", "290000.00", "CRC"),)),
        Cartel("20269990009", "EJEMPLO · Compra de sillas", a, TIPOS[1], 9, ((SILLA, "50", "45000.00", "CRC"),)),
    ]
    for n in range(10, 38):  # relleno: candidatos Alta y Media con cierres variados
        titulo = (GPS_ALTA, GPS_MEDIA, CAMARAS)[n % 3]
        # Sin líneas, el título «Alquiler de GPS…» queda en Media; con la línea de GPS subiría a Alta.
        lineas = () if titulo == GPS_MEDIA else ((CAMARA if titulo == CAMARAS else GPS, "1", "1000000.00", "CRC"),)
        primera.append(Cartel(f"202699900{n:02d}", f"EJEMPLO · {titulo} · lote {n}", INSTITUCIONES[n % 3][0],
                              TIPOS[n % 3], 2 + (n * 7) % 45, lineas))
    ultima = [Cartel(NUEVO, f"EJEMPLO · {GPS_ALTA} recolectores de basura", a, TIPOS[0], 12)]
    return primera, ultima


# --- Archivos CSV con el formato de SICOP --------------------------------------------------------------------

def _csv(ruta: Path, encabezado: str, filas: list[str]) -> Path:
    ruta.write_text("\n".join([encabezado, *filas]) + "\n", encoding="utf-8-sig")
    return ruta


def _fecha_sicop(momento: datetime) -> str:
    return momento.astimezone(CR).strftime("%d/%m/%Y %H:%M:%S")


def _csv_carteles(ruta: Path, carteles: list[Cartel], ahora: datetime) -> Path:
    publicado = _fecha_sicop(ahora - timedelta(days=3))
    filas = []
    for k, x in enumerate(carteles, start=1):
        cierre = "" if x.dias is None else _fecha_sicop((ahora + timedelta(days=x.dias)).replace(hour=16, minute=0))
        filas.append(f"{x.nro};{x.cedula};{publicado};2026LE-{k:06d}-0099990001;00099;PROVEEDURÍA DE EJEMPLO;{x.tipo};"
                     f"Cantidad definida;;{x.titulo};N;{publicado};{publicado};{cierre};{cierre}")
    return _csv(ruta, "Número SICOP;Cédula;Fecha Publicación;Numero de procedimiento;Cod Unidad Compra;"
                      "Nombre Unidad Compra;Tipo de procedimiento;Modalidad Procedimiento;Excepción CD;Descripción;"
                      "Pago Adelantado Pymes;Fecha Invitación;Fecha Inicio Recepción;Fecha Cierre Recepción;"
                      "Fecha Apertura", filas)


def _csv_lineas(ruta: Path, carteles: list[Cartel]) -> Path:
    filas = [f"{x.nro};{n};1;{cantidad};{precio};{moneda};505.00;{codigo}"
             for x in carteles for n, (codigo, cantidad, precio, moneda) in enumerate(x.lineas, start=1)]
    return _csv(ruta, "Número SICOP;Numero de linea;Numero partida;Cantidad;Precio Unitario Estimado;Moneda;"
                      "Tipo Cambio USD;Código identificación", filas)


def _zip_adjudicaciones(ruta: Path, ahora: datetime) -> Path:
    """Ganadores INVENTADOS de cuatro carteles de relleno (para la página «Competencia»)."""
    firme = _fecha_sicop(ahora - timedelta(days=40))
    ganadores = [("20269990010", "3101999001"), ("20269990011", "3101999002"), ("20269990013", "3101999001"),
                 ("20269990012", "3101999003")]
    adj = [f"{nro};2026LE-000001-0099990001;{firme};{firme};Si;{firme};N" for nro, _ in ganadores]
    prov = [f"{nro};2026LE-000001-0099990001;{ced}" for nro, ced in ganadores]
    lin = [f"{nro};1;{ced};1;{900000 + 50000 * k}.00;CRC;0;0;0;0;1.00" for k, (nro, ced) in enumerate(ganadores)]
    partes = {"Detalle Adjudicaciones.csv": ("Número SICOP;Numero de procedimiento;Fecha Comunicación;"
                                             "Fecha Adj Firme;Permite Recursos;Fecha Maxima Recursos;Desierto", adj),
              "Det Proveedores Adj.csv": ("Número SICOP;Numero de procedimiento;Cédula Empresa Proveedora", prov),
              "Det Lineas Adjudicadas.csv": ("Número SICOP;Numero de linea;Cédula Empresa Proveedora;Cantidad;Precio;"
                                             "Moneda;Descuento;IVA;Otros Impuestos;Acarreos;Tipo Cambio CRC", lin)}
    with zipfile.ZipFile(ruta, "w") as zf:
        for nombre, (encabezado, filas) in partes.items():
            zf.writestr(nombre, ("﻿" + "\n".join([encabezado, *filas]) + "\n").encode("utf-8"))
    return ruta


COMPETIDORES = {"3101999001": "EMPRESA DE EJEMPLO UNO S.A.", "3101999002": "EMPRESA DE EJEMPLO DOS S.A.",
                "3101999003": "EMPRESA DE EJEMPLO TRES S.A."}


def _golden(carpeta: Path) -> None:
    """Golden set de EJEMPLO (la página «Calidad de reglas» lo usa en las capturas en vez del real)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    filas = [
        f"20269990101;EJEMPLO · {GPS_ALTA} de la policía;interesa;gps_flotas;sí;;ejemplo;2026-10-01",
        f"20269990102;EJEMPLO · {CAMARAS} de seguridad;interesa;camaras_corporales;sí;;ejemplo;2026-10-01",
        f"20269990103;EJEMPLO · {GPS_MEDIA} de ambulancias;interesa;gps_flotas;sí;;ejemplo;2026-10-01",
        f"20269990104;EJEMPLO · {GPS_ALTA} para el museo de autos antiguos;no_interesa;;sí;;ejemplo;2026-10-01",
        "20269990105;EJEMPLO · Localización satelital de buses escolares;interesa;gps_flotas;sí;;ejemplo;2026-10-01",
    ]
    _csv(carpeta / "golden_set.csv", "nro_sicop;titulo;etiqueta;familia_esperada;confirmada;nota;fuente;actualizado",
         filas)


# --- Entorno: todas las claves de la configuración, apuntando a la carpeta de ejemplo -------------------------

def entorno(carpeta: Path = CARPETA_EJEMPLO) -> dict[str, str]:
    """TODAS las claves de DEFAULTS (así un .env real no influye) con rutas dentro de la carpeta de ejemplo."""
    valores = dict(DEFAULTS)
    valores.update({
        "APP_ENV": "development", "DATABASE_PATH": str(carpeta / "sicop.db"),
        "RAW_DATA_DIR": str(carpeta / "raw"), "INCOMING_DIR": str(carpeta / "entrada"),
        "EXPORTS_DIR": str(carpeta / "exportaciones"), "RECORDINGS_DIR": str(carpeta / "grabaciones"),
        "DOCUMENTS_DIR": str(carpeta / "documentos"), "EXPEDIENTES_DIR": str(carpeta / "expedientes"),
        "PROFILE_DOCS_DIR": str(carpeta / "perfil"),
        "SESSION_SECRET": "sesion-de-ejemplo-para-las-capturas-de-la-ayuda-000",
        # Solo para que el panel muestre el bloque del resumen. No hay clave: nada puede llamar a OpenAI.
        "AI_MODE": "openai", "OPENAI_API_KEY": "", "OPENAI_MODEL": "modelo-de-ejemplo",
        "NOTIFICATIONS_ENABLED": "false", "NOTIFICATIONS_DRY_RUN": "true", "SCHEDULER_ENABLED": "false",
        "ENRICH_ENABLED": "false", "SOURCE_MODE": "manual", "MAIL_PROVIDER": "unconfigured",
    })
    return valores


@dataclass
class Claves:
    """Lo que las capturas necesitan saber de la base de ejemplo (se guarda en claves.json)."""
    principal: str
    seguido: str
    sin_encargado: str
    consulta_grabacion: int
    grabacion: str          # «AAAA-MM-DD/nro/HHMMSS», relativa a RECORDINGS_DIR
    email: str
    contrasena: str


def leer_claves(carpeta: Path = CARPETA_EJEMPLO) -> Claves:
    return Claves(**json.loads((carpeta / "claves.json").read_text(encoding="utf-8")))


class EjemploInseguro(RuntimeError):
    """La carpeta de ejemplo apunta a la base real o a una carpeta que no es de ejemplo."""


def _preparar_carpeta(carpeta: Path) -> None:
    real = load_settings().database_path.resolve()
    if (carpeta / "sicop.db").resolve() == real:
        raise EjemploInseguro(f"La base de ejemplo no puede ser la base real ({real}).")
    if carpeta.exists():
        if not (carpeta / MARCA).is_file():
            raise EjemploInseguro(f"{carpeta} existe y no es una carpeta de ejemplo: no se borra.")
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    (carpeta / MARCA).write_text("Carpeta de EJEMPLO de la ayuda: se borra y se rehace sola.\n", encoding="utf-8")


# --- Resumen con IA: respuesta SIMULADA ----------------------------------------------------------------------

class _OpenAIDeEjemplo:
    """Imita client.responses.create con una respuesta fija. Nunca usa la red."""

    def __init__(self, datos: dict):
        self.responses = SimpleNamespace(create=lambda **_: SimpleNamespace(
            status="completed", output_text=json.dumps(datos, ensure_ascii=False), output=[],
            model="modelo-de-ejemplo", usage=SimpleNamespace(input_tokens=12000, output_tokens=900),
            incomplete_details=None))


def _resumen_de_ejemplo() -> dict:
    nada = {"valor": "no encontrado", "cita": "no encontrado"}
    return {
        "de_que_trata": "EJEMPLO: la institución contrata el monitoreo GPS de 12 vehículos por 24 meses.",
        "que_piden": [
            {"linea": "1", "bien_o_servicio": "Servicio de monitoreo GPS", "cantidad": "12",
             "especificaciones_clave": ["Reporte cada 30 s", "Plataforma web"], "cita": "[DOC 1 · pág. 1]"},
            {"linea": "2", "bien_o_servicio": "Dispositivo GPS", "cantidad": "40",
             "especificaciones_clave": ["Conexión 4G", "Botón de pánico"], "cita": "[DOC 1 · pág. 1]"}],
        "requerimientos": [
            {"requisito": "Experiencia mínima de 3 años", "tipo": "experiencia", "excluyente": True,
             "cita": "[DOC 1 · pág. 1]"},
            {"requisito": "Soporte técnico en horario de oficina", "tipo": "tecnico", "excluyente": False,
             "cita": "[DOC 1 · pág. 1]"}],
        "kpi_pliego": {"plazo_entrega": {"valor": "30 días hábiles", "cita": "[DOC 1 · pág. 1]"},
                       "vigencia_contrato": {"valor": "24 meses", "cita": "[DOC 1 · pág. 1]"},
                       "garantia_participacion_pct": nada, "garantia_cumplimiento_pct": nada,
                       "peso_precio_pct": {"valor": "80 %", "cita": "SICOP"},
                       "nivel_riesgo": {"valor": "medio", "cita": "no encontrado"}},
        "plazos": {"cierre_recepcion": nada, "apertura_ofertas": nada, "otros": []},
        "monto_estimado": {"valor": "no encontrado", "moneda": "no encontrado", "cita": "no encontrado"},
        "criterios_de_evaluacion": [{"criterio": "Precio", "peso": "80 %", "cita": "SICOP"},
                                    {"criterio": "Experiencia", "peso": "20 %", "cita": "SICOP"}],
        "encaje_hermatix": {"familia": "gps_flotas", "producto": "FleetMatix",
                            "por_que": "EJEMPLO: piden rastreo GPS de vehículos."},
        "riesgos_y_dudas": [{"riesgo": "EJEMPLO: confirmar si piden un técnico en planilla.",
                             "cita": "[DOC 1 · pág. 1]"}],
        "recomendacion": "dar_seguimiento",
        "justificacion": "EJEMPLO: encaja con el producto de GPS y el plazo alcanza.",
    }


# --- Crear la base ----------------------------------------------------------------------------------------------

def _sql(conn: sqlite3.Connection, sql: str, params=()) -> int:
    with conn:
        return conn.execute(sql, params).lastrowid


def _ficha_y_documentos(conn: sqlite3.Connection, carpeta: Path, ahora: datetime) -> None:
    """Ficha de SICOP del cartel principal (con un cierre distinto: sale el aviso) y dos documentos."""
    consultado = (ahora - timedelta(hours=3)).astimezone(CR).isoformat(timespec="seconds")
    cierre = (ahora + timedelta(days=5)).astimezone(CR).replace(hour=10, minute=0, second=0).isoformat()
    apertura = (ahora + timedelta(days=5)).astimezone(CR).replace(hour=10, minute=30, second=0).isoformat()
    garantias = {"participationGuarnRcvYnNm": "No", "fulfillmentGuarnRcvYnNm": "Sí", "fulfillmentGuarnAmt": 5,
                 "fulfillmentGuarnAmtType": "RAT", "fulfillmentGuarnDur": "12", "contractDur": "24",
                 "contractDurUnitNm": "Meses", "amtReadjustYnNm": "No"}
    criterios = {"criterios": ["Precio 80%", "Experiencia 20%"], "impactos": []}
    detalle = _sql(conn, "INSERT INTO tender_details (nro_sicop, consultado_en, content_hash, copia_fiel,"
                         " campos_quitados, estado_concurso, version_pliego, modificado, cierre_recepcion, apertura,"
                         " monto_estimado, moneda_monto, tipo_procedimiento, lineas_total, garantias, criterios)"
                         " VALUES (?, ?, 'ejemplo', '{}', '[]', 'En recepción de ofertas', '1', 'N', ?, ?, '6000000',"
                         " 'CRC', 'LICITACIÓN REDUCIDA', 3, ?, ?)",
                   (PRINCIPAL, consultado, cierre, apertura, json.dumps(garantias), json.dumps(criterios)))
    destino = carpeta / "documentos" / PRINCIPAL
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PDF_DE_EJEMPLO, destino / "pliego.pdf")
    tamano = (destino / "pliego.pdf").stat().st_size
    doc = _sql(conn, "INSERT INTO tender_documents (nro_sicop, detalle_id, tipo_documento, nombre_documento,"
                     " nombre_original, server_file, tamano_bytes, sha256, ruta_local, registrado_en, estado,"
                     " texto_estado, paginas) VALUES (?, ?, 'Pliego', 'PLIEGO DE CONDICIONES DE EJEMPLO',"
                     " 'Pliego de ejemplo.pdf', 'pliego.pdf', ?, 'ejemplo', ?, ?, 'guardado', 'extraido', 1)",
               (PRINCIPAL, detalle, tamano, f"{PRINCIPAL}/pliego.pdf", consultado))
    _sql(conn, "INSERT INTO tender_document_text (documento_id, pagina, texto) VALUES (?, 1, ?)",
         (doc, "EJEMPLO. Pliego de condiciones inventado para la ayuda. Se requiere el monitoreo GPS de 12"
               " vehículos y 40 dispositivos. Experiencia mínima de 3 años."))
    _sql(conn, "INSERT INTO tender_documents (nro_sicop, detalle_id, tipo_documento, nombre_documento,"
               " nombre_original, server_file, registrado_en, estado, motivo) VALUES (?, ?, 'Anexo',"
               " 'ANEXO TÉCNICO DE EJEMPLO', 'Anexo de ejemplo.xlsx', 'anexo.xlsx', ?, 'fallo', 'no llegó en 60 s')",
         (PRINCIPAL, detalle, consultado))


def _bitacora(conn: sqlite3.Connection, ahora: datetime) -> tuple[int, str]:
    """Una corrida de las 10:00 con una consulta bien y otra con FALLO (su grabación la graban las capturas)."""
    inicio = (ahora - timedelta(hours=2)).astimezone(CR).replace(microsecond=0)
    corrida = _sql(conn, "INSERT INTO enrich_runs (iniciada_en, terminada_en, estado, maximo, en_cola, consultados,"
                         " fallos) VALUES (?, ?, 'con_fallos', 20, 2, 2, 1)",
                   (inicio.isoformat(), (inicio + timedelta(minutes=3)).isoformat()))
    _sql(conn, "INSERT INTO enrich_consultas (run_id, nro_sicop, iniciada_en, duracion_s, resultado, motivo)"
               " VALUES (?, ?, ?, 41.0, 'nueva', NULL)", (corrida, PRINCIPAL, inicio.isoformat()))
    hora = inicio + timedelta(minutes=1)
    grabacion = f"{hora:%Y-%m-%d}/{CON_GRABACION}/{hora:%H%M%S}"
    consulta = _sql(conn, "INSERT INTO enrich_consultas (run_id, nro_sicop, iniciada_en, duracion_s, resultado,"
                          " motivo, grabacion) VALUES (?, ?, ?, 60.0, 'fallo', 'EJEMPLO: la página no respondió"
                          " a tiempo', ?)", (corrida, CON_GRABACION, hora.isoformat(), grabacion))
    return consulta, grabacion


def crear(carpeta: Path = CARPETA_EJEMPLO, ahora: datetime | None = None) -> Claves:
    """Borra y rehace la carpeta de ejemplo. Devuelve (y guarda en claves.json) lo que necesitan las capturas."""
    ahora = (ahora or datetime.now(timezone.utc)).replace(microsecond=0)
    _preparar_carpeta(carpeta)
    settings = load_settings(env_file=None, environ=entorno(carpeta))
    raw = settings.raw_data_dir
    archivos = carpeta / "archivos"
    archivos.mkdir()
    primera, ultima = _carteles()
    db = settings.database_path
    apply_migrations(db)
    with closing(connect(db)) as conn:
        import_instituciones(conn, _csv(archivos / "instituciones.csv",
                                        "Cédula;Institución;Dirección;Telefono;Representante;Codigo Postal;Provincia;"
                                        "Cantón;Distrito",
                                        [f"{ced};{nombre};Dirección de ejemplo;0000-0000;PERSONA DE EJEMPLO;10101;"
                                         "San José;San José;Carmen" for ced, nombre in INSTITUCIONES]), ORIGEN, raw)
        import_catalogo(conn, _csv(archivos / "catalogo.csv",
                                   "Codigo Clasificación;Código identificación;Nombre Identificacion;En Uso",
                                   [f"{c};{i};{n};Y" for c, i, n in CATALOGO]), ORIGEN, raw)
        reglas = cargar_reglas()
        for k, lote in enumerate((primera, ultima), start=1):
            import_carteles(conn, _csv_carteles(archivos / f"carteles_{k}.csv", lote, ahora), ORIGEN, raw)
            import_lineas(conn, _csv_lineas(archivos / f"lineas_{k}.csv", lote), ORIGEN, raw)
        adjudicaciones.import_zip(conn, _zip_adjudicaciones(archivos / "adjudicaciones.zip", ahora), ORIGEN, raw)
        evaluar_base(conn, reglas, datetime.now(timezone.utc))  # después de las importaciones: sin el aviso amarillo

        admin = usuarios.crear_usuario(conn, *ADMIN, CONTRASENA, rol=usuarios.ADMIN)
        luis = usuarios.crear_usuario(conn, *ENCARGADO, CONTRASENA)
        usuarios.crear_usuario(conn, *OTRA, CONTRASENA)
        ana = Quien(admin, ADMIN[1])

        hace = lambda horas: ahora - timedelta(hours=horas)  # noqa: E731
        panel.guardar_revision(conn, SEGUIDO, "revisar_requisitos", "", "EJEMPLO: confirmar la experiencia pedida.",
                               luis, hace(30))
        panel.guardar_revision(conn, SEGUIDO, "interesa", "", "EJEMPLO: cumplimos todo, vamos a ofertar.", admin,
                               hace(6))
        panel.guardar_revision(conn, "20269990007", "no_interesa", "no_encaja",
                               "EJEMPLO: solo compran el aparato, sin servicio.", luis, hace(20))
        panel.guardar_revision(conn, "20269990014", "ofertada", "", "", admin, hace(10))

        seguimiento.abrir(conn, SEGUIDO, ana, hace(5))
        seguimiento.asignar(conn, SEGUIDO, luis, ana, hace(5))
        seguimiento.cambiar_etapa(conn, SEGUIDO, "enviada", Quien(luis, ENCARGADO[1]), hace(2))
        seguimiento.escribir_nota(conn, SEGUIDO, "EJEMPLO: llamé a la institución, responden el lunes.",
                                  Quien(luis, ENCARGADO[1]), hace(4))
        with PDF_DE_EJEMPLO.open("rb") as pdf:
            expediente_archivos.guardar(conn, settings.expedientes_dir, SEGUIDO, pdf, "Oferta de ejemplo.pdf",
                                        settings.expediente_max_mb * 1024 * 1024, Quien(luis, ENCARGADO[1]), hace(3))
        seguimiento.abrir(conn, SIN_ENCARGADO, Quien(luis, ENCARGADO[1]), hace(1))

        destinatarios.agregar(conn, "equipo@ejemplo.test", "Equipo de Ejemplo", ana)
        destinatarios.agregar(conn, "marta@ejemplo.test", "Marta Ejemplo", ana)
        pedro = destinatarios.agregar(conn, "pedro@ejemplo.test", "Pedro Ejemplo", ana)
        destinatarios.cambiar_estado(conn, pedro, False, ana)

        _ficha_y_documentos(conn, carpeta, ahora)
        ia_resumen.resumir(conn, load_settings(env_file=None, environ={
            **entorno(carpeta), "OPENAI_API_KEY": "clave-de-ejemplo-sin-uso", "IA_PRECIO_ENTRADA_USD": "1.00",
            "IA_PRECIO_SALIDA_USD": "5.00"}), PRINCIPAL, cliente=_OpenAIDeEjemplo(_resumen_de_ejemplo()),
            dormir=lambda s: None)

        version = panel.version_vigente(conn)
        avisos.preparar(conn, version, ahora, settings.notify_lookback_days)
        de_marta = [i for (i,) in conn.execute("SELECT id FROM notification_outbox WHERE recipient = ?"
                                               " AND nro_sicop IN (?, ?) ORDER BY nro_sicop",
                                               ("marta@ejemplo.test", PRINCIPAL, SEGUIDO))]
        momento = ahora.isoformat(timespec="seconds")
        with conn:
            conn.execute("UPDATE notification_outbox SET status = 'fallido', updated_at = ?, detalle = ? WHERE id = ?",
                         (momento, "EJEMPLO: 550 el buzón no existe", de_marta[0]))
            conn.execute("UPDATE notification_outbox SET status = 'incierto', updated_at = ?, detalle = ? WHERE id = ?",
                         (momento, "EJEMPLO: envío en curso: sin respuesta del proveedor", de_marta[1]))

        consulta, grabacion = _bitacora(conn, ahora)
    _golden(carpeta / "golden")
    claves = Claves(PRINCIPAL, SEGUIDO, SIN_ENCARGADO, consulta, grabacion, ADMIN[0], CONTRASENA)
    (carpeta / "claves.json").write_text(json.dumps(asdict(claves), ensure_ascii=False, indent=2), encoding="utf-8")
    return claves


def correo_de_ejemplo(carpeta: Path, ahora: datetime, base_url: str) -> tuple[str, str]:
    """(asunto, html) del correo diario de «equipo@ejemplo.test», armado con la plantilla real del aviso."""
    with closing(connect(carpeta / "sicop.db")) as conn:
        por_destinatario = avisos.pendientes(conn, ahora, base_url, con_resumen=True)
    oportunidades = por_destinatario.get("equipo@ejemplo.test", [])
    asunto, html, _ = avisos.componer(oportunidades, ahora, base_url)
    return asunto, html


def subida_de_ejemplo(carpeta: Path, numero: int, ahora: datetime | None = None) -> Path:
    """Un CSV de carteles con un cartel EJEMPLO más, para la captura de «Cargar archivo». Cada número da un
    archivo distinto: uno repetido no se vuelve a importar ni a evaluar."""
    ahora = ahora or datetime.now(timezone.utc)
    extra = [Cartel(f"202699902{numero:02d}", f"EJEMPLO · {GPS_ALTA} del cuerpo de bomberos {numero}",
                    INSTITUCIONES[1][0], TIPOS[0], 8)]
    return _csv_carteles(carpeta / "archivos" / f"carteles_subida_{numero}.csv", extra, ahora)


