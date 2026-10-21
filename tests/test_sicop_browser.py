"""Solicitud automática en SICOP (obtención automática, lección 2) con SICOP y Gmail SIMULADOS.

Corre un Chromium real sin ventana, pero context.route responde la dirección de SICOP con la página SIMULADA
tests/fixtures/sicop_simulado.html y corta cualquier otra petición: nunca sale a internet. Si Chromium no está
instalado (python -m playwright install chromium), estas pruebas se saltan."""

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

import pytest

from app.cli import main
from app.config import load_settings
from app.database import apply_migrations
from app.importers.comun import HORA_CR
from app.sources import sicop_browser as sb
from app.sources.gmail_reader import CorreoNoLlego, CorreoSicop, FormatoDesconocido


def _chromium_instalado() -> bool:
    try:
        with sb.sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _chromium_instalado(),
                                reason="Chromium de Playwright no instalado: python -m playwright install chromium")

PLANTILLA = (Path(__file__).parent / "fixtures" / "sicop_simulado.html").read_text(encoding="utf-8")
BUZON = "licitaciones@ejemplo.test"
CODIGO = "Zq9Xw4"
PID = "99999"
INICIO = datetime(2026, 10, 22, 8, 0, tzinfo=HORA_CR)
ESPERA_MS = 3000  # en las pruebas no hace falta esperar 30 s a un botón que no existe


class _Reloj:
    """SIMULADO: el tiempo solo avanza cuando el código «duerme»."""

    def __init__(self, inicio=INICIO):
        self.t = inicio

    def __call__(self):
        return self.t

    def dormir(self, segundos):
        self.t += timedelta(seconds=segundos)


class _LectorSimulado:
    """SIMULADO: responde en orden (el último se repite). Una excepción se lanza; un texto es el código."""

    def __init__(self, *respuestas):
        self.respuestas, self.desde = list(respuestas), []

    def buscar_codigo(self, desde):
        self.desde.append(desde)
        r = self.respuestas.pop(0) if len(self.respuestas) > 1 else self.respuestas[0]
        if isinstance(r, Exception):
            raise r
        return CorreoSicop("id-simulado", desde, "codigo", r)


class _Simulacion:
    def __init__(self, variante="normal", estado_http=200):
        self.variante, self.estado_http = variante, estado_http
        self.informes, self.peticiones = {}, []

    def __call__(self, contexto):
        html = PLANTILLA.replace("__VARIANTE__", self.variante).replace("__CODIGO__", CODIGO).replace("__PID__", PID)
        contexto.expose_binding("informar", lambda _origen, que, valor: self.informes.setdefault(que, []).append(valor))

        def manejar(route):
            url = route.request.url
            self.peticiones.append(url)
            if url == sb.URL:
                route.fulfill(status=self.estado_http, content_type="text/html; charset=utf-8", body=html)
            else:
                route.abort()
        contexto.route("**/*", manejar)


def _settings(tmp_path, **extra):
    db = tmp_path / "sicop.db"
    apply_migrations(db)
    valores = {"DATABASE_PATH": str(db), "EXPORTS_DIR": str(tmp_path / "exports"), "SICOP_REQUEST_EMAIL": BUZON}
    valores.update(extra)
    return load_settings(env_file=None, environ=valores)


def _solicitar(settings, simulacion, lector, reloj=None):
    reloj = reloj or _Reloj()
    return sb.solicitar_reporte(settings, lector, reloj=reloj, dormir=reloj.dormir, preparar_contexto=simulacion,
                                espera_ms=ESPERA_MS)


def _filas(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(f) for f in conn.execute("SELECT * FROM solicitudes_sicop ORDER BY id")]


# --- Flujo completo ---------------------------------------------------------------------------------------

def test_flujo_completo_con_el_codigo_del_buzon(tmp_path):
    settings, sim = _settings(tmp_path), _Simulacion()
    lector = _LectorSimulado(CorreoNoLlego("todavía no"), CODIGO)

    r = _solicitar(settings, sim, lector)

    assert (r.codigo, r.process_id) == (CODIGO, PID)
    assert sim.informes == {"correo": [BUZON], "codigo": [CODIGO], "aceptar": ["si"]}
    assert lector.desde[0] == INICIO - sb.MARGEN_RELOJ  # solo valen correos posteriores a la solicitud
    fila = _filas(settings)[0]
    assert (fila["estado"], fila["correo_enviado"], fila["process_id"], fila["motivo"]) == ("esperando_enlace", 1, PID, None)
    assert {u.split("/")[2] for u in sim.peticiones} == {"www.sicop.go.cr"}  # nada fuera de la página simulada
    assert CODIGO not in repr(r) and PID not in repr(r)


def test_espera_a_que_se_cierre_el_otro_panel(tmp_path):
    """Observado el 2026-10-21: al abrir el reporte, el panel que estaba abierto se cierra con una animación y por un
    momento hay dos iconos CSV visibles."""
    settings, sim = _settings(tmp_path), _Simulacion("animacion")
    assert _solicitar(settings, sim, _LectorSimulado(CODIGO)).codigo == CODIGO
    assert sim.informes["correo"] == [BUZON]


def test_si_quedan_dos_csv_falla_sin_escribir_el_correo(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "ANIMACION_MS", 1000)
    settings, sim = _settings(tmp_path), _Simulacion("dos_csv")
    with pytest.raises(sb.FalloObtencion, match="Hay 2 iconos CSV visibles"):
        _solicitar(settings, sim, _LectorSimulado(CODIGO))
    assert "correo" not in sim.informes and _filas(settings)[0]["correo_enviado"] == 0


def test_sin_url_de_descarga_igual_llega_a_procesando(tmp_path):
    settings = _settings(tmp_path)
    r = _solicitar(settings, _Simulacion("sin_url"), _LectorSimulado(CODIGO))
    assert r.process_id is None
    assert _filas(settings)[0]["estado"] == "esperando_enlace"


# --- Fallos -----------------------------------------------------------------------------------------------

def test_si_no_llega_el_codigo_falla_con_captura_y_la_solicitud_cuenta(tmp_path):
    settings, reloj = _settings(tmp_path), _Reloj()
    with pytest.raises(sb.FalloObtencion, match="No llegó el correo con el código en 10 min") as exc:
        _solicitar(settings, _Simulacion(), _LectorSimulado(CorreoNoLlego("no")), reloj)
    assert reloj() - INICIO >= timedelta(minutes=10)
    assert exc.value.captura is not None and exc.value.captura.is_file()
    fila = _filas(settings)[0]
    assert (fila["estado"], fila["correo_enviado"]) == ("fallido", 1)
    assert fila["captura"] == str(exc.value.captura)

    with pytest.raises(sb.YaSolicitadoHoy):  # una sola solicitud por día
        _solicitar(settings, _Simulacion(), _LectorSimulado(CODIGO))
    assert len(_filas(settings)) == 1


def test_codigo_rechazado_es_fallo(tmp_path):
    settings, sim = _settings(tmp_path), _Simulacion("codigo_rechazado")
    with pytest.raises(sb.FalloObtencion, match="SICOP no aceptó el código"):
        _solicitar(settings, sim, _LectorSimulado(CODIGO))
    assert sim.informes["codigo"] == [CODIGO]
    assert _filas(settings)[0]["estado"] == "fallido"


def test_formato_desconocido_del_correo_es_fallo(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(sb.FalloObtencion, match="No se pudo leer el código: formato raro"):
        _solicitar(settings, _Simulacion(), _LectorSimulado(FormatoDesconocido("formato raro")))


def test_boton_cambiado_falla_antes_del_correo_y_se_puede_repetir(tmp_path):
    settings, sim = _settings(tmp_path), _Simulacion("boton_cambiado")
    with pytest.raises(sb.FalloObtencion, match="Paso «ventana del correo»: no apareció a tiempo") as exc:
        _solicitar(settings, sim, _LectorSimulado(CODIGO))
    assert exc.value.captura.is_file()
    assert "correo" not in sim.informes
    assert _filas(settings)[0]["correo_enviado"] == 0

    r = _solicitar(settings, _Simulacion(), _LectorSimulado(CODIGO))  # no contó: SICOP no mandó ningún código
    assert r.codigo == CODIGO


def test_captcha_detiene_sin_escribir_nada(tmp_path):
    settings, sim = _settings(tmp_path), _Simulacion("captcha")
    with pytest.raises(sb.FalloObtencion, match="control no automatizable") as exc:
        _solicitar(settings, sim, _LectorSimulado(CODIGO))
    assert exc.value.control
    assert sim.informes == {}
    assert _filas(settings)[0]["correo_enviado"] == 0


def test_bloqueo_http_429_es_control_no_automatizable(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(sb.FalloObtencion, match="HTTP 429") as exc:
        _solicitar(settings, _Simulacion(estado_http=429), _LectorSimulado(CODIGO))
    assert exc.value.control


def test_sin_migrar_lo_dice(tmp_path):
    settings = load_settings(env_file=None, environ={"DATABASE_PATH": str(tmp_path / "vacia.db"),
                                                     "SICOP_REQUEST_EMAIL": BUZON})
    with pytest.raises(sb.FalloObtencion, match="migrate"):
        _solicitar(settings, _Simulacion(), _LectorSimulado(CODIGO))


# --- Comando ----------------------------------------------------------------------------------------------

def _comando(monkeypatch, tmp_path, sim, lector):
    reloj = _Reloj()
    monkeypatch.setattr("app.cli._crear_lector", lambda settings: lector)
    monkeypatch.setattr(sb, "solicitar_reporte", partial(sb.solicitar_reporte, reloj=reloj, dormir=reloj.dormir,
                                                         preparar_contexto=sim, espera_ms=ESPERA_MS))
    return main(["obtain", "request"], _settings(tmp_path))


def test_obtain_request_muestra_todo_enmascarado(tmp_path, monkeypatch, capsys):
    assert _comando(monkeypatch, tmp_path, _Simulacion(), _LectorSimulado(CODIGO)) == 0
    salida = capsys.readouterr().out
    assert "código Zq**** aceptado" in salida and "processId=99***" in salida
    assert "Procesando el reporte" in salida
    assert CODIGO not in salida and PID not in salida and BUZON not in salida


def test_obtain_request_fallo_muestra_motivo_y_captura(tmp_path, monkeypatch, capsys):
    assert _comando(monkeypatch, tmp_path, _Simulacion("codigo_rechazado"), _LectorSimulado(CODIGO)) == 1
    err = capsys.readouterr().err
    assert "FALLO · SICOP no aceptó el código" in err and "Captura:" in err
    assert CODIGO not in err and BUZON not in err
