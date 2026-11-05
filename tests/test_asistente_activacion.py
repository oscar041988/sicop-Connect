"""Asistente, lección 5: interruptor ASSISTANT_ENABLED, modo simple sin IA, registro y aviso del perfil.

Base, lista y usuarios SINTÉTICOS de tests/test_asistente.py. Nunca se llama a OpenAI.
"""

from contextlib import closing
from datetime import timedelta

from app import perfil, seguimiento
from app.config import load_settings
from app.database import connect
from app.historial import Quien
from tests.test_asistente import AHORA, ANA, NRO, _post, lista, web  # noqa: F401
from tests.test_panel import db  # noqa: F401 (fixture)


def test_por_defecto_viene_apagado():
    assert load_settings(env_file=None, environ={}).assistant_enabled is False
    assert load_settings(env_file=None, environ={"ASSISTANT_ENABLED": "true"}).assistant_enabled is True


def _seguido(db_path, u):
    with closing(connect(db_path)) as conn:
        seguimiento.abrir(conn, NRO, Quien(u["oscar"], "Oscar Sintético"), AHORA)


def test_apagado_no_aparece_y_sus_direcciones_no_responden(web, monkeypatch):
    db_path, ids, _, c, u = web
    _seguido(db_path, u)
    oscar = c["oscar"]
    assert "Lista de verificación para el asistente" in oscar.get(f"/oportunidades/{NRO}").text
    token_antes = _post(oscar, f"/oportunidades/{NRO}/asistente/empezar")              # con el asistente encendido
    assert token_antes.status_code == 303
    monkeypatch.setenv("ASSISTANT_ENABLED", "false")
    pagina = oscar.get(f"/oportunidades/{NRO}").text
    assert "Lista de verificación para el asistente" not in pagina and 'id="asistente"' not in pagina
    for ruta in (f"/oportunidades/{NRO}/verificacion", f"/oportunidades/{NRO}/asistente/resultados/1"):
        r = oscar.get(ruta)
        assert r.status_code == 404 and "ASSISTANT_ENABLED=false" in r.text
    r = _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['sicop']}/responder", {"valor_si_no": "1"})
    assert r.status_code == 404
    with closing(connect(db_path)) as conn:                                              # no se borró nada
        assert conn.execute("SELECT COUNT(*) FROM eligibility_sessions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM eligibility_answers").fetchone()[0] == 0
    monkeypatch.setenv("ASSISTANT_ENABLED", "true")                                      # se vuelve a encender
    assert _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['sicop']}/responder",
                 {"valor_si_no": "1"}).status_code == 303


def test_sin_ia_funciona_como_formulario(web):
    db_path, ids, _, c, u = web                         # el fixture web ya tiene AI_MODE=none
    _seguido(db_path, u)
    oscar = c["oscar"]
    assert _post(oscar, f"/oportunidades/{NRO}/asistente/empezar").status_code == 303
    pagina = " ".join(oscar.get(f"/oportunidades/{NRO}").text.split())
    assert "El cartel pide:" in pagina                                    # la pregunta de la app, sin la IA
    assert _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['sicop']}/responder",
                 {"valor_si_no": "1"}).status_code == 303
    assert _post(oscar, f"/oportunidades/{NRO}/asistente/resultado").status_code == 303   # resultado sin IA


def test_el_registro_lo_ve_solo_un_administrador(web):
    db_path, ids, _, c, u = web
    _seguido(db_path, u)
    oscar = c["oscar"]
    _post(oscar, f"/oportunidades/{NRO}/asistente/empezar")
    _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['sicop']}/responder", {"valor_si_no": "1"})
    assert c["ivania"].get("/asistente/registro").status_code == 403                  # encargada, no administradora
    pagina = " ".join(oscar.get("/asistente/registro").text.split())
    assert "Empezó el asistente de elegibilidad de un cartel" in pagina
    assert "Respondió una pregunta del asistente" in pagina and "Oscar Sintético" in pagina
    assert "Agregó un requisito a la lista de verificación" in pagina                   # lo de la fixture (lista)
    assert "Dio seguimiento a un cartel" not in pagina                                 # no es del asistente
    assert 'href="/asistente/registro"' in oscar.get("/oportunidades").text             # en el menú
    assert 'href="/asistente/registro"' not in c["ivania"].get("/oportunidades").text


def test_aviso_del_perfil_en_el_panel(web):
    db_path, _, settings, c, _ = web
    oscar = c["oscar"]
    assert "Perfil de Hermatix:" not in oscar.get("/oportunidades").text
    with closing(connect(db_path)) as conn:
        poliza = perfil.crear(conn, "poliza", "Póliza SINTÉTICA de riesgos", ANA, AHORA)
        vence = (perfil.hoy() + timedelta(days=10)).isoformat()
        perfil.nueva_version(conn, settings.profile_docs_dir, poliza, perfil.Datos(valor="Póliza", vence_el=vence),
                             None, 1024, ANA, AHORA)
    pagina = " ".join(oscar.get("/oportunidades").text.split())
    assert "Perfil de Hermatix:</strong> 1 elemento vencido o por vencer (Póliza SINTÉTICA de riesgos)" in pagina
    assert 'href="/perfil">Revisar el perfil' in pagina


def test_al_calcular_se_ve_el_veredicto_y_la_explicacion_esta_en_la_constancia(web):
    db_path, ids, _, c, u = web
    _seguido(db_path, u)
    oscar = c["oscar"]
    _post(oscar, f"/oportunidades/{NRO}/asistente/empezar")
    _post(oscar, f"/oportunidades/{NRO}/asistente/ampliar")
    _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['sicop']}/responder", {"valor_si_no": "0"})   # excluyente: No
    _post(oscar, f"/oportunidades/{NRO}/asistente/{ids['soporte']}/responder", {"valor_texto": "24/7"})  # → Revisar
    _post(oscar, f"/oportunidades/{NRO}/asistente/resultado")
    pagina = " ".join(oscar.get(f"/oportunidades/{NRO}").text.split())
    assert '<strong>No cumplen un requisito excluyente</strong>' in pagina
    assert "Esto es lo que falta" not in pagina                      # la explicación solo está en la constancia
    rid = pagina.split("/asistente/resultados/")[1].split("/")[0]
    base = f"/oportunidades/{NRO}/asistente/resultados/{rid}"
    botones = [pagina.index(f'class="btn p" href="{base}/explicacion">Ver explicación</a>'),
               pagina.index(f'class="btn o" href="{base}">Ver constancia</a>'),
               pagina.index(f'class="btn o" href="{base}?imprimir=1"')]
    assert botones == sorted(botones)                                       # en ese orden, uno a la par del otro
    explicacion = oscar.get(f"{base}/explicacion").text
    assert "Esto es lo que falta" in explicacion and "Detalle por requisito" not in explicacion
    constancia = oscar.get(base).text
    assert "Esto es lo que falta" in constancia and "Detalle por requisito" in constancia
    assert '<details class="respuestas-asistente cada-requisito">' in pagina           # cerrada aunque haya un Revisar
    assert "1 revisar" in pagina
