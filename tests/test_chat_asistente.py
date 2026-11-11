"""El asistente como chat (app/ai/chat.py; DECISION_IA.md §10; migración 0044).

Lista, base y usuarios SINTÉTICOS de tests/test_asistente.py. La IA es SIMULADA: nunca se llama a OpenAI ni a
Anthropic (regla 7). Lo que «contesta» la IA lo escribe cada prueba.
"""

import io
import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest

from app import asistente, seguimiento
from app.ai import chat as ia_chat
from app.ai import cliente as ia_cliente
from app.config import load_settings
from app.database import connect
from app.historial import Quien
from app.sources import sicop_documentos
from tests.test_asistente import (ANA, AHORA, NRO, PDF, _empezar, _pasos, _post, _responder, db, lista,  # noqa: F401
                                  web)


class IaSimulada:
    """Imita client.responses.create (OpenAI): devuelve, en orden, lo que se le dé, y anota cada llamada."""

    def __init__(self, *salidas):
        self.salidas, self.llamadas, self.responses = list(salidas), [], self

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        salida = self.salidas.pop(0)
        if isinstance(salida, Exception):
            raise salida
        return SimpleNamespace(status="completed", output_text=json.dumps(salida), output=[], model="modelo-simulado",
                               usage=SimpleNamespace(input_tokens=1500, output_tokens=120), incomplete_details=None)


def _r(ref, estado="respondido", valor="", vence_el="", usa_archivo=False):
    return {"ref": ref, "estado": estado, "valor": valor, "vence_el": vence_el, "usa_archivo": usa_archivo}


def _con_ia(settings, **extra):
    return load_settings(env_file=None, environ={
        **settings.raw, "AI_MODE": "openai", "OPENAI_API_KEY": "clave-SIMULADA", "OPENAI_MODEL": "modelo-simulado",
        "IA_PRECIO_ENTRADA_USD": "1.00", "IA_PRECIO_SALIDA_USD": "5.00", "IA_MAX_DAILY_COST": "5.00",
        "ASSISTANT_CHAT": "true", **extra})


def _enviar(db, settings, texto, simulado, archivo=None, quien=ANA):
    with closing(connect(db)) as conn:
        ia_chat.enviar(conn, settings, NRO, texto, archivo, quien, AHORA, cliente=simulado, dormir=lambda s: None)


def _mensajes(db):
    with closing(connect(db)) as conn:
        return ia_chat.mensajes(conn, asistente.sesion(conn, NRO).id)


def _respuesta(db, item_id):
    return next(p for p in _pasos(db) if p.item.id == item_id).respuesta


def _ampliar(db):
    with closing(connect(db)) as conn:
        asistente.ampliar(conn, NRO, ANA, AHORA)


# --- Una vuelta del chat -------------------------------------------------------------------------------------------

def test_la_ia_propone_y_la_app_guarda_con_las_reglas_de_siempre(lista):
    db, ids, settings = lista
    settings = _con_ia(settings)
    _empezar(db)
    simulado = IaSimulada({"mensaje": "Gracias por los datos.",
                           "respuestas": [_r("R1", valor="sí"), _r("R2", valor="14")]})

    _enviar(db, settings, "Sí, ofertamos por SICOP y tenemos 14 años con GPS.", simulado)

    assert _respuesta(db, ids["sicop"]).resumen == "Sí"
    assert _respuesta(db, ids["anos"]).resumen == "14 años"
    assert _respuesta(db, ids["anos"]).nota == ia_chat.NOTA                 # se sabe que vino del chat
    roles = [(m.rol, m.texto.split("\n")[0][:40]) for m in _mensajes(db)]
    assert [r for r, _ in roles] == ["app", "persona", "asistente", "app", "app"]
    assert roles[0][1].startswith("Hola. Leí los requisitos")               # la presentación, sin IA
    assert "Guardado · Ofertar por SICOP" in _mensajes(db)[3].texto           # lo confirma la app, no la IA
    assert "Ya están respondidos los requisitos excluyentes" in _mensajes(db)[4].texto
    # A la IA fue la lista, la conversación y el mensaje; nunca el perfil.
    enviado = simulado.llamadas[0]["input"]
    assert "R1 · excluyente: sí" in enviado and "MENSAJE NUEVO: Sí, ofertamos" in enviado
    assert "APP: Hola. Leí los requisitos" in enviado and "perfil" not in enviado.lower()
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT proposito, nro_sicop FROM ia_usage").fetchall() == [("chat", NRO)]


def test_un_documento_no_queda_cumplido_sin_el_archivo(lista):
    db, ids, settings = lista
    settings = _con_ia(settings)
    _empezar(db)
    _ampliar(db)
    patente = next(n for n, p in enumerate(_pasos(db), start=1) if p.item.id == ids["patente"])
    simulado = IaSimulada({"mensaje": "Entendido.", "respuestas": [_r(f"R{patente}")]})   # «ponle que sí»
    _enviar(db, settings, "Ponle que sí tenemos la patente.", simulado)
    assert _respuesta(db, ids["patente"]) is None
    assert "No se guardó «Aportar patente municipal vigente." in _mensajes(db)[-2].texto
    assert "Sube el documento" in _mensajes(db)[-2].texto


@pytest.mark.parametrize("lee", [True, False])
def test_el_archivo_se_guarda_tal_cual_y_la_ia_lee_su_texto_solo_si_se_permite(lista, monkeypatch, lee):
    db, ids, settings = lista
    settings = _con_ia(settings, ASSISTANT_SEND_DOCUMENTS="true" if lee else "false")
    monkeypatch.setattr(sicop_documentos, "extraer_texto", lambda datos, ext: sicop_documentos.Texto(
        "extraido", 1, [("", 1, "PATENTE SINTÉTICA TEXTO-DEL-ARCHIVO vence 2027-03-31")]))
    _empezar(db)
    _ampliar(db)
    patente = next(n for n, p in enumerate(_pasos(db), start=1) if p.item.id == ids["patente"])
    simulado = IaSimulada({"mensaje": "Recibido.",
                           "respuestas": [_r(f"R{patente}", vence_el="2027-03-31", usa_archivo=True)]})
    _enviar(db, settings, "Aquí va la patente.", simulado, archivo=(PDF, "patente.pdf"))

    r = _respuesta(db, ids["patente"])
    assert r.tiene_archivo and r.resumen == "patente.pdf · vence 31/03/2027"
    with closing(connect(db)) as conn:
        ruta, _ = asistente.documento(conn, settings.assistant_docs_dir, NRO, r.id)
    assert ruta.read_bytes() == PDF                                          # el archivo no cambia
    enviado = simulado.llamadas[0]["input"]
    assert "ARCHIVO: patente.pdf" in enviado
    assert ("TEXTO-DEL-ARCHIVO" in enviado) is lee
    assert any(m.archivo_nombre == "patente.pdf" and m.rol == "persona" for m in _mensajes(db))


def test_requisito_inventado_y_archivo_sin_requisito_no_se_guardan(lista):
    db, ids, settings = lista
    settings = _con_ia(settings)
    _empezar(db)
    simulado = IaSimulada({"mensaje": "¿A qué requisito corresponde el archivo?",
                           "respuestas": [_r("R9", valor="sí"), _r("R1", estado="otro")]})
    _enviar(db, settings, "Les mando esto.", simulado, archivo=(PDF, "algo.pdf"))
    assert all(p.respuesta is None for p in _pasos(db))
    assert "El archivo «algo.pdf» no se guardó" in _mensajes(db)[-2].texto
    assert not settings.assistant_docs_dir.exists()


def test_sin_presupuesto_o_si_la_ia_falla_el_mensaje_queda_y_se_avisa(lista):
    db, ids, settings = lista
    _empezar(db)
    con_tope = _con_ia(settings, IA_MAX_DAILY_COST="0.01")
    with closing(connect(db)) as conn:
        conn.execute("INSERT INTO ia_usage (creado_en, proposito, modelo, costo_estimado, moneda, duracion_s,"
                     " intentos, resultado) VALUES (?, 'resumen', 'm', '0.02', 'USD', 1, 1, 'ok')",
                     (AHORA.astimezone(ia_chat.HORA_CR).isoformat(),))
        conn.commit()
    simulado = IaSimulada()
    _enviar(db, con_tope, "Hola", simulado)
    assert simulado.llamadas == [] and "presupuesto de IA de hoy" in _mensajes(db)[-1].texto

    import httpx2
    import openai
    error = openai.AuthenticationError("clave SIMULADA mala", body=None,
                                       response=httpx2.Response(401, request=httpx2.Request("POST", "https://x.test")))
    _enviar(db, _con_ia(settings, IA_MAX_DAILY_COST="100"), "Hola otra vez", IaSimulada(error))
    assert "La IA no respondió bien (AuthenticationError 401)" in _mensajes(db)[-1].texto
    assert [m.texto for m in _mensajes(db) if m.rol == "persona"] == ["Hola", "Hola otra vez"]


def test_mensaje_vacio_y_sin_empezar_no_se_aceptan(lista):
    db, ids, settings = lista
    settings = _con_ia(settings)
    with pytest.raises(ia_chat.ChatInvalido, match="no se ha empezado"):
        _enviar(db, settings, "Hola", IaSimulada())
    _empezar(db)
    with pytest.raises(ia_chat.ChatInvalido, match="Escriba un mensaje"):
        _enviar(db, settings, "   ", IaSimulada())


def test_ya_esta_lista_cuando_todo_tiene_respuesta(lista):
    db, ids, settings = lista
    with closing(connect(db)) as conn:
        s = asistente.empezar(conn, NRO, ANA, AHORA)
        assert not ia_chat.listo(asistente.recorrido(conn, NRO, AHORA.date()), s)
    _ampliar(db)
    _responder(db, settings, ids["sicop"], valor_si_no="1")
    _responder(db, settings, ids["anos"], valor_numero="14")
    _responder(db, settings, ids["soporte"], valor_texto="Sí, 24/7")
    _responder(db, settings, ids["cierre"], estado="no_se")
    _responder(db, settings, ids["patente"], archivo=PDF)
    with closing(connect(db)) as conn:
        s, pasos = asistente.sesion(conn, NRO), asistente.recorrido(conn, NRO, AHORA.date())
        assert ia_chat.listo(pasos, s)
        assert "Ya están respondidos todos los requisitos" in ia_chat.siguiente_mensaje(pasos, s)


def test_los_mensajes_no_se_borran_ni_se_modifican(lista):
    db, ids, settings = lista
    _empezar(db)
    _enviar(db, _con_ia(settings), "Hola", IaSimulada({"mensaje": "Hola.", "respuestas": []}))
    with closing(sqlite3.connect(db)) as conn:
        for sql in ("UPDATE asistente_chat SET texto = 'otro'", "DELETE FROM asistente_chat"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


# --- En la página --------------------------------------------------------------------------------------------------

@pytest.fixture
def web_chat(web, monkeypatch):
    """La página con el chat encendido y la IA SIMULADA (crear_cliente no llega nunca a la red)."""
    for clave, valor in (("AI_MODE", "openai"), ("OPENAI_API_KEY", "clave-SIMULADA"), ("OPENAI_MODEL", "modelo-sim"),
                         ("ASSISTANT_CHAT", "true"), ("IA_MAX_DAILY_COST", "5.00")):
        monkeypatch.setenv(clave, valor)
    simulado = IaSimulada()
    monkeypatch.setattr(ia_cliente, "crear_cliente", lambda settings: simulado)
    return (*web, simulado)


def test_en_la_pagina_el_chat_reemplaza_la_pregunta_y_responde(web_chat):
    db, ids, _, c, u, simulado = web_chat
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, NRO, Quien(u["oscar"], "Oscar Sintético"), AHORA)
        seguimiento.asignar(conn, NRO, u["ivania"], Quien(u["oscar"], "Oscar Sintético"), AHORA)
        asistente.empezar(conn, NRO, ANA, AHORA)                     # sin pasar por la IA de las preguntas
    pagina = c["ivania"].get(f"/oportunidades/{NRO}").text
    assert 'id="chat"' in pagina and "Hola. Leí los requisitos" in pagina and 'name="valor_si_no"' not in pagina
    simulado.salidas.append({"mensaje": "Gracias.", "respuestas": [_r("R1", valor="sí")]})
    r = _post(c["ivania"], f"/oportunidades/{NRO}/asistente/chat", {"mensaje": "Sí ofertamos por SICOP <b>ya</b>"})
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}#chat"
    pagina = c["ivania"].get(f"/oportunidades/{NRO}").text
    assert "Sí ofertamos por SICOP &lt;b&gt;ya&lt;/b&gt;" in pagina           # escapado
    assert "Guardado · Ofertar por SICOP" in pagina and "Pregunta 2 de 2" in pagina
    # Otra encargada no entra; sin token CSRF tampoco.
    assert _post(c["ana"], f"/oportunidades/{NRO}/asistente/chat", {"mensaje": "Hola"}).status_code == 403
    assert len(simulado.llamadas) == 1


def test_con_el_chat_apagado_sigue_el_formulario_de_siempre(web):
    db, ids, _, c, u = web
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, NRO, Quien(u["oscar"], "Oscar Sintético"), AHORA)
        asistente.empezar(conn, NRO, ANA, AHORA)
    pagina = c["oscar"].get(f"/oportunidades/{NRO}").text
    assert 'id="chat"' not in pagina and 'name="valor_si_no"' in pagina
    r = _post(c["oscar"], f"/oportunidades/{NRO}/asistente/chat", {"mensaje": "Hola"})
    assert r.status_code == 400 and "El chat está apagado" in r.text
