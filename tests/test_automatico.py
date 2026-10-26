"""Obtención automática integrada al ciclo (lección 4) con SICOP, Gmail y descarga SIMULADOS.

Nada sale de la computadora: la solicitud, el lector de Gmail, la descarga y el proveedor de correo son
SIMULADOS. El ZIP lleva un cartel SINTÉTICO de GPS (tests/test_ciclo.py), que las reglas evalúan Alta, y las
líneas de lineas_muestra.csv (REALES, públicas)."""

import os
import sqlite3
import time
from contextlib import closing
from datetime import timedelta
from functools import partial

import pytest

from app import cli, destinatarios
from app.bloqueo import CicloOcupado, bloqueo
from app.cli import main
from app.database import connect
from app.notifications import EnvioRechazado
from app.sources import automatico, obtencion
from app.sources import sicop_browser as sb
from app.sources.sicop_browser import FalloObtencion
from tests.test_ciclo import GPS, _carteles
from tests.test_obtencion import ENLACE, PID, SOLICITUD, _fila, _Lector, _settings, _solicitud, _zip

ANTES = SOLICITUD.replace(hour=6, minute=50)
DESPUES = SOLICITUD + timedelta(minutes=5)  # 07:35
ZIP_GPS = _zip(carteles=_carteles(GPS))


class _Reloj:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class _Solicitar:
    """SIMULADO: obtain request. Deja la fila como la real (esperando_enlace) o falla como la real."""

    def __init__(self, fallo: str | None = None):
        self.fallo, self.llamadas = fallo, 0

    def __call__(self, settings, lector):
        self.llamadas += 1
        sid = _solicitud(settings, estado="fallido" if self.fallo else "esperando_enlace", process_id=None)
        if self.fallo:
            with closing(sqlite3.connect(settings.database_path)) as conn:
                conn.execute("UPDATE solicitudes_sicop SET motivo = ? WHERE id = ?", (self.fallo, sid))
                conn.commit()
            raise FalloObtencion(self.fallo)
        return sb.Resultado(sid, "Zq9Xw4", None)


def _descarga_ok(url, carpeta, nombre, **_):
    """SIMULADO: la descarga de SICOP deja el ZIP de muestra."""
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_bytes(ZIP_GPS)
    return carpeta / nombre


def _descarga_bloqueada(url, carpeta, nombre, **_):
    """SIMULADO: la página de bloqueo del 22/10 (ID de soporte inventado)."""
    raise FalloObtencion("control no automatizable: la página muestra un CAPTCHA o un aviso de bloqueo (ID de "
                         "soporte de SICOP: 00000000-1111-2222-3333-444444444444). No se reintenta.", control=True)


class _Proveedor:
    """SIMULADO: el Gmail que envía."""

    def __init__(self, error=None):
        self.enviados, self.error = [], error

    def enviar(self, para, asunto, html, texto):
        if self.error:
            raise self.error
        self.enviados.append((para, asunto, texto))
        return "id-simulado"


def _auto(tmp_path, **extra):
    settings = _settings(tmp_path, SOURCE_MODE="auto", OBTAIN_ALERT_TO="licitaciones@ejemplo.test", **extra)
    with closing(connect(settings.database_path)) as conn:
        destinatarios.agregar(conn, "oscar@ejemplo.test", "Oscar")
    return settings


def _vuelta(settings, reloj, *, solicitar=None, lector=None, descargar=_descarga_ok, proveedor=None):
    return automatico.vuelta(
        settings, crear_lector=lambda s: lector or _Lector(ENLACE), reloj=reloj,
        proveedor_alerta=(lambda s: proveedor) if proveedor else None,
        solicitar=solicitar or _Solicitar(), sondear=partial(obtencion.sondear, descargar=descargar))


def _envejecer(carpeta):
    """El ciclo deja para después lo modificado hace menos de 60 s: aquí se simula que ya pasó ese minuto."""
    viejo = time.time() - 120
    for p in carpeta.iterdir():
        if p.is_file():
            os.utime(p, (viejo, viejo))


def _ciclos(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        return conn.execute("SELECT mode, status FROM source_runs WHERE kind = 'ciclo' ORDER BY id").fetchall()


# --- Modo manual y horario ---------------------------------------------------------------------------------

def test_modo_manual_no_toca_sicop_ni_gmail(tmp_path):
    settings = _settings(tmp_path)  # SOURCE_MODE=manual por defecto

    def prohibido(*_a, **_k):
        raise AssertionError("en modo manual no se toca SICOP ni Gmail")

    v = automatico.vuelta(settings, crear_lector=prohibido, solicitar=prohibido, sondear=prohibido,
                          reloj=_Reloj(DESPUES))
    assert not v.fallo and "SOURCE_MODE=manual" in v.lineas[0]
    with closing(sqlite3.connect(settings.database_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM solicitudes_sicop").fetchone() == (0,)


def test_antes_de_la_hora_no_pide_ni_abre_gmail(tmp_path):
    settings = _auto(tmp_path)
    solicitar = _Solicitar()

    def sin_gmail(_):
        raise AssertionError("antes de la hora no se abre Gmail")

    v = automatico.vuelta(settings, crear_lector=sin_gmail, solicitar=solicitar, reloj=_Reloj(ANTES))
    assert solicitar.llamadas == 0 and "Todavía no es hora" in v.lineas[0]


# --- Camino completo ---------------------------------------------------------------------------------------

def test_auto_pide_valida_y_deja_el_zip_para_el_ciclo_de_las_8(tmp_path):
    settings = _auto(tmp_path)
    solicitar = _Solicitar()

    v1 = _vuelta(settings, _Reloj(DESPUES), solicitar=solicitar)
    assert not v1.fallo and solicitar.llamadas == 1
    assert any("ZIP validado" in linea for linea in v1.lineas)

    _envejecer(settings.incoming_dir)
    v2 = _vuelta(settings, _Reloj(DESPUES + timedelta(minutes=15)), solicitar=solicitar)
    assert not v2.fallo, v2.lineas
    assert solicitar.llamadas == 1  # una por turno
    assert any("ya está validada" in linea for linea in v2.lineas)
    # La vuelta no corre el ciclo (Ivania, 2026-10-26): el ZIP espera en la carpeta al correo de las 8:00.
    assert _ciclos(settings) == []
    assert any(p.suffix == ".zip" for p in settings.incoming_dir.iterdir())


def test_con_la_solicitud_del_turno_fallida_no_pide_otra_ni_corre_el_ciclo(tmp_path):
    settings = _auto(tmp_path)
    _solicitud(settings, estado="fallido", cuando=DESPUES)  # este turno ya se pidió y falló
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.execute("UPDATE solicitudes_sicop SET alerta_estado = 'vista_previa'")
        conn.commit()
    settings.incoming_dir.mkdir(parents=True)
    (settings.incoming_dir / "Reporte de detalle pliego de condiciones.zip").write_bytes(ZIP_GPS)
    _envejecer(settings.incoming_dir)
    solicitar = _Solicitar()

    v = _vuelta(settings, _Reloj(DESPUES + timedelta(hours=1)), solicitar=solicitar)
    assert solicitar.llamadas == 0
    assert any("no se pide otra en este turno" in linea for linea in v.lineas)
    assert _ciclos(settings) == []


# --- Fallos y alerta ---------------------------------------------------------------------------------------

def test_fallo_de_la_solicitud_alerta_una_vez_y_no_pide_otra(tmp_path):
    settings = _auto(tmp_path)
    solicitar = _Solicitar(fallo="No llegó el correo con el código en 10 min.")

    v1 = _vuelta(settings, _Reloj(DESPUES), solicitar=solicitar)
    assert v1.fallo
    vista = settings.exports_dir / "alerta-obtencion-1.txt"
    texto = vista.read_text(encoding="utf-8")
    assert "No llegó el correo con el código" in texto and "pídelo a mano" in texto
    assert _fila(settings, 1)["alerta_estado"] == "vista_previa"

    v2 = _vuelta(settings, _Reloj(DESPUES + timedelta(minutes=15)), solicitar=solicitar)
    assert solicitar.llamadas == 1  # no se pide otra hoy
    assert not any("Alerta" in linea for linea in v2.lineas)  # ni se repite la alerta


def test_bloqueo_en_la_descarga_da_el_plan_b_sin_el_enlace(tmp_path):
    settings = _auto(tmp_path)
    v = _vuelta(settings, _Reloj(DESPUES), descargar=_descarga_bloqueada)
    assert v.fallo and any("control no automatizable" in linea for linea in v.lineas)
    fila = _fila(settings, 1)
    assert fila["estado"] == "fallido" and fila["enlace_recibido_en"] is not None
    texto = (settings.exports_dir / "alerta-obtencion-1.txt").read_text(encoding="utf-8")
    assert "«Envío de reporte»" in texto and "00000000-1111-2222-3333-444444444444" in texto
    assert ENLACE not in texto and PID not in texto  # regla 7: la alerta nunca lleva el enlace


def test_alerta_real_solo_con_los_avisos_habilitados_y_una_sola_vez(tmp_path):
    settings = _auto(tmp_path, NOTIFICATIONS_ENABLED="true", NOTIFICATIONS_DRY_RUN="false")
    proveedor = _Proveedor()
    solicitar = _Solicitar(fallo="control no automatizable: CAPTCHA.")

    _vuelta(settings, _Reloj(DESPUES), solicitar=solicitar, proveedor=proveedor)
    _vuelta(settings, _Reloj(DESPUES + timedelta(minutes=15)), solicitar=solicitar, proveedor=proveedor)
    assert len(proveedor.enviados) == 1
    para, asunto, _ = proveedor.enviados[0]
    assert para == "licitaciones@ejemplo.test" and "FALLO" in asunto
    assert _fila(settings, 1)["alerta_estado"] == "aceptada"
    assert not (settings.exports_dir / "alerta-obtencion-1.txt").exists()


def test_alerta_rechazada_queda_fallida_y_no_se_reintenta(tmp_path):
    settings = _auto(tmp_path, NOTIFICATIONS_ENABLED="true", NOTIFICATIONS_DRY_RUN="false")
    proveedor = _Proveedor(error=EnvioRechazado("buzón inexistente"))
    solicitar = _Solicitar(fallo="control no automatizable: CAPTCHA.")

    v = _vuelta(settings, _Reloj(DESPUES), solicitar=solicitar, proveedor=proveedor)
    assert any("Gmail la rechazó" in linea for linea in v.lineas)
    assert _fila(settings, 1)["alerta_estado"] == "fallida"
    v2 = _vuelta(settings, _Reloj(DESPUES + timedelta(minutes=15)), solicitar=solicitar, proveedor=proveedor)
    assert not any("Alerta" in linea for linea in v2.lineas)


# --- Bloqueo y comando -------------------------------------------------------------------------------------

def test_dos_vueltas_a_la_vez_no_se_cruzan(tmp_path, capsys):
    settings = _auto(tmp_path)
    with bloqueo(automatico.ruta_bloqueo(settings), "otra vuelta (SIMULADA)"):
        with pytest.raises(CicloOcupado):
            _vuelta(settings, _Reloj(DESPUES))
        assert main(["obtain", "auto"], settings=settings) == 2
    assert "Otra vuelta de obtain auto sigue en curso" in capsys.readouterr().err
    with closing(sqlite3.connect(settings.database_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM solicitudes_sicop").fetchone() == (0,)


def test_comando_en_modo_manual_no_hace_nada(tmp_path, capsys, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(cli, "_crear_lector", lambda _: pytest.fail("en modo manual no se abre Gmail"))
    assert main(["obtain", "auto"], settings=settings) == 0
    assert "SOURCE_MODE=manual" in capsys.readouterr().out


def test_source_mode_desconocido_es_error(tmp_path, capsys):
    settings = _settings(tmp_path, SOURCE_MODE="automatico")
    assert main(["obtain", "auto"], settings=settings) == 1
    assert "SOURCE_MODE debe ser manual o auto" in capsys.readouterr().err
