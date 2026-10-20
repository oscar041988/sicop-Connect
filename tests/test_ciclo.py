"""Ciclo completo (lección 8): run-cycle = recoger → importar → evaluar → avisar.

Datos SINTÉTICOS (carteles «SINTETICO …», cédula 9999999999) escritos en una carpeta temporal; las fechas son
relativas a hoy para que el plazo siga abierto. Nunca toca data/ ni envía correos: el envío usa un proveedor
SIMULADO.
"""

import io
import json
import os
import sqlite3
import subprocess
import sys
import time
import zipfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app import cli, ciclo, destinatarios
from app.bloqueo import CicloOcupado, bloqueo
from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect
from app.importers.comun import HORA_CR
from tests.test_avisos import ProveedorSimulado

ENCABEZADO = ("Número SICOP;Cédula;Fecha Publicación;Numero de procedimiento;Cod Unidad Compra;Nombre Unidad Compra;"
              "Tipo de procedimiento;Modalidad Procedimiento;Excepción CD;Descripción;Pago Adelantado Pymes;"
              "Fecha Invitación;Fecha Inicio Recepción;Fecha Cierre Recepción;Fecha Apertura")
GPS = ("20269900001", "SINTETICO monitoreo GPS de flotilla vehicular")   # Alta (Fleetmatix)
OTRO = ("20269900002", "SINTETICO compra de papel bond")                  # no coincide


HOY = datetime.now(HORA_CR).replace(microsecond=0)  # una sola vez: el mismo cartel sale idéntico en dos archivos


def _fila(nro, descripcion, cierre_dias=5):
    hoy = HOY
    publicado = (hoy - timedelta(days=1)).strftime("%d/%m/%Y %H:%M:%S")
    cierre = (hoy + timedelta(days=cierre_dias)).strftime("%d/%m/%Y %H:%M:%S")
    return ";".join([nro, "9999999999", publicado, "2026LD-999999-0099900001", "00099", "UNIDAD SINTETICA",
                     "Licitación Reducida", "Cantidad definida", "", descripcion, "N", publicado, publicado,
                     cierre, cierre])


def _carteles(*filas):
    """CSV como el del portal: UTF-8 con BOM, «;» y CRLF, terminado en salto de línea."""
    return ("﻿" + "\r\n".join([ENCABEZADO, *(_fila(*f) for f in filas)]) + "\r\n").encode("utf-8")


@pytest.fixture
def entorno(tmp_path):
    db = tmp_path / "data" / "sicop.db"
    apply_migrations(db)
    with closing(connect(db)) as conn:
        destinatarios.agregar(conn, "oscar@ejemplo.test", "Oscar")
    settings = load_settings(env_file=None, environ={
        "DATABASE_PATH": str(db), "INCOMING_DIR": str(tmp_path / "incoming"), "RAW_DATA_DIR": str(tmp_path / "raw"),
        "EXPORTS_DIR": str(tmp_path / "exports"), "APP_BASE_URL": "https://sicop.ejemplo.test/"})
    settings.incoming_dir.mkdir(parents=True)
    return settings


def _dejar(settings, nombre, contenido, hace_s=3600):
    """Deja un archivo en INCOMING_DIR como si se hubiera descargado hace `hace_s` segundos."""
    path = settings.incoming_dir / nombre
    path.write_bytes(contenido)
    antes = time.time() - hace_s
    os.utime(path, (antes, antes))
    return path


def _ciclos(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        return conn.execute("SELECT id, status, error, coverage, period_from, period_to FROM source_runs"
                            " WHERE kind = 'ciclo' ORDER BY id").fetchall()


def _outbox(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        return conn.execute("SELECT recipient, nro_sicop, status FROM notification_outbox ORDER BY id").fetchall()


def _hoy():
    return f"{datetime.now(HORA_CR):%Y-%m-%d}"


# --- Criterio de la guía ------------------------------------------------------------------------------

def test_ciclo_completo_en_dry_run(entorno, capsys):
    _dejar(entorno, "Detalle de pliegos de condiciones.csv", _carteles(GPS, OTRO))

    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 0

    salida = capsys.readouterr().out
    assert "DRY-RUN" in salida and "IMPORTADO (carteles) Detalle de pliegos de condiciones.csv" in salida
    assert "Ciclo #1: OK." in salida
    assert _outbox(entorno) == [("oscar@ejemplo.test", GPS[0], "preparado")]   # preparado, nunca enviado
    [(id_, estado, error, cobertura, desde, hasta)] = _ciclos(entorno)
    assert (estado, error) == ("ok", None)
    assert desde == hasta == (datetime.now(HORA_CR) - timedelta(days=1)).strftime("%Y-%m-%d")
    cobertura = json.loads(cobertura)
    assert cobertura["archivos"][0]["resultado"] == "importado"
    assert cobertura["avisos"]["nuevos"] == 1
    # El archivo se movió a procesados/<fecha>/ y su importación apunta a este ciclo.
    assert not (entorno.incoming_dir / "Detalle de pliegos de condiciones.csv").exists()
    assert (entorno.incoming_dir / "procesados" / _hoy() / "Detalle de pliegos de condiciones.csv").exists()
    with closing(sqlite3.connect(entorno.database_path)) as conn:
        assert conn.execute("SELECT source_run_id FROM imports").fetchall() == [(id_,)]


def test_dos_ciclos_a_la_vez_el_segundo_sale_con_mensaje_claro(entorno, capsys):
    archivo = _dejar(entorno, "carteles.csv", _carteles(GPS))

    with bloqueo(ciclo.ruta_bloqueo(entorno), "empezó 2026-10-14 08:00:00, proceso 4242"):
        assert main(["run-cycle", "--origen", "sintetico"], entorno) == 2

    error = capsys.readouterr().err
    assert "ya hay un ciclo en curso (empezó 2026-10-14 08:00:00, proceso 4242)" in error
    assert "Este no hizo nada" in error
    assert archivo.exists() and _outbox(entorno) == []   # no tocó ni la carpeta ni los avisos
    [(_, estado, motivo, *_)] = _ciclos(entorno)
    assert estado == "fallo" and motivo.startswith("otro ciclo en curso")


def test_el_bloqueo_funciona_entre_dos_procesos(entorno):
    """Como dos terminales: otro proceso de Python tiene el bloqueo."""
    lock = ciclo.ruta_bloqueo(entorno)
    codigo = ("import sys, time; from pathlib import Path; from app.bloqueo import bloqueo\n"
              "with bloqueo(Path(sys.argv[1]), 'proceso de prueba'):\n"
              "    print('listo', flush=True); time.sleep(30)\n")
    otro = subprocess.Popen([sys.executable, "-c", codigo, str(lock)], stdout=subprocess.PIPE, text=True,
                            cwd=Path(__file__).resolve().parent.parent)
    try:
        assert otro.stdout.readline().strip() == "listo"
        with pytest.raises(CicloOcupado, match="proceso de prueba"):
            ciclo.run_cycle(entorno, "sintetico")
    finally:
        otro.kill()
        otro.wait()
    # Al morir el otro proceso, el sistema suelta el bloqueo: el siguiente ciclo corre.
    _dejar(entorno, "carteles.csv", _carteles(GPS))
    assert ciclo.run_cycle(entorno, "sintetico").estado == "ok"


@pytest.mark.parametrize("nombre, contenido, motivo", [
    ("cortado.csv", _carteles(GPS, OTRO)[:-40], "termina a mitad de una fila"),
    ("ultima_fila_corta.csv", _carteles(GPS) + "20269900009;9999999999\r\n".encode(), "la última fila (línea 3) tiene 2"),
    ("vacio.csv", b"", "vacío"),
    ("otra_cosa.csv", b"nombre;edad\r\nAna;30\r\n", "no se reconoce el tipo de reporte"),
    ("catalogo.zip", b"PK\x03\x04 esto no es un zip completo", "ZIP está dañado o incompleto"),
])
def test_un_fallo_de_la_fuente_queda_registrado_y_no_se_avisa(entorno, capsys, nombre, contenido, motivo):
    _dejar(entorno, nombre, contenido)

    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 1

    salida = capsys.readouterr()
    assert f"ERROR {nombre}" in salida.out and motivo in salida.out
    assert "NO se avisó" in salida.out and "FALLO" in salida.err
    [(_, estado, error, cobertura, *_)] = _ciclos(entorno)
    assert estado == "fallo" and motivo in error
    assert json.loads(cobertura)["archivos"][0]["resultado"] == "error"
    assert _outbox(entorno) == []   # nunca «0 oportunidades»: simplemente no se avisa
    assert (entorno.incoming_dir / "con_error" / _hoy() / nombre).exists()


def test_si_un_archivo_falla_se_importa_el_resto_pero_no_se_avisa(entorno):
    _dejar(entorno, "carteles.csv", _carteles(GPS))
    _dejar(entorno, "lineas.csv", b"N\xfamero SICOP;Numero de linea\r\n2026990")   # cortado

    c = ciclo.run_cycle(entorno, "sintetico")

    assert c.estado == "fallo" and [a.resultado for a in c.archivos] == ["error", "importado"]
    assert c.avisos is None and _outbox(entorno) == []


def test_carpeta_vacia_no_es_cero_oportunidades(entorno, capsys):
    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 1

    salida = capsys.readouterr()
    assert "no llegó ningún archivo nuevo" in salida.err and "no significa que no haya compras" in salida.err
    [(_, estado, error, *_)] = _ciclos(entorno)
    assert estado == "fallo" and "no llegó ningún archivo nuevo" in error


def test_ciclo_repetido_no_duplica_avisos(entorno):
    _dejar(entorno, "carteles_1.csv", _carteles(GPS))
    assert ciclo.run_cycle(entorno, "sintetico").avisos.nuevos == 1

    # Al día siguiente llega otro archivo con el mismo cartel sin cambios y uno nuevo que no coincide.
    _dejar(entorno, "carteles_2.csv", _carteles(GPS, OTRO))
    segundo = ciclo.run_cycle(entorno, "sintetico")

    assert segundo.estado == "ok"
    assert (segundo.avisos.nuevos, segundo.avisos.ya_avisados) == (0, 1)
    assert _outbox(entorno) == [("oscar@ejemplo.test", GPS[0], "preparado")]


def test_el_mismo_archivo_otra_vez_no_cambia_nada(entorno):
    _dejar(entorno, "carteles.csv", _carteles(GPS))
    ciclo.run_cycle(entorno, "sintetico")
    copia = (entorno.incoming_dir / "procesados" / _hoy() / "carteles.csv").read_bytes()
    _dejar(entorno, "carteles.csv", copia)

    c = ciclo.run_cycle(entorno, "sintetico")

    assert [a.resultado for a in c.archivos] == ["ya_importado"]
    assert c.estado == "fallo" and "no llegó ningún archivo nuevo" in c.error
    assert len(_outbox(entorno)) == 1
    # No se pisa el primero: queda con otro nombre en procesados.
    assert (entorno.incoming_dir / "procesados" / _hoy() / "carteles (2).csv").exists()


def test_archivos_que_se_estan_copiando_o_temporales_se_dejan(entorno):
    _dejar(entorno, "carteles.csv", _carteles(GPS))
    reciente = _dejar(entorno, "recien_llegado.csv", _carteles(OTRO), hace_s=5)
    temporal = _dejar(entorno, "Detalle.csv.crdownload", b"a medias")

    c = ciclo.run_cycle(entorno, "sintetico")

    assert {a.archivo: a.resultado for a in c.archivos} == {
        "carteles.csv": "importado", "recien_llegado.csv": "en_espera", "Detalle.csv.crdownload": "ignorado"}
    assert c.estado == "ok" and reciente.exists() and temporal.exists()


def test_si_solo_hay_un_archivo_en_espera_el_mensaje_lo_dice(entorno, capsys):
    """Caso real (2026-10-13): se copió el archivo y se corrió el ciclo antes de un minuto."""
    reciente = _dejar(entorno, "Detalle de pliegos de condiciones.csv", _carteles(GPS), hace_s=5)

    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 1

    error = capsys.readouterr().err
    assert "no se importó ningún archivo nuevo: 1 en espera" in error
    assert "vuelve a correr el ciclo en un minuto" in error and "no llegó" not in error
    assert reciente.exists() and _outbox(entorno) == []


def test_un_ciclo_interrumpido_queda_como_fallo(entorno):
    with closing(connect(entorno.database_path)) as conn:
        conn.execute("INSERT INTO source_runs (started_at, mode, data_origin, status, kind)"
                     " VALUES ('2026-10-14T08:00:00-06:00', 'manual', 'sintetico', 'en_curso', 'ciclo')")
    _dejar(entorno, "carteles.csv", _carteles(GPS))
    ciclo.run_cycle(entorno, "sintetico")

    assert [(e, err) for _, e, err, *_ in _ciclos(entorno)] == [
        ("fallo", "interrumpido: el ciclo no terminó"), ("ok", None)]


# --- --send: las mismas exigencias que notify --send, con proveedor SIMULADO --------------------------

def test_send_se_niega_sin_habilitar_y_no_toca_nada(entorno, capsys, monkeypatch):
    monkeypatch.setattr(cli, "_crear_proveedor", lambda s: pytest.fail("no debe crear el proveedor"))
    archivo = _dejar(entorno, "carteles.csv", _carteles(GPS))

    assert main(["run-cycle", "--origen", "sintetico", "--send"], entorno) == 1

    assert "NOTIFICATIONS_ENABLED=true" in capsys.readouterr().err
    assert archivo.exists() and _ciclos(entorno) == []


def test_send_envia_una_vez_y_el_ciclo_siguiente_no_reenvia(entorno, capsys, monkeypatch):
    sim = ProveedorSimulado()
    monkeypatch.setattr(cli, "_crear_proveedor", lambda s: sim)
    habilitado = load_settings(env_file=None, environ={
        **{k: entorno.get(k) for k in ("DATABASE_PATH", "INCOMING_DIR", "RAW_DATA_DIR", "EXPORTS_DIR", "APP_BASE_URL")},
        "NOTIFICATIONS_ENABLED": "true", "NOTIFICATIONS_DRY_RUN": "false", "MAIL_PROVIDER": "gmail_api",
        "MAIL_FROM": "licitaciones@ejemplo.test"})
    _dejar(habilitado, "carteles_1.csv", _carteles(GPS))
    assert main(["run-cycle", "--origen", "sintetico", "--send"], habilitado) == 0
    _dejar(habilitado, "carteles_2.csv", _carteles(GPS, OTRO))
    assert main(["run-cycle", "--origen", "sintetico", "--send"], habilitado) == 0

    assert [para for para, *_ in sim.llamadas] == ["oscar@ejemplo.test"]
    assert _outbox(habilitado) == [("oscar@ejemplo.test", GPS[0], "aceptado")]
    assert "ACEPTADO" in capsys.readouterr().out


def test_zip_del_catalogo_se_reconoce(entorno, tmp_path):
    fuente = Path(__file__).parent / "fixtures" / "catalogo_identificacion_sintetico.csv"
    zip_path = tmp_path / "catalogo.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(fuente, "Codigos Identificacion.csv")

    assert ciclo.tipo_de_reporte(zip_path) == "catalogo"


# --- ZIP de pliegos tal como llega del portal (DECISION_OBTENCION.md, O4a) ----------------------------------

ENCABEZADO_LINEAS = ("Número SICOP;Numero de linea;Numero partida;Cantidad;Precio Unitario Estimado;Moneda;"
                     "Tipo Cambio USD;Código identificación")
ZIP_PLIEGOS = "Reporte de detalle pliego de condiciones.zip"


def _lineas(nro):
    return ("﻿" + "\r\n".join([ENCABEZADO_LINEAS, f"{nro};1;1;3;150000.00;CRC;;8311160200000001"]) + "\r\n"
            ).encode("utf-8")


def _zip_pliegos(miembros):
    contenido = io.BytesIO()
    with zipfile.ZipFile(contenido, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in miembros.items():
            zf.writestr(nombre, datos)
    return contenido.getvalue()


def _importaciones(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        return conn.execute("SELECT report, file_name FROM imports ORDER BY id").fetchall()


def test_zip_de_pliegos_se_importa_sin_descomprimirlo(entorno, capsys):
    _dejar(entorno, ZIP_PLIEGOS, _zip_pliegos({"Detalle de pliegos de condiciones.csv": _carteles(GPS, OTRO),
                                              "Detalles lineas.csv": _lineas(GPS[0])}))

    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 0

    salida = capsys.readouterr().out
    assert f"IMPORTADO (carteles) {ZIP_PLIEGOS} › Detalle de pliegos de condiciones.csv" in salida
    assert f"IMPORTADO (lineas) {ZIP_PLIEGOS} › Detalles lineas.csv" in salida
    # Carteles antes que líneas, con el nombre de siempre: igual que si se hubiera descomprimido a mano.
    assert _importaciones(entorno) == [("carteles", "Detalle de pliegos de condiciones.csv"),
                                       ("lineas", "Detalles lineas.csv")]
    assert _outbox(entorno) == [("oscar@ejemplo.test", GPS[0], "preparado")]
    # El ZIP se mueve entero a procesados; los CSV extraídos no quedan en la carpeta de entrada.
    assert sorted(p.name for p in entorno.incoming_dir.iterdir()) == ["procesados"]
    assert [p.name for p in (entorno.incoming_dir / "procesados" / _hoy()).iterdir()] == [ZIP_PLIEGOS]


def test_zip_de_pliegos_ya_descomprimido_a_mano_no_se_importa_dos_veces(entorno, capsys):
    carteles_csv, lineas_csv = _carteles(GPS), _lineas(GPS[0])
    _dejar(entorno, "Detalle de pliegos de condiciones.csv", carteles_csv)
    _dejar(entorno, "Detalles lineas.csv", lineas_csv)
    main(["run-cycle", "--origen", "sintetico"], entorno)
    capsys.readouterr()

    _dejar(entorno, ZIP_PLIEGOS, _zip_pliegos({"Detalle de pliegos de condiciones.csv": carteles_csv,
                                              "Detalles lineas.csv": lineas_csv}))
    main(["run-cycle", "--origen", "sintetico"], entorno)

    salida = capsys.readouterr().out
    assert salida.count("YA IMPORTADO") == 2 and len(_importaciones(entorno)) == 2


@pytest.mark.parametrize("miembros, motivo", [
    ({"Detalle de pliegos de condiciones.csv": "carteles"}, "faltan Detalles lineas.csv"),
    ({"Detalle de pliegos de condiciones.csv": "carteles", "Detalles lineas.csv": "lineas", "otro.csv": "x"},
     "sobran otro.csv"),
])
def test_zip_de_pliegos_incompleto_se_aparta_y_no_se_avisa(entorno, miembros, motivo):
    datos = {"carteles": _carteles(GPS), "lineas": _lineas(GPS[0]), "x": b"x\r\n"}
    _dejar(entorno, ZIP_PLIEGOS, _zip_pliegos({n: datos[v] for n, v in miembros.items()}))

    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 1

    [(_, estado, error, *_)] = _ciclos(entorno)
    assert estado == "fallo" and motivo in error
    assert _importaciones(entorno) == [] and _outbox(entorno) == []
    assert (entorno.incoming_dir / "con_error" / _hoy() / ZIP_PLIEGOS).exists()


def test_zip_de_pliegos_con_un_csv_cortado_se_aparta_entero(entorno):
    _dejar(entorno, ZIP_PLIEGOS, _zip_pliegos({"Detalle de pliegos de condiciones.csv": _carteles(GPS),
                                              "Detalles lineas.csv": _lineas(GPS[0])[:-10]}))

    assert main(["run-cycle", "--origen", "sintetico"], entorno) == 1

    [(_, estado, error, *_)] = _ciclos(entorno)
    assert estado == "fallo" and "termina a mitad de una fila" in error
    assert _importaciones(entorno) == []  # ninguno de los dos: el ZIP se revisa completo antes de importar
    assert (entorno.incoming_dir / "con_error" / _hoy() / ZIP_PLIEGOS).exists()
