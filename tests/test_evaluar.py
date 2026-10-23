"""Motor de reglas y comando evaluate. Textos SINTÉTICOS (salvo que se indique); base temporal, nunca data/."""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect
from app.matching.evaluar import Texto, calidad_datos, evaluar_base, evaluar_textos, plazo_estado
from app.matching.reglas import ReglasError, cargar_reglas, normalizar

AHORA = datetime(2026, 10, 9, 12, 0, tzinfo=timezone(timedelta(hours=-6)))
REGLAS_MINI = """\
familias:
  gps_flotas:
    producto: fleetmatix
    senales_alta: ["monitoreo gps"]
    senales_media: ["gps", "control de combustible"]
    contexto: ["flotilla"]
    exclusiones: ["topografico"]
"""


@pytest.fixture(scope="module")
def reglas():
    return cargar_reglas()  # el archivo real config/hermatix_rules.yaml


def _por_familia(reglas, titulo, lineas=None):
    return {e.familia: e for e in evaluar_textos(reglas, titulo, lineas)}


# --- Criterio de aceptación de la guía (sección 16.4) ------------------------------------

def test_monitoreo_gps_de_vehiculos_es_alta_fleetmatix(reglas):
    e = _por_familia(reglas, "Servicio de monitoreo GPS de vehículos institucionales")["gps_flotas"]

    assert (e.encaje, e.producto) == ("alta", "fleetmatix")
    assert "senales_alta: monitoreo gps" in e.regla
    assert "«monitoreo GPS» (título)" in e.evidencia  # frase exacta, con sus mayúsculas originales


@pytest.mark.parametrize("titulo", [
    "Adquisición de GPS para levantamiento topográfico",
    "Compra de cámaras de seguridad del edificio",
    "Mantenimiento del radar meteorológico",
])
def test_falsos_positivos_de_la_guia_no_son_alta(reglas, titulo):
    assert all(e.encaje != "alta" for e in evaluar_textos(reglas, titulo))


def test_exclusion_anula_y_deja_evidencia(reglas):
    e = _por_familia(reglas, "Adquisición de GPS para levantamiento topográfico")["gps_flotas"]

    assert e.encaje == "sin_coincidencia"
    assert "exclusiones: levantamiento" in e.regla and "exclusiones: topografico" in e.regla
    assert "«topográfico» (título)" in e.evidencia


# --- Normalización y búsqueda ----------------------------------------------------------

def test_normalizar_quita_mayusculas_tildes_nbsp_y_signos():
    assert normalizar("CÁMARAS  Corporales, (Body-Cam)") == "camaras corporales body cam"


def test_palabra_completa_y_plural(reglas):
    # «lora» no está dentro de «exploración»; «edificio» sí cubre «edificios».
    assert "iot_frio" not in _por_familia(reglas, "Servicio de exploración geológica")
    e = _por_familia(reglas, "Cámaras para flotilla de los edificios")
    assert e["videotelematica"].encaje == "sin_coincidencia"


def test_gana_la_coincidencia_mas_larga(reglas):
    # «control de llantas» (señal) contiene «llantas»: no se cuenta además «llantas» como exclusión.
    e = _por_familia(reglas, "Software de control de llantas")["mantenimiento_flotas"]
    assert e.encaje != "sin_coincidencia"
    assert "llantas" not in e.regla.replace("control de llantas", "")


def test_media_sola_es_baja_y_con_contexto_es_media(reglas):
    assert _por_familia(reglas, "Compra de GPS")["gps_flotas"].encaje == "baja"
    assert _por_familia(reglas, "Alquiler de GPS para la flotilla")["gps_flotas"].encaje == "media"
    assert _por_familia(reglas, "Solo para la flotilla") == {}  # el contexto solo no crea coincidencia


@pytest.mark.parametrize("titulo, esperado", [
    # Decisiones de Ivania (2026-10-09) sobre rastreo_activos y mantenimiento_flotas.
    ("Compra de GPS para contenedores", "alta"),
    ("Servicio de monitoreo de carga", "alta"),
    ("Compra de contenedores plásticos para residuos sólidos carga trasera", None),  # ni siquiera es señal
    ("Etiquetas y cintas para impresora térmica", "sin_coincidencia"),
    ("Camión para lavado de contenedores de carga lateral, con sistema hidrostático", "baja"),
])
def test_contenedores_y_carga_solo_cuentan_con_rastreo(reglas, titulo, esperado):
    e = _por_familia(reglas, titulo).get("rastreo_activos")
    assert (e.encaje if e else None) == esperado


@pytest.mark.parametrize("titulo, esperado", [
    # Decisiones de Ivania (2026-10-09) sobre gps_flotas.
    ("Servicio de rastreo GPS para la flotilla municipal", "alta"),
    ("Servicio de Monitoreo y Localización Satelital mediante el Sistema GPS", "alta"),
    ("Servicio de reparación de 9 vehículos de la flotilla vehicular", None),
    ("Reparación del sistema de monitoreo GPS de la flotilla", "sin_coincidencia"),
    ("Compra de llantas para la flotilla vehicular", None),
])
def test_talleres_de_flotilla_no_son_candidatos(reglas, titulo, esperado):
    e = _por_familia(reglas, titulo).get("gps_flotas")
    assert (e.encaje if e else None) == esperado


@pytest.mark.parametrize("titulo, familia, esperado", [
    # Decisiones de Ivania (2026-10-09).
    ("Equipos de robótica, sistemas didácticos y GPS de navegación", "gps_flotas", "sin_coincidencia"),
    ("Alquiler de GPS con navegación para la flotilla", "gps_flotas", "media"),
    ("Cámara de refrigeración para banco de sangre", "iot_frio", None),
    ("Monitoreo de temperatura de la cámara de refrigeración del banco de sangre", "iot_frio", "alta"),
    ("Termómetro de mano para control de cadena de frío", "iot_frio", "sin_coincidencia"),
    ("Termómetro de mano con pantalla LCD para cadena de frío", "iot_frio", "sin_coincidencia"),  # «de mano» manda
    ("Termómetro digital para control de cadena de frío", "iot_frio", "alta"),
    ("Compra de vacunas con monitoreo de temperatura", "iot_frio", "sin_coincidencia"),
])
def test_decisiones_navegacion_camara_de_mano_y_vacunas(reglas, titulo, familia, esperado):
    e = _por_familia(reglas, titulo).get(familia)
    assert (e.encaje if e else None) == esperado


def test_mantenimiento_preventivo_solo_sube_con_software(reglas):
    assert _por_familia(reglas, "Mantenimiento preventivo de los sistemas de bombeo")[
        "mantenimiento_flotas"].encaje == "baja"
    assert _por_familia(reglas, "Mantenimiento preventivo del sistema de software de flota")[
        "mantenimiento_flotas"].encaje == "media"


def test_señales_en_lineas_y_exclusion_por_linea(reglas):
    lineas = [Texto("línea 1", "TERMOHIGRÓMETRO CON REGISTRADOR DE DATOS"),
              Texto("línea 2", "REFRIGERADORA CON SENSORES DE TEMPERATURA")]

    e = _por_familia(reglas, "Insumos varios II", lineas)["iot_frio"]

    assert e.encaje == "alta"
    assert "(línea 1)" in e.evidencia and "línea 2" not in e.evidencia  # la línea 2 quedó excluida


def test_clave_mal_escrita_es_error(tmp_path):
    archivo = tmp_path / "reglas.yaml"
    archivo.write_text(REGLAS_MINI.replace("exclusiones", "Exlcusiones"), encoding="utf-8")

    with pytest.raises(ReglasError, match="Exlcusiones"):
        cargar_reglas(archivo)


def test_version_cambia_con_el_contenido_no_con_los_saltos_de_linea(tmp_path):
    a, b, c = tmp_path / "a.yaml", tmp_path / "b.yaml", tmp_path / "c.yaml"
    a.write_bytes(REGLAS_MINI.encode())
    b.write_bytes(REGLAS_MINI.replace("\n", "\r\n").encode())
    c.write_bytes(REGLAS_MINI.replace('"gps",', '"gps", "avl",').encode())

    assert cargar_reglas(a).version == cargar_reglas(b).version != cargar_reglas(c).version


# --- Plazo y calidad de datos (dimensiones separadas) -----------------------------------------

@pytest.mark.parametrize("cierre, esperado", [
    (None, "por_verificar"),
    ("2026-10-09T09:00:00-06:00", "vencido"),
    ("2026-10-15T09:00:00-06:00", "cierra_7_dias"),
    ("2026-11-30T09:00:00-06:00", "abierto"),
    ("2026-11-30", "por_verificar"),  # sin zona horaria
])
def test_plazo_estado(cierre, esperado):
    assert plazo_estado(cierre, AHORA) == esperado


def test_calidad_datos():
    assert calidad_datos(0, 0) == "sin_lineas"
    assert calidad_datos(3, 1) == "codigo_sin_catalogo"
    assert calidad_datos(3, 0) == "completo"


# --- Guardado en la base: idempotencia y versión de reglas ------------------------------------

@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    t = "2026-10-01T00:00:00+00:00"
    with closing(connect(path)) as conn:
        conn.executemany(
            "INSERT INTO tenders (nro_sicop, descripcion, fecha_cierre_recepcion, content_hash, first_seen, last_seen)"
            " VALUES (?, ?, ?, 'h', ?, ?)",
            [("00000000001", "Servicio de monitoreo GPS de vehículos", "2026-10-12T10:00:00-06:00", t, t),
             ("00000000002", "Adquisición de GPS para levantamiento topográfico", None, t, t),
             ("00000000003", "Insumos varios", "2026-12-01T10:00:00-06:00", t, t)],
        )
        conn.execute("INSERT INTO catalog_items (codigo_identificacion, codigo_clasificacion, nombre, first_seen,"
                     " last_seen) VALUES ('4111230100000001', '41112301', 'REGISTRADOR DE TEMPERATURA', ?, ?)", (t, t))
        conn.executemany(
            "INSERT INTO tender_lines (nro_sicop, numero_linea, codigo_identificacion, content_hash, first_seen,"
            " last_seen) VALUES ('00000000003', ?, ?, 'h', ?, ?)",
            [("1", "4111230100000001", t, t), ("2", "9999999900000001", t, t)],
        )
    return path


def _filas(path):
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("SELECT nro_sicop, familia, producto, encaje, plazo_estado, calidad_datos, rules_version,"
                            " evaluated_at FROM opportunity_assessments ORDER BY nro_sicop, familia").fetchall()


def test_evaluar_guarda_dimensiones_separadas(db, reglas):
    with closing(connect(db)) as conn:
        evaluar_base(conn, reglas, AHORA)

    filas = {(f[0], f[1]): f for f in _filas(db)}
    assert filas[("00000000001", "gps_flotas")][2:6] == ("fleetmatix", "alta", "cierra_7_dias", "sin_lineas")
    assert filas[("00000000002", "gps_flotas")][3:6] == ("sin_coincidencia", "por_verificar", "sin_lineas")
    # La señal vino de la línea con catálogo; la otra línea no une con el catálogo.
    assert filas[("00000000003", "iot_frio")][3:6] == ("alta", "abierto", "codigo_sin_catalogo")


def test_reevaluar_es_idempotente(db, reglas):
    with closing(connect(db)) as conn:
        primera = evaluar_base(conn, reglas, AHORA)
        antes = _filas(db)
        segunda = evaluar_base(conn, reglas, AHORA + timedelta(minutes=5))

    assert primera.nuevas == len(antes) > 0
    assert (segunda.nuevas, segunda.actualizadas, segunda.sin_cambios) == (0, 0, len(antes))
    assert _filas(db) == antes  # ni siquiera cambia evaluated_at


def test_otra_version_de_reglas_agrega_filas_sin_borrar_las_anteriores(db, reglas, tmp_path):
    otras = tmp_path / "reglas.yaml"
    otras.write_text(REGLAS_MINI, encoding="utf-8")
    with closing(connect(db)) as conn:
        evaluar_base(conn, reglas, AHORA)
        evaluar_base(conn, cargar_reglas(otras), AHORA)

    versiones = {f[6] for f in _filas(db)}
    assert versiones == {reglas.version, cargar_reglas(otras).version}


def test_familia_que_deja_de_coincidir_se_marca_sin_borrar(db, tmp_path):
    archivo = tmp_path / "reglas.yaml"
    archivo.write_text(REGLAS_MINI, encoding="utf-8")
    reglas = cargar_reglas(archivo)
    with closing(connect(db)) as conn:
        evaluar_base(conn, reglas, AHORA)
        conn.execute("UPDATE tenders SET descripcion = 'Compra de sillas' WHERE nro_sicop = '00000000001'")
        r = evaluar_base(conn, reglas, AHORA)

    assert r.retiradas == 1
    fila = [f for f in _filas(db) if f[0] == "00000000001"]
    assert [f[3] for f in fila] == ["sin_coincidencia"]


def test_retirar_una_familia_no_toca_las_de_otros_carteles(db, tmp_path):
    """Revisión del 2026-10-23: las previas se agrupan por cartel (antes cada cartel recorría las de toda la base)."""
    archivo = tmp_path / "reglas.yaml"
    archivo.write_text(REGLAS_MINI, encoding="utf-8")
    reglas = cargar_reglas(archivo)
    with closing(connect(db)) as conn:
        conn.execute("UPDATE tenders SET descripcion = 'Servicio de monitoreo GPS de flotilla'"
                     " WHERE nro_sicop = '00000000003'")
        evaluar_base(conn, reglas, AHORA)
        antes = {f[0]: f for f in _filas(db)}
        conn.execute("UPDATE tenders SET descripcion = 'Compra de sillas' WHERE nro_sicop = '00000000001'")
        r = evaluar_base(conn, reglas, AHORA)

    despues = {f[0]: f for f in _filas(db)}
    assert (r.retiradas, r.actualizadas, r.nuevas) == (1, 0, 0) and r.sin_cambios == len(antes) - 1
    assert despues["00000000001"][3] == "sin_coincidencia"
    assert {k: v for k, v in despues.items() if k != "00000000001"} == \
        {k: v for k, v in antes.items() if k != "00000000001"}


def test_solo_la_evaluacion_completa_queda_registrada(db, reglas):
    with closing(connect(db)) as conn:
        evaluar_base(conn, reglas, AHORA, nro_sicop="00000000001")  # un solo cartel: no deja al día lo importado
        evaluar_base(conn, reglas, AHORA + timedelta(minutes=5))
        registro = conn.execute("SELECT rules_version, evaluated_at, carteles FROM evaluation_runs").fetchall()

    assert registro == [(reglas.version, (AHORA + timedelta(minutes=5)).isoformat(timespec="seconds"), 3)]


def test_comando_evaluate(db, capsys):
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(db)})

    assert main(["evaluate"], settings) == 0
    salida = capsys.readouterr().out
    assert "Carteles evaluados: 3" in salida
    assert "00000000001 · Alta · gps_flotas (fleetmatix)" in salida

    assert main(["evaluate"], settings) == 0
    assert "nuevas 0 · actualizadas 0" in capsys.readouterr().out
