"""Corregir la oferta desde el chat (app/oferta_cambios.py; DECISION_IA.md §10, paso 4; migración 0045).

Pliego, requisitos, documentos y tarifas SINTÉTICOS de tests/test_propuesta.py: las secciones S1 a S4 son «Llamado a
cotizar», «Aspectos generales», «Requisitos de admisibilidad» y «Especificaciones técnicas» (esta, en rojo: un
requisito no cumple). La IA es SIMULADA (regla 7): nunca se llama a OpenAI ni a Anthropic.
"""

import io
import json
import sqlite3
from contextlib import closing

import pytest
from docx import Document

from app import oferta_cambios, propuesta, seguimiento
from app.ai import chat as ia_chat
from app.database import connect
from app.historial import Quien
from tests.test_chat_asistente import IaSimulada
from tests.test_propuesta import (ANA, AHORA, Impresora, OpenAISimulado, _acciones, _armar, _pliego, _requisitos,
                                  _settings, _tarifas, panel_oferta)  # noqa: F401
from tests.test_propuesta_word import _texto
from tests.test_seguimiento import NRO, _asignar, _dar_seguimiento, _id, clientes, db  # noqa: F401
from tests.test_panel import token_csrf


@pytest.fixture
def oferta(db, tmp_path):  # noqa: F811
    """Cartel con pliego, asistente respondido y la oferta armada una vez (versión 1)."""
    settings = _settings(db, tmp_path)
    _pliego(db)
    _requisitos(db, settings)
    _armar(db, settings, OpenAISimulado(), Impresora(), _tarifas(db))     # deja las secciones de la IA en caché
    return db, settings


def _base(db, settings):
    with closing(connect(db)) as conn:
        return propuesta.preparar(conn, settings, NRO, ANA, AHORA, tarifas=_tarifas(db), con_cambios=False)


def _claves(db, settings):
    base = _base(db, settings)
    return base, [oferta_cambios.clave(b) for b in oferta_cambios.secciones(base.bloques)]


def _proponer(db, cambio):
    with closing(connect(db)) as conn:
        return oferta_cambios.proponer(conn, NRO, cambio, "SINTÉTICO", None, AHORA)


def _decidir(db, settings, propuesta_id, aplicar=True):
    base = _base(db, settings)
    with closing(connect(db)) as conn:
        return oferta_cambios.decidir(conn, NRO, propuesta_id, aplicar, base.bloques, base.anexos, ANA, AHORA)


# --- Aplicar cambios -----------------------------------------------------------------------------------------------

def test_los_cambios_permitidos_se_aplican_en_orden(oferta):
    db, settings = oferta
    base, s = _claves(db, settings)
    patente = next(a for a in base.anexos if a.ruta is not None)
    cambios = [
        {"accion": "cambiar_respuesta", "seccion": s[0], "texto": "Hermatix acepta y ofrece soporte 24/7."},
        {"accion": "marcar", "seccion": s[2], "tipo": "acepta"},
        {"accion": "quitar_seccion", "seccion": s[1]},
        {"accion": "agregar_seccion", "titulo": "Nota aclaratoria", "texto": "Texto SINTÉTICO.", "antes_de": s[2]},
        {"accion": "mover_seccion", "seccion": s[2], "antes_de": s[0]},
        {"accion": "quitar_anexo", "anexo": oferta_cambios.clave_anexo(patente)},
    ]
    bloques, anexos, avisos = oferta_cambios.aplicar(base.bloques, base.anexos, cambios)
    assert avisos == []
    titulos = [b.titulo for b in oferta_cambios.secciones(bloques)]
    assert titulos == ["REQUISITOS DE ADMISIBILIDAD", "LLAMADO A COTIZAR", "Nota aclaratoria",
                       "ESPECIFICACIONES TÉCNICAS"]                         # sin «Aspectos generales»
    por_titulo = {b.titulo: b for b in bloques}
    assert por_titulo["LLAMADO A COTIZAR"].respuesta == ["Hermatix acepta y ofrece soporte 24/7."]
    assert por_titulo["REQUISITOS DE ADMISIBILIDAD"].respuesta == ["Entendemos y aceptamos lo indicado."]
    assert por_titulo["LLAMADO A COTIZAR"].texto == next(b for b in base.bloques if b.titulo == "LLAMADO A COTIZAR").texto
    assert patente.titulo not in [a.titulo for a in anexos] and [a.numero for a in anexos if a.grupo == 2] == ["2.1"]
    # Volver a poner deshace el quitar.
    _, anexos, _ = oferta_cambios.aplicar(base.bloques, base.anexos, cambios + [
        {"accion": "restaurar_anexo", "anexo": oferta_cambios.clave_anexo(patente)}])
    assert patente.titulo in [a.titulo for a in anexos]


def test_lo_que_esta_en_rojo_o_pendiente_no_se_toca_y_nada_se_pierde_en_silencio(oferta):
    db, settings = oferta
    base, s = _claves(db, settings)
    roja = s[3]                                                         # «Especificaciones técnicas»
    ficha = next(a for a in base.anexos if a.pendiente)
    cambios = [{"accion": "cambiar_respuesta", "seccion": roja, "texto": "Cumplimos."},
               {"accion": "marcar", "seccion": roja, "tipo": "cumple"},
               {"accion": "quitar_seccion", "seccion": roja},
               {"accion": "quitar_anexo", "anexo": oferta_cambios.clave_anexo(ficha)},
               {"accion": "cambiar_respuesta", "seccion": "9·seccion que ya no existe", "texto": "x"}]
    bloques, anexos, avisos = oferta_cambios.aplicar(base.bloques, base.anexos, cambios)
    assert len(avisos) == 5 and all("no se aplicó" in a for a in avisos)
    assert "está en rojo" in avisos[0] and "pendiente" in avisos[3] and "no se encontró" in avisos[4]
    assert next(b for b in bloques if b.titulo == "ESPECIFICACIONES TÉCNICAS").pendiente
    assert ficha.titulo in [a.titulo for a in anexos]
    for prohibido in ({"accion": "cambiar_precio", "texto": "10"}, {"accion": "cambiar_pliego", "texto": "x"}):
        with pytest.raises(oferta_cambios.CambioInvalido, match="nunca precios ni el pliego"):
            oferta_cambios.validar(prohibido, base.bloques, base.anexos, [])


# --- Versiones -----------------------------------------------------------------------------------------------------

def test_aplicar_crea_una_version_nueva_y_la_anterior_se_conserva(oferta):
    db, settings = oferta
    with closing(connect(db)) as conn:
        assert [v.numero for v in oferta_cambios.versiones(conn, NRO)] == [1]          # la primera vez que se armó
    _, s = _claves(db, settings)
    pid = _proponer(db, {"accion": "cambiar_respuesta", "seccion": s[0], "texto": "Respuesta SINTÉTICA nueva."})
    nueva = _decidir(db, settings, pid)
    assert nueva.numero == 2 and nueva.cambios[0]["texto"] == "Respuesta SINTÉTICA nueva."
    with closing(connect(db)) as conn:
        v1 = oferta_cambios.version(conn, NRO, 1)
        assert v1.cambios == []
        p = oferta_cambios.propuestas(conn, NRO)[0]
        assert (p.estado, p.decidido_por) == ("aplicada", "Ana Sintética")
    with pytest.raises(oferta_cambios.CambioInvalido, match="ya se decidió"):
        _decidir(db, settings, pid)
    rechazada = _proponer(db, {"accion": "quitar_seccion", "seccion": s[1]})
    assert _decidir(db, settings, rechazada, aplicar=False) is None
    assert _acciones(db, "aplicar_cambio_oferta") == 1 and _acciones(db, "rechazar_cambio_oferta") == 1
    with closing(sqlite3.connect(db)) as conn:
        for sql in ("DELETE FROM oferta_versiones", "UPDATE oferta_versiones SET descripcion = 'x'",
                    "DELETE FROM oferta_propuestas", "UPDATE oferta_propuestas SET estado = 'pendiente'"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


def test_el_pdf_y_el_word_salen_con_los_cambios_y_se_puede_pedir_una_version_anterior(oferta):
    db, settings = oferta
    _, s = _claves(db, settings)
    _decidir(db, settings, _proponer(db, {"accion": "cambiar_respuesta", "seccion": s[0],
                                          "texto": "Respuesta SINTÉTICA de la versión 2."}))
    impresora = Impresora()
    _armar(db, settings, OpenAISimulado(), impresora, _tarifas(db))
    principal = impresora.principal()
    assert "Respuesta SINTÉTICA de la versión 2." in principal and "Versión 2" in principal
    with closing(connect(db)) as conn:
        word = propuesta.armar_word(conn, settings, NRO, ANA, AHORA, tarifas=_tarifas(db))
        texto = _texto(Document(io.BytesIO(word.contenido)))
        assert "Respuesta SINTÉTICA de la versión 2." in texto and "Versión 2" in texto
        anterior = Impresora()
        propuesta.armar(conn, settings, NRO, ANA, AHORA, imprimir=anterior, tarifas=_tarifas(db), version=1)
        assert "Respuesta SINTÉTICA de la versión 2." not in anterior.principal()
        with pytest.raises(propuesta.PropuestaError, match="no tiene versión 9"):
            propuesta.armar(conn, settings, NRO, ANA, AHORA, imprimir=Impresora(), tarifas=_tarifas(db), version=9)


# --- En el chat ----------------------------------------------------------------------------------------------------

def _chat(db, settings, texto, salida):
    simulado = IaSimulada({"mensaje": "Le propongo el cambio.", "respuestas": [], **salida})
    with closing(connect(db)) as conn:
        ia_chat.enviar(conn, settings, NRO, texto, None, ANA, AHORA, cliente=simulado, dormir=lambda s: None)
        return simulado, ia_chat.mensajes(conn, ia_chat.asistente.sesion(conn, NRO).id)


def _c(accion, seccion="", texto="", anexo="", tipo="", titulo="", antes_de=""):
    return {"accion": accion, "seccion": seccion, "antes_de": antes_de, "anexo": anexo, "tipo": tipo,
            "titulo": titulo, "texto": texto}


def test_en_el_chat_la_ia_propone_y_la_oferta_no_cambia_sin_aplicar(oferta):
    db, settings = oferta
    simulado, mensajes = _chat(db, settings, "En la sección 1 que diga que damos soporte 24/7.",
                               {"cambios": [_c("cambiar_respuesta", "S1", "Brindamos soporte 24/7 (SINTÉTICO).")]})
    enviado = simulado.llamadas[0]
    assert "OFERTA ACTUAL (versión 1):" in enviado["input"] and "S4 · 4. ESPECIFICACIONES TÉCNICAS · en rojo: sí" \
        in enviado["input"]
    assert "CUANDO YA HAY UNA OFERTA" in enviado["instructions"]
    propuesto = next(m for m in mensajes if m.texto.startswith("Cambio propuesto:"))
    assert "«Brindamos soporte 24/7 (SINTÉTICO).»" in propuesto.texto
    with closing(connect(db)) as conn:
        p = oferta_cambios.propuestas(conn, NRO)[0]
        assert (p.estado, p.mensaje_id) == ("pendiente", propuesto.id)
        assert [v.numero for v in oferta_cambios.versiones(conn, NRO)] == [1]          # nada cambió todavía


def test_en_el_chat_un_cambio_que_no_se_puede_se_explica(oferta):
    db, settings = oferta
    _, mensajes = _chat(db, settings, "Ponle que cumplimos la sección 4 y bájale el precio.",
                        {"cambios": [_c("marcar", "S4", tipo="cumple"), _c("cambiar_respuesta", "S9", "x")]})
    avisos = [m.texto for m in mensajes if m.texto.startswith("Ese cambio no se puede hacer")]
    assert len(avisos) == 2 and "está en rojo" in avisos[0] and "no se encontró" in avisos[1]
    with closing(connect(db)) as conn:
        assert oferta_cambios.propuestas(conn, NRO) == []


def test_sin_oferta_todavia_la_ia_no_recibe_la_oferta(db, tmp_path):  # noqa: F811
    settings = _settings(db, tmp_path)
    _pliego(db)
    _requisitos(db, settings)
    simulado, _ = _chat(db, settings, "Hola", {"cambios": [_c("quitar_seccion", "S1")]})
    assert "OFERTA ACTUAL" not in simulado.llamadas[0]["input"]
    assert "CUANDO YA HAY UNA OFERTA" not in simulado.llamadas[0]["instructions"]
    with closing(connect(db)) as conn:
        assert oferta_cambios.propuestas(conn, NRO) == []


# --- En la página --------------------------------------------------------------------------------------------------

def test_en_la_pagina_aplicar_y_no(panel_oferta, db, tmp_path, monkeypatch):  # noqa: F811
    for clave, valor in (("ASSISTANT_CHAT", "true"), ("AI_MODE", "openai"), ("OPENAI_API_KEY", "clave-SIMULADA"),
                         ("OPENAI_MODEL", "modelo-sim"), ("ASSISTANT_ENABLED", "true")):
        monkeypatch.setenv(clave, valor)
    oscar, ana = panel_oferta["oscar"], panel_oferta["ana"]
    _dar_seguimiento(oscar)
    _asignar(oscar, _id(db, "ivania@ejemplo.test"))
    settings = _settings(db, tmp_path)
    _pliego(db)
    _requisitos(db, settings)
    _armar(db, settings, OpenAISimulado(), Impresora(), _tarifas(db))
    _, s = _claves(db, settings)
    with closing(connect(db)) as conn:
        sesion = ia_chat.asistente.sesion(conn, NRO)
        mid = ia_chat._guardar(conn, sesion.id, "app", "Cambio propuesto: SINTÉTICO", AHORA)
        aplicar = oferta_cambios.proponer(conn, NRO, {"accion": "cambiar_respuesta", "seccion": s[0],
                                                      "texto": "Texto SINTÉTICO."}, "SINTÉTICO", mid, AHORA)
        mid2 = ia_chat._guardar(conn, sesion.id, "app", "Cambio propuesto: otro SINTÉTICO", AHORA)
        rechazar = oferta_cambios.proponer(conn, NRO, {"accion": "quitar_seccion", "seccion": s[1]}, "otro", mid2,
                                           AHORA)
    pagina = oscar.get(f"/oportunidades/{NRO}").text
    assert f"/asistente/propuestas/{aplicar}/aplicar" in pagina and "Oferta · versión 1" in pagina
    token = token_csrf(pagina)
    assert ana.post(f"/oportunidades/{NRO}/asistente/propuestas/{aplicar}/aplicar",
                    data={"csrf_token": token_csrf(ana.get(f"/oportunidades/{NRO}").text)}).status_code == 403
    r = oscar.post(f"/oportunidades/{NRO}/asistente/propuestas/{aplicar}/aplicar", data={"csrf_token": token},
                   follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}#chat"
    r = oscar.post(f"/oportunidades/{NRO}/asistente/propuestas/{rechazar}/rechazar", data={"csrf_token": token},
                   follow_redirects=False)
    assert r.status_code == 303
    pagina = " ".join(oscar.get(f"/oportunidades/{NRO}").text.split())
    assert "Aplicado · versión 2: SINTÉTICO" in pagina and "No aplicado: otro" in pagina
    assert "Oferta · versión 2" in pagina and "Versiones (2)" in pagina
    r = oscar.post(f"/oportunidades/{NRO}/asistente/propuestas/{aplicar}/aplicar", data={"csrf_token": token})
    assert r.status_code == 400 and "ya se decidió" in r.text
