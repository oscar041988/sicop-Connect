"""Fase 2 · el servidor recibe el enriquecimiento de la PC (docs/ENVIO_ENRIQUECIMIENTO.md, paso 2).

Base temporal de tests/test_enriquecimiento.py (carteles y evaluación SINTÉTICOS) y fichas y documentos SIMULADOS
de tests/fixtures. Sin navegador: la «PC» es el TestClient, que manda lo que la PC habría bajado de SICOP.
"""

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sources import enriquecimiento as en
from app.sources.sicop_tender_detail import copia_fiel, ficha_desde_textos
from app.web import api_enriquecimiento as api
from tests.test_documentos import _archivos, _lista
from tests.test_enriquecimiento import _base, _sql
from tests.test_ficha import GPS, HORA, SANTA_ANA, _original

TOKEN = "TOKEN-SIMULADO-de-prueba-0123456789-abcdefghij"
NOMBRES = ("busqueda", "ficha", "criterios", "impactos", "documentos", "lineas")


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    settings = _base(tmp_path)
    for clave in ("DATABASE_PATH", "EXPORTS_DIR", "RECORDINGS_DIR", "DOCUMENTS_DIR"):
        monkeypatch.setenv(clave, settings.get(clave))
    monkeypatch.setenv("ENRICH_TOKEN", TOKEN)
    monkeypatch.setenv("ENRICH_MAX_PER_DAY", "20")
    monkeypatch.setattr(en, "_ahora", lambda: HORA)          # la cola de las fichas SIMULADAS (27/10)
    return settings, TestClient(app)


def _cab(token=TOKEN):
    return {"Authorization": f"Bearer {token}"}


def _ficha(nro=GPS, **en_ficha) -> str:
    """Lo que la PC manda: las respuestas de SICOP tal cual (copia fiel), opcionalmente con campos de más."""
    textos = {n: _original(nro, n) for n in NOMBRES}
    if en_ficha:
        datos = json.loads(textos["ficha"])
        datos.update(en_ficha)
        textos["ficha"] = json.dumps(datos, ensure_ascii=False)
    return copia_fiel(ficha_desde_textos(nro, textos))


def _enviar(cliente, corrida, consulta: dict, archivos: dict[str, bytes] | None = None, token=TOKEN):
    partes = [("consulta", ("consulta.json", io.BytesIO(json.dumps(consulta).encode()), "application/json"))]
    partes += [("archivo", (nombre, io.BytesIO(datos), "application/octet-stream"))
               for nombre, datos in (archivos or {}).items()]
    return cliente.post(f"/api/enriquecimiento/corridas/{corrida}/consultas", files=partes, headers=_cab(token))


def _consulta(nro=GPS, resultado="nueva", ficha=None, **extra) -> dict:
    return {"nro_sicop": nro, "resultado": resultado, "motivo": "", "iniciada_en": HORA.isoformat(),
            "duracion_s": 12.5, "grabacion": f"2026-10-27/{nro}/090000", "es_reintento": False,
            "ficha": _ficha(nro) if ficha is None else ficha, **extra}


def test_sin_token_configurado_no_existe_y_con_token_malo_401(servidor, monkeypatch):
    _, cliente = servidor
    assert cliente.post("/api/enriquecimiento/corridas").status_code == 401                # sin cabecera
    assert cliente.post("/api/enriquecimiento/corridas", headers=_cab("otro")).status_code == 401
    assert cliente.post("/api/enriquecimiento/corridas", headers=_cab(TOKEN + "x")).status_code == 401
    monkeypatch.setenv("ENRICH_TOKEN", "")
    assert cliente.post("/api/enriquecimiento/corridas", headers=_cab()).status_code == 404
    # El resto del panel sigue pidiendo sesión.
    assert cliente.get("/oportunidades", follow_redirects=False).status_code == 303


def test_corrida_completa_guarda_ficha_documentos_y_bitacora(servidor):
    settings, cliente = servidor
    r = cliente.post("/api/enriquecimiento/corridas", headers=_cab())
    assert r.status_code == 201
    abierta = r.json()
    nros = [c["nro_sicop"] for c in abierta["carteles"]]
    assert GPS in nros and abierta["carteles"][nros.index(GPS)]["documentos_guardados"] == []
    corrida = abierta["corrida"]
    assert _sql(settings, "SELECT origen, estado, cola_json FROM enrich_runs WHERE id = ?", (corrida,)) == \
        [("remoto", "en_curso", json.dumps(nros))]

    archivos = _archivos(GPS)
    r = _enviar(cliente, corrida, _consulta(), archivos)
    assert r.status_code == 201, r.text
    hecho = r.json()
    assert hecho["resultado"] == "nueva" and {d["estado"] for d in hecho["documentos"]} == {"guardado"}
    assert _sql(settings, "SELECT count(*) FROM tender_details WHERE nro_sicop = ?", (GPS,)) == [(1,)]
    assert _sql(settings, "SELECT count(*) FROM tender_documents WHERE nro_sicop = ? AND estado = 'guardado'",
                (GPS,)) == [(len(_lista(GPS)),)]
    assert _sql(settings, "SELECT count(*) FROM tender_document_text x JOIN tender_documents d ON d.id ="
                " x.documento_id WHERE d.nro_sicop = ?", (GPS,))[0][0] > 0               # el texto de los PDF
    assert _sql(settings, "SELECT run_id, resultado, grabacion, documentos_guardados FROM enrich_consultas") == \
        [(corrida, "nueva", f"2026-10-27/{GPS}/090000", len(_lista(GPS)))]
    for (ruta,) in _sql(settings, "SELECT ruta_local FROM tender_documents WHERE estado = 'guardado'"):
        assert (settings.documents_dir / ruta).is_file()

    # Repetir el mismo envío no duplica: la ficha es la misma y los archivos ya están.
    otra = _enviar(cliente, corrida, _consulta(), archivos).json()
    assert otra["resultado"] == "sin_cambios" and {d["estado"] for d in otra["documentos"]} == {"ya_guardado"}
    assert _sql(settings, "SELECT count(*) FROM tender_documents WHERE nro_sicop = ?", (GPS,)) == \
        [(len(_lista(GPS)),)]

    r = cliente.post(f"/api/enriquecimiento/corridas/{corrida}/cierre", json={"estado": "ok"}, headers=_cab())
    assert r.status_code == 200 and r.json()["consultados"] == 2
    assert _sql(settings, "SELECT estado, consultados, fallos FROM enrich_runs WHERE id = ?", (corrida,)) == \
        [("ok", 2, 0)]
    assert _enviar(cliente, corrida, _consulta(), {}).status_code == 409                   # ya cerrada


def test_la_siguiente_corrida_dice_que_documentos_ya_tiene_el_servidor(servidor):
    _, cliente = servidor
    corrida = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()["corrida"]
    _enviar(cliente, corrida, _consulta(), _archivos(GPS))
    # La primera queda abierta (la PC se apagó): la nueva la cierra como detenida.
    nueva = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()
    assert GPS not in [c["nro_sicop"] for c in nueva["carteles"]]       # ya consultado hoy
    settings = servidor[0]
    assert _sql(settings, "SELECT estado, motivo FROM enrich_runs WHERE id = ?", (corrida,)) == \
        [("detenida", "la PC no cerró la corrida")]


def test_documento_que_la_pc_no_bajo_queda_con_su_motivo(servidor):
    settings, cliente = servidor
    corrida = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()["corrida"]
    archivos = _archivos(GPS)
    faltante = next(iter(archivos))
    del archivos[faltante]
    r = _enviar(cliente, corrida, _consulta(documentos={faltante: {"estado": "fallo", "motivo": "el archivo no"
                                                                    " llegó en 60 s"}}), archivos)
    assert r.status_code == 201
    assert _sql(settings, "SELECT estado, motivo FROM tender_documents WHERE server_file = ?", (faltante,)) == \
        [("fallo", "el archivo no llegó en 60 s")]


def test_solo_carteles_de_la_cola_y_ficha_del_mismo_cartel(servidor):
    _, cliente = servidor
    corrida = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()["corrida"]
    assert _enviar(cliente, corrida, _consulta(nro="20260000099", ficha="{}")).status_code == 403
    r = _enviar(cliente, corrida, _consulta(nro=GPS, ficha=_ficha(SANTA_ANA)))
    assert r.status_code == 400 and "otro cartel" in r.json()["error"]
    assert _enviar(cliente, corrida, _consulta(resultado="inventado")).status_code == 400
    assert _enviar(cliente, corrida, _consulta(resultado="nueva", ficha="")).status_code == 400
    assert _enviar(cliente, 999, _consulta()).status_code == 404
    assert _enviar(cliente, corrida, _consulta(), token="malo").status_code == 401


def test_un_fallo_sin_ficha_queda_en_la_bitacora(servidor):
    settings, cliente = servidor
    corrida = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()["corrida"]
    r = _enviar(cliente, corrida, _consulta(resultado="control", ficha="", motivo="SICOP mostró un CAPTCHA"))
    assert r.status_code == 201 and r.json()["resultado"] == "control"
    cliente.post(f"/api/enriquecimiento/corridas/{corrida}/cierre",
                 json={"estado": "detenida", "motivo": "CAPTCHA"}, headers=_cab())
    assert _sql(settings, "SELECT estado, fallos, motivo FROM enrich_runs WHERE id = ?", (corrida,)) == \
        [("detenida", 1, "CAPTCHA")]
    assert _sql(settings, "SELECT count(*) FROM tender_details") == [(0,)]


def test_el_servidor_vuelve_a_quitar_los_datos_de_personas(servidor):
    settings, cliente = servidor
    corrida = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()["corrida"]
    # Una PC vieja o alterada que no los quitó: el servidor los quita igual.
    ficha = json.loads(_ficha())
    ficha["ficha"]["executorNm"] = "PERSONA SIMULADA"
    r = _enviar(cliente, corrida, _consulta(ficha=json.dumps(ficha, ensure_ascii=False)), _archivos(GPS))
    assert r.status_code == 201
    [(copia, quitados)] = _sql(settings, "SELECT copia_fiel, campos_quitados FROM tender_details")
    assert "PERSONA SIMULADA" not in copia and "executorNm" in quitados


def test_envio_que_pasa_el_tope_se_rechaza(servidor, monkeypatch):
    settings, cliente = servidor
    corrida = cliente.post("/api/enriquecimiento/corridas", headers=_cab()).json()["corrida"]
    monkeypatch.setattr(api, "tope_bytes", lambda settings: 100)
    r = _enviar(cliente, corrida, _consulta(), _archivos(GPS))
    assert r.status_code == 413
    assert _sql(settings, "SELECT count(*) FROM tender_details") == [(0,)]
