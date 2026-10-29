"""Obtención en el servidor (2026-10-26): dos turnos por día, descarga a mano con recordatorio, la vuelta no manda
avisos (salen con el ciclo de las 8:00) y ese ciclo cuenta los ZIP subidos en el panel.

Todo SIMULADO: SICOP, Gmail, la descarga y el proveedor de correo. El ZIP lleva un cartel SINTÉTICO de GPS
(tests/test_ciclo.py) y las líneas de lineas_muestra.csv (REALES, públicas).
"""

import shutil
import sqlite3
from contextlib import closing
from datetime import timedelta
from functools import partial

import pytest

from app import ciclo
from app.config import load_settings
from app.database import MIGRATIONS_DIR, apply_migrations, connect
from app.sources import automatico, obtencion
from app.sources import sicop_browser as sb
from app.sources.gmail_reader import CorreoNoLlego
from app.web.rutas import _importar_zip_pliegos
from tests.test_automatico import ZIP_GPS, _auto, _envejecer, _Proveedor, _Reloj
from tests.test_obtencion import ENLACE, PID, SOLICITUD, _fila, _Lector, _settings, _solicitud

DOS_TURNOS = {"OBTAIN_REQUEST_HOUR": "07:30,14:00", "OBTAIN_DOWNLOAD": "manual"}
MANANA = SOLICITUD + timedelta(minutes=5)                 # 07:35
TARDE = SOLICITUD.replace(hour=14, minute=5)              # 14:05


class _SolicitarA:
    """SIMULADO: obtain request; deja la fila como la real, con la hora y el turno del reloj."""

    def __init__(self, reloj):
        self.reloj, self.llamadas = reloj, 0

    def __call__(self, settings, lector):
        self.llamadas += 1
        sid = _solicitud(settings, cuando=self.reloj(), process_id=None)
        return sb.Resultado(sid, "Zq9Xw4", None)


def _sin_descarga(*_a, **_k):
    raise AssertionError("con OBTAIN_DOWNLOAD=manual no se descarga nada")


def _vuelta(settings, reloj, solicitar, lector=None, proveedor=None, **extra):
    return automatico.vuelta(
        settings, crear_lector=lambda s: lector or _Lector(ENLACE), reloj=reloj, solicitar=solicitar,
        proveedor_alerta=(lambda s: proveedor) if proveedor else None,
        sondear=partial(obtencion.sondear, descargar=_sin_descarga), **extra)


# --- Configuración y turno --------------------------------------------------------------------------------

def test_una_o_dos_horas_y_errores_claros(tmp_path):
    assert [f"{h:%H:%M}" for h in _settings(tmp_path, OBTAIN_REQUEST_HOUR="14:00, 07:30").obtain_request_hours] \
        == ["07:30", "14:00"]
    assert [f"{h:%H:%M}" for h in load_settings(env_file=None, environ={}).obtain_request_hours] == ["07:00"]
    for valor, mensaje in (("07:00,08:00,09:00", "como máximo dos"), ("07:30,07:30", "repetida"),
                           ("7.30", "HH:MM")):
        with pytest.raises(ValueError, match=mensaje):
            load_settings(env_file=None, environ={"OBTAIN_REQUEST_HOUR": valor}).obtain_request_hours
    with pytest.raises(ValueError, match="OBTAIN_DOWNLOAD"):
        load_settings(env_file=None, environ={"OBTAIN_DOWNLOAD": "a veces"}).obtain_download
    assert load_settings(env_file=None, environ={}).obtain_download == "manual"


def test_turno_de_cada_hora(tmp_path):
    settings = _settings(tmp_path, **DOS_TURNOS)
    for hora, minuto, turno in ((6, 0, "07:30"), (8, 0, "07:30"), (13, 59, "07:30"), (14, 0, "14:00"), (19, 0, "14:00")):
        assert sb.turno_de(settings, SOLICITUD.replace(hour=hora, minute=minuto)) == turno


def test_la_base_impide_dos_solicitudes_en_el_mismo_turno(tmp_path):
    settings = _settings(tmp_path, **DOS_TURNOS)
    _solicitud(settings, cuando=MANANA)
    _solicitud(settings, cuando=TARDE)  # otro turno del mismo día: sí
    with pytest.raises(sqlite3.IntegrityError):
        _solicitud(settings, cuando=MANANA + timedelta(minutes=30))


def test_0017_conserva_las_solicitudes_de_antes(tmp_path):
    hasta_0016 = tmp_path / "hasta_0016"
    hasta_0016.mkdir()
    for archivo in sorted(MIGRATIONS_DIR.glob("00*.sql")):
        if archivo.name < "0017":
            shutil.copy(archivo, hasta_0016)
    db = tmp_path / "sicop.db"
    apply_migrations(db, hasta_0016)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("INSERT INTO solicitudes_sicop (solicitada_en, correo_enviado, estado, motivo, alerta_estado)"
                     " VALUES ('2026-10-22T08:04:38-06:00', 1, 'fallido', 'bloqueo', 'anterior')")
        conn.commit()

    assert apply_migrations(db) == ["0017_obtencion_dos_turnos.sql", "0018_fichas.sql", "0019_documentos.sql", "0020_bitacora_enriquecimiento.sql", "0021_retiro_al_cierre.sql", "0022_grabaciones_revisadas.sql", "0023_ia_usage.sql", "0024_aviso_encargado.sql", "0025_seguimiento_etapas.sql", "0026_ia_resumenes.sql"]
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT solicitada_en, turno, estado, motivo, alerta_estado FROM solicitudes_sicop"
                            ).fetchall() == [("2026-10-22T08:04:38-06:00", "", "fallido", "bloqueo", "anterior")]


# --- Dos turnos con descarga a mano ----------------------------------------------------------------------

def test_pide_en_cada_turno_no_descarga_y_manda_un_recordatorio_por_turno(tmp_path):
    settings = _auto(tmp_path, **DOS_TURNOS)
    reloj = _Reloj(MANANA)
    solicitar = _SolicitarA(reloj)

    v1 = _vuelta(settings, reloj, solicitar)
    assert not v1.fallo, v1.lineas
    assert solicitar.llamadas == 1 and _fila(settings, 1)["turno"] == "07:30"
    assert _fila(settings, 1)["estado"] == "enlace_recibido"
    texto = (settings.exports_dir / "recordatorio-obtencion-1.txt").read_text(encoding="utf-8")
    assert "descargar el reporte de las 07:30" in texto and "«Envío de reporte»" in texto
    assert "/cargar" in texto and "pliegos" in texto
    assert ENLACE not in texto and PID not in texto  # regla 7: nunca el enlace ni el processId

    reloj.t = MANANA + timedelta(minutes=15)
    v2 = _vuelta(settings, reloj, solicitar)
    assert solicitar.llamadas == 1  # una por turno
    assert any("ya tiene su enlace" in linea for linea in v2.lineas)
    assert not any("Recordatorio" in linea for linea in v2.lineas)  # no se repite

    reloj.t = TARDE
    v3 = _vuelta(settings, reloj, solicitar)
    assert solicitar.llamadas == 2 and _fila(settings, 2)["turno"] == "14:00", v3.lineas
    assert (settings.exports_dir / "recordatorio-obtencion-2.txt").is_file()


def test_si_el_enlace_de_la_manana_no_llego_se_cierra_al_pedir_el_de_la_tarde(tmp_path):
    settings = _auto(tmp_path, **DOS_TURNOS)
    reloj = _Reloj(MANANA)
    solicitar = _SolicitarA(reloj)
    sin_correo = _Lector(CorreoNoLlego("todavía no"))

    _vuelta(settings, reloj, solicitar, lector=sin_correo)
    assert _fila(settings, 1)["estado"] == "esperando_enlace"

    reloj.t = TARDE
    v = _vuelta(settings, reloj, solicitar, lector=sin_correo)
    manana = _fila(settings, 1)
    assert manana["estado"] == "fallido" and "antes de la solicitud de las 14:00" in manana["motivo"]
    assert (settings.exports_dir / "alerta-obtencion-1.txt").is_file()  # su alerta, con el plan B
    assert solicitar.llamadas == 2 and _fila(settings, 2)["estado"] == "esperando_enlace"
    assert v.fallo


def test_recordatorio_real_una_sola_vez(tmp_path):
    settings = _auto(tmp_path, NOTIFICATIONS_ENABLED="true", NOTIFICATIONS_DRY_RUN="false", **DOS_TURNOS)
    proveedor = _Proveedor()
    reloj = _Reloj(MANANA)
    solicitar = _SolicitarA(reloj)

    _vuelta(settings, reloj, solicitar, proveedor=proveedor)
    reloj.t = MANANA + timedelta(minutes=15)
    _vuelta(settings, reloj, solicitar, proveedor=proveedor)

    assert len(proveedor.enviados) == 1
    para, asunto, texto = proveedor.enviados[0]
    assert para == "licitaciones@ejemplo.test" and "descargar el reporte de las 07:30" in asunto
    assert ENLACE not in texto and _fila(settings, 1)["alerta_estado"] == "aceptada"


# --- La vuelta no manda avisos --------------------------------------------------------------------------

def test_la_vuelta_no_corre_el_ciclo_aunque_haya_un_zip(tmp_path, monkeypatch):
    settings = _auto(tmp_path, NOTIFICATIONS_ENABLED="true", NOTIFICATIONS_DRY_RUN="false", **DOS_TURNOS)
    _subido_en_el_panel(settings)
    monkeypatch.setattr(ciclo, "run_cycle", lambda *a, **k: pytest.fail("la vuelta no corre el ciclo"))

    reloj = _Reloj(MANANA)
    v = _vuelta(settings, reloj, _SolicitarA(reloj), proveedor=_Proveedor())
    assert not v.fallo, v.lineas
    assert (settings.incoming_dir / "pliegos-subido.zip").is_file()  # espera al ciclo de las 8:00


# --- Avisos después de subir el ZIP en el panel -------------------------------------------------------------

def _subido_en_el_panel(settings):
    """Como «Cargar archivo»: importa el ZIP en el momento y lo deja en la carpeta de entrada."""
    settings.incoming_dir.mkdir(parents=True, exist_ok=True)
    ruta = settings.incoming_dir / "pliegos-subido.zip"
    ruta.write_bytes(ZIP_GPS)
    with closing(connect(settings.database_path)) as conn:
        partes, error = _importar_zip_pliegos(conn, ruta, ruta.name, "real", settings.raw_data_dir)
    assert error is None and len(partes) == 2
    _envejecer(settings.incoming_dir)


def test_un_zip_subido_en_el_panel_produce_los_avisos(tmp_path):
    settings = _auto(tmp_path)
    _subido_en_el_panel(settings)

    c = ciclo.run_cycle(settings, "real", dry_run=True, ahora=TARDE)

    assert c.estado == "ok", c.error
    assert all(a.resultado == "ya_importado" and a.fuera_de_ciclo for a in c.archivos)
    assert sum(len(x) for x in c.avisos.preparados.values()) >= 1


def test_el_mismo_zip_ya_visto_por_un_ciclo_no_vuelve_a_contar(tmp_path):
    settings = _auto(tmp_path)
    settings.incoming_dir.mkdir(parents=True)
    (settings.incoming_dir / "pliegos.zip").write_bytes(ZIP_GPS)
    _envejecer(settings.incoming_dir)
    assert ciclo.run_cycle(settings, "real", dry_run=True, ahora=TARDE).estado == "ok"  # lo importa el ciclo

    (settings.incoming_dir / "copia.zip").write_bytes(ZIP_GPS)
    _envejecer(settings.incoming_dir)
    c = ciclo.run_cycle(settings, "real", dry_run=True, ahora=TARDE + timedelta(minutes=15))
    assert c.estado == "fallo" and "no llegó ningún archivo nuevo" in c.error
    assert not any(a.fuera_de_ciclo for a in c.archivos)
