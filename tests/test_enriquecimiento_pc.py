"""Fase 2 · enrich remoto: la PC consulta SICOP y manda todo al servidor (docs/ENVIO_ENRIQUECIMIENTO.md, paso 3).

El «servidor» es la app con una base temporal (carteles y evaluación SINTÉTICOS de tests/test_enriquecimiento.py);
la «PC» le habla por TransportePrueba, que pasa el cuerpo multipart que arma la PC tal cual al TestClient (así se
prueba el armado real contra el lector del servidor, sin red). SICOP es la página SIMULADA de tests/test_ficha.py.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import cli
from app.config import load_settings
from app.main import app
from app.sources import enriquecimiento as en
from app.sources import enriquecimiento_pc as pc
from app.sources.sicop_tender_detail import Consulta
from tests.test_documentos import _lista
from tests.test_enriquecimiento import _dos_abiertos, _sql, navegador
from tests.test_ficha import ESPERA_MS, GPS, HORA, SANTA_ANA, _Pausas, _Sicop

TOKEN = "TOKEN-SIMULADO-de-prueba-0123456789-abcdefghij"


class TransportePrueba:
    """Como TransporteHttp, pero hacia la app de prueba: mismo cuerpo, misma cabecera, sin red."""

    def __init__(self, token=TOKEN):
        self.cliente, self.token, self.pedidos = TestClient(app), token, []

    def post(self, ruta, cuerpo, tipo):
        self.pedidos.append(ruta)
        r = self.cliente.post(ruta, content=cuerpo, headers={"Authorization": f"Bearer {self.token}",
                                                              "Content-Type": tipo})
        return r.status_code, r.json()


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    """Servidor con GPS y Santa Ana en la cola, y la PC con su propia carpeta."""
    settings, archivos = _dos_abiertos(tmp_path / "servidor")
    for clave in ("DATABASE_PATH", "EXPORTS_DIR", "RECORDINGS_DIR", "DOCUMENTS_DIR"):
        monkeypatch.setenv(clave, settings.get(clave))
    monkeypatch.setenv("ENRICH_TOKEN", TOKEN)
    monkeypatch.setenv("ENRICH_MAX_PER_DAY", "20")
    reloj = {"ahora": HORA}
    monkeypatch.setattr(en, "_ahora", lambda: reloj["ahora"])
    pc_dir = tmp_path / "pc"
    pc_settings = load_settings(env_file=None, environ={
        "DATABASE_PATH": str(pc_dir / "sicop.db"), "RECORDINGS_DIR": str(pc_dir / "grabaciones"),
        "BROWSER_HEADLESS": "true", "ENRICH_ENABLED": "true", "ENRICH_SERVER_URL": "http://127.0.0.1:8000",
        "ENRICH_TOKEN": TOKEN})
    return settings, pc_settings, archivos, reloj


def _remoto(pc_settings, archivos, reloj, transporte=None, **extra):
    return pc.correr_remoto(pc_settings, transporte or TransportePrueba(), reloj=lambda: reloj["ahora"],
                            dormir=_Pausas(), preparar_contexto=_Sicop(archivos=archivos), espera_ms=ESPERA_MS,
                            espera_documento_ms=ESPERA_MS, **extra)


@navegador
def test_la_pc_consulta_y_el_servidor_guarda(servidor):
    settings, pc_settings, archivos, reloj = servidor
    corrida = _remoto(pc_settings, archivos, reloj)

    assert corrida.estado == "ok" and corrida.error is None
    assert [c.nro_sicop for c in corrida.consultas] == [GPS, SANTA_ANA]
    # Todo quedó en la base del SERVIDOR, con los números del servidor.
    assert _sql(settings, "SELECT origen, estado, consultados, fallos FROM enrich_runs") == [("remoto", "ok", 2, 0)]
    assert _sql(settings, "SELECT nro_sicop, resultado FROM enrich_consultas ORDER BY id") == \
        [(GPS, "nueva"), (SANTA_ANA, "nueva")]
    for nro in (GPS, SANTA_ANA):
        assert _sql(settings, "SELECT count(*) FROM tender_documents WHERE nro_sicop = ? AND estado = 'guardado'",
                    (nro,)) == [(len(_lista(nro)),)]
    assert _sql(settings, "SELECT count(*) FROM tender_document_text")[0][0] > 0
    # Las grabaciones se quedan en la PC; la base de trabajo también (solo sirve para la corrida).
    assert (pc_settings.recordings_dir / "2026-10-27" / GPS).is_dir()
    assert (pc_settings.database_path.parent / "trabajo" / "trabajo.db").is_file()
    assert not pc_settings.database_path.exists()            # la base de la PC no se tocó


@navegador
def test_al_dia_siguiente_no_vuelve_a_bajar_lo_que_el_servidor_ya_tiene(servidor):
    settings, pc_settings, archivos, reloj = servidor
    _remoto(pc_settings, archivos, reloj)
    contar = "SELECT count(*) FROM tender_documents WHERE nro_sicop = ?"
    antes = {nro: _sql(settings, contar, (nro,)) for nro in (GPS, SANTA_ANA)}
    reloj["ahora"] = HORA + timedelta(days=1)                 # al día siguiente, con sus documentos: no vuelve
    assert _remoto(pc_settings, archivos, reloj).estado == "sin_cola"
    for nro in (GPS, SANTA_ANA):                              # SICOP los modificó: vuelven a la cola
        _sql(settings, "INSERT INTO raw_snapshots (import_id, entity, natural_key, content_hash, payload, captured_at)"
                       " VALUES (1, 'cartel', ?, ?, '{}', ?)", (nro, f"modificado-{nro}",
                                                                (HORA + timedelta(hours=12)).isoformat()))
    reloj["ahora"] = HORA + timedelta(days=2)
    corrida = _remoto(pc_settings, archivos, reloj)

    assert corrida.consultas and corrida.estado == "ok"
    for respuesta in corrida.respuestas:                      # cada cartel ya estaba entero en el servidor
        assert respuesta["resultado"] == "sin_cambios"
        assert {d["estado"] for d in respuesta["documentos"]} == {"ya_guardado"}
    for c in corrida.consultas:                               # y la PC tampoco se los pidió a SICOP
        assert c.documentos and {d.estado for d in c.documentos} == {"ya_guardado"}
    for c in corrida.consultas:                               # (lo que cerró sí se borró al abrir la corrida)
        assert _sql(settings, contar, (c.nro_sicop,)) == antes[c.nro_sicop]


def test_una_consulta_sin_ficha_viaja_en_multipart(servidor):
    """Sin navegador: el multipart que arma la PC lo entiende el servidor (un CAPTCHA, sin ficha)."""
    settings, pc_settings, _, _ = servidor
    transporte = TransportePrueba()
    abierta = pc._llamar_json(transporte, f"{pc.API}/corridas", {}, _Pausas(), print)
    trabajo = pc.preparar_trabajo(pc_settings, abierta["carteles"], HORA)
    c = Consulta(GPS, "control", "SICOP mostró un CAPTCHA (SIMULADO)")
    c.grabacion, c.duracion_s, c.iniciada_en = f"2026-10-27/{GPS}/090000", 3.0, HORA.isoformat()
    from contextlib import closing
    from app.database import connect
    with closing(connect(trabajo.database_path)) as conn:
        cuerpo, tipo = pc.multipart(pc.paquete(conn, trabajo, c, es_reintento=False))
    respuesta = pc._llamar(transporte, f"{pc.API}/corridas/{abierta['corrida']}/consultas", cuerpo, tipo,
                           _Pausas(), print)
    assert respuesta["resultado"] == "control"
    assert _sql(settings, "SELECT resultado, motivo, grabacion FROM enrich_consultas") == \
        [("control", "SICOP mostró un CAPTCHA (SIMULADO)", f"2026-10-27/{GPS}/090000")]


def test_reintenta_si_el_servidor_no_responde_y_no_si_dice_que_no():
    pausas = _Pausas()

    class Secuencia:
        def __init__(self, *respuestas):
            self.respuestas = list(respuestas)

        def post(self, ruta, cuerpo, tipo):
            r = self.respuestas.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

    assert pc._llamar(Secuencia(pc.ServidorError("sin red"), (502, {}), (201, {"ok": 1})), "/x", b"", "t", pausas,
                      lambda _: None) == {"ok": 1}
    assert pausas.segundos == [10, 20]
    with pytest.raises(pc.ServidorError, match="409: ya terminó"):
        pc._llamar(Secuencia((409, {"error": "ya terminó"})), "/x", b"", "t", _Pausas(), lambda _: None)
    with pytest.raises(pc.ServidorError, match="sin red"):
        pc._llamar(Secuencia(*[pc.ServidorError("sin red")] * 3), "/x", b"", "t", _Pausas(), lambda _: None)


def test_comandos_enrich_remoto_y_enrich_run(servidor, capsys, monkeypatch):
    _, pc_settings, _, _ = servidor
    # Con ENRICH_SERVER_URL, enrich run no escribe en la base local.
    assert cli.enrich_run(pc_settings, None) == 1
    assert "enrich remoto" in capsys.readouterr().err
    # Token malo: el servidor no abre la corrida y no se abre el navegador.
    assert cli.enrich_remoto(pc_settings, None, transporte=TransportePrueba(token="malo")) == 1
    assert "401" in capsys.readouterr().err
    # Sin https (y no es 127.0.0.1): no se manda el token sin cifrar.
    inseguro = load_settings(env_file=None, environ={**pc_settings.raw, "ENRICH_SERVER_URL": "http://otro.test"})
    assert cli.enrich_remoto(inseguro, None) == 1 and "https://" in capsys.readouterr().err
    sin_token = load_settings(env_file=None, environ={**pc_settings.raw, "ENRICH_TOKEN": ""})
    assert cli.enrich_remoto(sin_token, None) == 1 and "ENRICH_TOKEN" in capsys.readouterr().err
