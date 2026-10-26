"""Espera del enlace, descarga y validación (obtención automática, lección 3) con Gmail y SICOP SIMULADOS.

La descarga corre en un Chromium real sin ventana, pero context.route responde el enlace con una página SIMULADA
que inicia la descarga de un ZIP armado aquí con los fixtures carteles_muestra.csv y lineas_muestra.csv (REALES,
públicos) y corta cualquier otra petición: nunca sale a internet. Sin Chromium instalado, las de descarga se saltan."""

import io
import shutil
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import pytest

from app.cli import main
from app.config import load_settings
from app.database import MIGRATIONS_DIR, apply_migrations
from app.importers import zip_pliegos
from app.importers.comun import HORA_CR
from app.sources import obtencion
from app.sources import sicop_browser as sb
from app.sources.gmail_reader import CorreoNoLlego, CorreoSicop, FormatoDesconocido, GmailError
from tests.test_sicop_browser import _chromium_instalado

FIXTURES = Path(__file__).parent / "fixtures"
CARTELES = (FIXTURES / "carteles_muestra.csv").read_bytes()
LINEAS = (FIXTURES / "lineas_muestra.csv").read_bytes()
PID = "99999"
ENLACE = f"https://www.sicop.go.cr/app/module/bid/public/ext-report-download?processId={PID}"
URL_ZIP = "https://www.sicop.go.cr/app/descarga-simulada.zip"
SOLICITUD = datetime(2026, 10, 22, 7, 30, tzinfo=HORA_CR)

con_chromium = pytest.mark.skipif(not _chromium_instalado(),
                                  reason="Chromium de Playwright no instalado: python -m playwright install chromium")


def _zip(carteles=CARTELES, lineas=LINEAS) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        nombres = list(zip_pliegos.ARCHIVOS)
        zf.writestr(nombres[0], carteles)
        zf.writestr(nombres[1], lineas)
    return buffer.getvalue()


class _Reloj:
    def __init__(self, inicio=SOLICITUD + timedelta(minutes=5)):
        self.t = inicio

    def __call__(self):
        return self.t


class _Lector:
    """SIMULADO: responde en orden (el último se repite)."""

    def __init__(self, *respuestas):
        self.respuestas, self.llamadas = list(respuestas), 0

    def buscar_enlace(self, desde):
        self.llamadas += 1
        r = self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]
        if isinstance(r, Exception):
            raise r
        return CorreoSicop("id-simulado", SOLICITUD + timedelta(minutes=4), "enlace", r)


class _Portal:
    """SIMULADO: la página «Espere mientras se descarga el archivo» y el archivo que descarga."""

    def __init__(self, archivo: bytes = b"", descarga: bool = True, pagina: str | None = None):
        self.archivo, self.descarga, self.pagina, self.peticiones = archivo, descarga, pagina, []

    def __call__(self, contexto):
        script = ("<script>setTimeout(() => { const a = document.createElement('a'); "
                  f"a.href = '{URL_ZIP}'; document.body.appendChild(a); a.click(); }}, 100);</script>"
                  if self.descarga else "")
        pagina = self.pagina or ("<!doctype html><html><body><p>Espere mientras se descarga el archivo</p>"
                                 f"{script}</body></html>")

        def manejar(route):
            url = route.request.url
            self.peticiones.append(url)
            if url == ENLACE:
                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=pagina)
            elif url == URL_ZIP:
                route.fulfill(status=200, body=self.archivo, headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": 'attachment; filename="reporte.zip"'})
            else:
                route.abort()
        contexto.route("**/*", manejar)


def _settings(tmp_path, **extra):
    db = tmp_path / "sicop.db"
    apply_migrations(db)
    valores = {"DATABASE_PATH": str(db), "RAW_DATA_DIR": str(tmp_path / "raw"),
               "INCOMING_DIR": str(tmp_path / "incoming"), "EXPORTS_DIR": str(tmp_path / "exports")}
    valores.update(extra)
    return load_settings(env_file=None, environ=valores)


def _solicitud(settings, estado="esperando_enlace", process_id=PID, cuando=SOLICITUD) -> int:
    """Una solicitud como la deja obtain request (lección 2)."""
    with closing(sqlite3.connect(settings.database_path)) as conn:
        sid = conn.execute("INSERT INTO solicitudes_sicop (solicitada_en, correo_enviado, estado, process_id)"
                           " VALUES (?, 1, ?, ?)", (cuando.isoformat(timespec="seconds"), estado, process_id)).lastrowid
        conn.commit()
    return sid


def _fila(settings, sid):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM solicitudes_sicop WHERE id = ?", (sid,)).fetchone())


def _sondear(settings, lector, portal=None, reloj=None):
    descargar = partial(sb.descargar, preparar_contexto=portal or _Portal(_zip()), espera_ms=3000)
    return obtencion.sondear(settings, lector, reloj=reloj or _Reloj(), descargar=descargar)


# --- Camino completo y reinicio ---------------------------------------------------------------------------

@con_chromium
def test_reinicio_a_mitad_de_la_espera_retoma_y_valida(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings)

    r1 = _sondear(settings, _Lector(CorreoNoLlego("no")))
    assert (r1.estado, r1.fallo) == ("esperando_enlace", False)
    assert "Todavía no llegó" in r1.mensaje and "19:30" in r1.mensaje  # plazo de 12 h

    # «Reinicio»: otro proceso, con objetos nuevos; solo la base recuerda en qué punto quedó.
    portal = _Portal(_zip())
    r2 = _sondear(settings, _Lector(ENLACE), portal)
    assert r2.estado == "validado" and "5 carteles y 5 líneas" in r2.mensaje
    fila = _fila(settings, sid)
    original, entrada = Path(fila["archivo_original"]), Path(fila["archivo_entrada"])
    assert original.parent == settings.raw_data_dir / "descargas"
    assert original.read_bytes() == portal.archivo  # el original tal como lo entregó «SICOP»
    assert entrada == settings.incoming_dir / f"sicop-pliegos-20261022-{sid}.zip"
    assert entrada.read_bytes() == original.read_bytes()
    assert fila["archivo_sha256"] == obtencion.sha256(entrada)
    assert fila["enlace_recibido_en"] == "2026-10-22T07:34:00-06:00"
    assert all(fila[c] for c in ("descargado_en", "validado_en", "terminada_en"))
    assert not list(settings.incoming_dir.glob("*.part"))
    assert {u for u in portal.peticiones} == {ENLACE, URL_ZIP}  # nada fuera del portal simulado

    # Un segundo sondeo no descarga de nuevo: ya no hay solicitudes abiertas.
    otro_portal, lector = _Portal(_zip()), _Lector(ENLACE)
    r3 = _sondear(settings, lector, otro_portal)
    assert r3.estado is None and otro_portal.peticiones == [] and lector.llamadas == 0


@con_chromium
def test_descargado_sin_validar_se_valida_sin_bajarlo_otra_vez(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings, estado="descargado")
    original = settings.raw_data_dir / "descargas" / "sicop-pliegos-20261022-1.zip"
    original.parent.mkdir(parents=True)
    original.write_bytes(_zip())
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.execute("UPDATE solicitudes_sicop SET archivo_original = ? WHERE id = ?", (str(original), sid))
        conn.commit()
    portal, lector = _Portal(_zip()), _Lector(ENLACE)
    assert _sondear(settings, lector, portal).estado == "validado"
    assert portal.peticiones == [] and lector.llamadas == 0


# --- Plazos y enlaces -------------------------------------------------------------------------------------

def test_si_el_enlace_no_llega_en_el_plazo_falla(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings)
    r = _sondear(settings, _Lector(CorreoNoLlego("no")), reloj=_Reloj(SOLICITUD + timedelta(hours=13)))
    assert r.fallo and "El enlace no llegó en 12 h" in r.mensaje
    assert _fila(settings, sid)["estado"] == "fallido"


def test_solicitud_a_medias_se_cierra_despues_del_plazo(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings, estado="solicitado")
    assert not _sondear(settings, _Lector(ENLACE)).fallo  # obtain request puede seguir en curso
    r = _sondear(settings, _Lector(ENLACE), reloj=_Reloj(SOLICITUD + timedelta(hours=13)))
    assert r.fallo and "quedó a medias" in r.mensaje
    assert _fila(settings, sid)["estado"] == "fallido"


def test_enlace_de_otra_solicitud_se_ignora(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings, process_id="12345")
    r = _sondear(settings, _Lector(ENLACE))
    assert not r.fallo and "otra solicitud" in r.mensaje
    assert _fila(settings, sid)["estado"] == "esperando_enlace"


def test_formato_desconocido_falla_y_gmail_caido_no_cierra(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings)
    with pytest.raises(GmailError):
        _sondear(settings, _Lector(GmailError("sin conexión")))
    assert _fila(settings, sid)["estado"] == "esperando_enlace"
    assert _sondear(settings, _Lector(FormatoDesconocido("formato raro"))).fallo
    assert _fila(settings, sid)["estado"] == "fallido"


@con_chromium
def test_enlace_que_no_descarga_es_enlace_vencido(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings)
    r = _sondear(settings, _Lector(ENLACE), _Portal(descarga=False))
    assert r.fallo and "Enlace vencido o SICOP no inició la descarga" in r.mensaje
    assert "HTTP 200 · página www.sicop.go.cr/app/module/bid/public/ext-report-download." in r.mensaje
    assert PID not in r.mensaje  # el diagnóstico no muestra el processId
    fila = _fila(settings, sid)
    assert fila["estado"] == "fallido" and Path(fila["captura"]).is_file()
    assert not settings.incoming_dir.exists() or not any(settings.incoming_dir.iterdir())


# SIMULADO: copia del texto de la página que SICOP mostró al programa el 22/10, con un ID de soporte inventado.
PAGINA_BLOQUEO = ("<!doctype html><html><body><p>No fue posible acceder a la página solicitada. Por favor, póngase en "
                  "contacto con nosotros.</p><p>ID de soporte: 00000000-1111-2222-3333-444444444444</p>"
                  "<p><a href='javascript:history.back()'>[Volver atrás]</a></p></body></html>")


@con_chromium
def test_pagina_de_bloqueo_es_control_no_automatizable(tmp_path):
    settings = _settings(tmp_path)
    sid = _solicitud(settings)
    portal = _Portal(pagina=PAGINA_BLOQUEO)
    r = _sondear(settings, _Lector(ENLACE), portal)
    assert r.fallo and "control no automatizable" in r.mensaje
    assert "00000000-1111-2222-3333-444444444444" in r.mensaje
    assert "Diagnóstico: enlace abierto a las" in r.mensaje and "HTTP 200" in r.mensaje
    assert PID not in r.mensaje
    fila = _fila(settings, sid)
    assert fila["estado"] == "fallido" and Path(fila["captura"]).is_file()
    assert portal.peticiones.count(ENLACE) == 1  # no se reintenta
    assert not settings.incoming_dir.exists() or not any(settings.incoming_dir.iterdir())


# --- Validación: un archivo raro es un FALLO, nunca «cero oportunidades» -----------------------------------

ENCABEZADO_CARTELES = CARTELES.split(b"\r\n", 1)[0] + b"\r\n"
ENCABEZADO_LINEAS = LINEAS.split(b"\r\n", 1)[0] + b"\r\n"


@con_chromium
@pytest.mark.parametrize("archivo, motivo", [
    (b"", "está vacío"),
    (b"<!doctype html><html><body>El enlace ha expirado</body></html>", "página web en vez del ZIP"),
    (_zip(carteles=b"\xef\xbb\xbfa;b;c\r\n1;2;3\r\n"), "faltan columnas"),
    (_zip(carteles=ENCABEZADO_CARTELES, lineas=ENCABEZADO_LINEAS), "no tiene filas"),
    (_zip(carteles=CARTELES[3:]), "no es UTF-8 con BOM"),
    (b"PK\x03\x04 esto no es un zip", "no es el ZIP del reporte"),
])
def test_archivo_no_valido_falla_y_no_llega_a_la_entrada(tmp_path, archivo, motivo):
    settings = _settings(tmp_path)
    sid = _solicitud(settings)
    r = _sondear(settings, _Lector(ENLACE), _Portal(archivo))
    assert r.fallo and motivo in r.mensaje
    fila = _fila(settings, sid)
    assert fila["estado"] == "fallido"
    assert Path(fila["archivo_original"]).is_file()  # se queda en descargas/ para revisarlo
    assert not settings.incoming_dir.exists() or not any(settings.incoming_dir.iterdir())


# --- Base de datos ----------------------------------------------------------------------------------------

def test_la_base_impide_dos_solicitudes_el_mismo_dia(tmp_path):
    settings = _settings(tmp_path)
    _solicitud(settings)
    with pytest.raises(sqlite3.IntegrityError):
        _solicitud(settings, cuando=SOLICITUD + timedelta(hours=2))
    _solicitud(settings, cuando=SOLICITUD + timedelta(days=1))  # otro día, sí


def test_migracion_0010_convierte_los_estados_viejos(tmp_path):
    hasta_0009 = tmp_path / "migraciones"
    hasta_0009.mkdir()
    for m in sorted(MIGRATIONS_DIR.glob("000*.sql")):
        shutil.copy(m, hasta_0009)
    db = tmp_path / "vieja.db"
    apply_migrations(db, hasta_0009)
    with closing(sqlite3.connect(db)) as conn:
        conn.executemany("INSERT INTO solicitudes_sicop (solicitada_en, correo_enviado, estado, terminada_en)"
                         " VALUES (?, ?, ?, ?)", [("2026-10-20T07:30:00-06:00", 1, "procesando", "2026-10-20T07:33"),
                                                  ("2026-10-21T07:30:00-06:00", 1, "fallo", "2026-10-21T07:41"),
                                                  ("2026-10-22T07:30:00-06:00", 0, "en_curso", None)])
        conn.commit()

    assert apply_migrations(db) == ["0010_solicitudes_estados.sql", "0011_alerta_obtencion.sql", "0012_adjudicaciones.sql", "0013_cierre_y_resumen.sql",
                                    "0014_calidad_reglas.sql", "0015_seguimiento.sql"]
    assert apply_migrations(db) == []  # repetible: la segunda vez no cambia nada
    with closing(sqlite3.connect(db)) as conn:
        filas = conn.execute("SELECT estado, esperando_enlace_en, terminada_en, alerta_estado FROM solicitudes_sicop"
                             " ORDER BY id")
        # 0011: la fallida de antes no manda alerta (ya se revisó a mano).
        assert filas.fetchall() == [("esperando_enlace", "2026-10-20T07:33", None, None),
                                    ("fallido", None, "2026-10-21T07:41", "anterior"), ("solicitado", None, None, None)]


# --- Comandos ---------------------------------------------------------------------------------------------

@con_chromium
def test_obtain_poll_y_status_sin_enlace_ni_process_id(tmp_path, monkeypatch, capsys):
    settings = _settings(tmp_path)
    _solicitud(settings)
    monkeypatch.setattr("app.cli._crear_lector", lambda s: _Lector(ENLACE))
    monkeypatch.setattr(obtencion, "sondear", partial(obtencion.sondear, reloj=_Reloj(), descargar=partial(
        sb.descargar, preparar_contexto=_Portal(_zip()), espera_ms=3000)))

    assert main(["obtain", "poll"], settings) == 0
    assert main(["obtain", "status"], settings) == 0
    salida = capsys.readouterr().out
    assert "ZIP validado y dejado en la carpeta de entrada" in salida
    assert "VALIDADO · enlace 07:34 → descargado" in salida
    assert "archivo: sicop-pliegos-20261022-1.zip (SHA-256" in salida
    assert PID not in salida and "processId" not in salida and "sicop.go.cr" not in salida


def test_obtain_poll_seguir_espera_y_termina_en_fallo(tmp_path, monkeypatch, capsys):
    settings = _settings(tmp_path)
    _solicitud(settings)
    relojes = iter([_Reloj(), _Reloj(SOLICITUD + timedelta(hours=13))])
    real = obtencion.sondear
    monkeypatch.setattr("app.cli._crear_lector", lambda s: _Lector(CorreoNoLlego("no")))
    monkeypatch.setattr(obtencion, "sondear", lambda s, lector: real(s, lector, reloj=next(relojes)))
    esperas = []
    monkeypatch.setattr("time.sleep", esperas.append)

    assert main(["obtain", "poll", "--seguir"], settings) == 1
    assert esperas == [300]  # OBTAIN_POLL_MINUTES = 5
    captura = capsys.readouterr()
    assert "Todavía no llegó" in captura.out and "FALLO · El enlace no llegó en 12 h" in captura.err


def test_obtain_poll_sin_solicitudes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.cli._crear_lector", lambda s: _Lector(ENLACE))
    assert main(["obtain", "poll"], _settings(tmp_path)) == 0
    assert "No hay ninguna solicitud abierta" in capsys.readouterr().out
