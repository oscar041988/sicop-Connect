"""La IA en uso, cambiada desde el panel (Administración → IA; pedido de Oscar el 18/11, DECISION_IA.md §11).

Todo con un Anthropic SIMULADO (nunca se llama a la red ni se gasta) y claves SIMULADAS.
"""

from contextlib import closing

import anthropic
import pytest
from fastapi.testclient import TestClient

from app import historial, ia_panel, usuarios
from app.ai import cliente
from app.config import load_settings, ruta_ia_panel
from app.database import connect
from app.historial import Quien
from app.main import app
from tests.test_ia_anthropic import AnthropicSimulado, error, respuesta
from tests.test_panel import CONTRASENA, db, iniciar_sesion, token_csrf  # noqa: F401  (db es un fixture)

CLAVE_VIEJA = "sk-ant-SIMULADA-vieja-0000000000wxyz"
CLAVE_NUEVA = "sk-ant-SIMULADA-nueva-1111111111a1b2"
ADMIN = Quien(None, "Prueba")


@pytest.fixture
def entorno(db, monkeypatch):
    """Lo que vendría del .env: OpenAI con su clave y una clave vieja de Anthropic (todo SIMULADO)."""
    for clave, valor in {"DATABASE_PATH": str(db), "AI_MODE": "openai", "OPENAI_API_KEY": "sk-SIMULADA-openai-99999999",
                         "OPENAI_MODEL": "modelo-openai-simulado", "ANTHROPIC_API_KEY": CLAVE_VIEJA,
                         "ANTHROPIC_MODEL": "", "IA_PRECIO_ENTRADA_USD": "", "IA_PRECIO_SALIDA_USD": ""}.items():
        monkeypatch.setenv(clave, valor)
    return db


def _settings(tmp_path):
    return load_settings(env_file=tmp_path / "no-existe.env")


def _cambiar(db, settings, simulado=None, **datos):
    datos = {"modo": "anthropic", "modelo": "claude-opus-5-5", "clave": "", "precio_entrada": "5",
             "precio_salida": "25", **datos}
    with closing(connect(db)) as conn:
        return ia_panel.cambiar(conn, settings, quien=ADMIN, cliente=simulado or AnthropicSimulado(respuesta()),
                                **datos)


def test_ia_env_gana_sobre_el_env_y_solo_para_la_ia(entorno, tmp_path):
    ruta_ia_panel(str(entorno)).write_text("AI_MODE=anthropic\nANTHROPIC_MODEL=claude-opus-5-5\n"
                                           "DATABASE_PATH=/otra/base.db\n", encoding="utf-8")
    s = _settings(tmp_path)
    assert (s.ai_mode, s.ia_modelo) == ("anthropic", "claude-opus-5-5")
    assert s.database_path == entorno                       # lo que no es de la IA se ignora
    sin_archivo = load_settings(env_file=None)               # las pruebas con env_file=None no lo leen
    assert sin_archivo.ai_mode == "openai"


def test_cambiar_prueba_y_guarda(entorno, tmp_path):
    simulado = AnthropicSimulado(respuesta())
    mensaje = _cambiar(entorno, _settings(tmp_path), simulado, clave=CLAVE_NUEVA)

    assert "Anthropic" in mensaje and "claude-opus-5-5" in mensaje
    assert simulado.llamadas[0]["model"] == "claude-opus-5-5"     # la prueba se hizo con lo nuevo
    s = _settings(tmp_path)
    assert (s.ai_mode, s.anthropic_model, s.anthropic_api_key) == ("anthropic", "claude-opus-5-5", CLAVE_NUEVA)
    assert (s.get("IA_PRECIO_ENTRADA_USD"), s.get("IA_PRECIO_SALIDA_USD")) == ("5", "25")
    assert s.openai_api_key == "sk-SIMULADA-openai-99999999"      # la otra IA queda igual
    with closing(connect(entorno)) as conn:
        eventos = historial.ultimos(conn, historial.DE_IA)
        assert [e.detalle for e in eventos] == ["Anthropic (Claude) · claude-opus-5-5 · clave nueva"]
        guardado = "\n".join(str(f) for f in conn.execute("SELECT * FROM audit_log").fetchall())
    assert CLAVE_NUEVA not in guardado and CLAVE_NUEVA[-12:] not in guardado


def test_sin_clave_nueva_se_queda_la_que_hay(entorno, tmp_path):
    _cambiar(entorno, _settings(tmp_path))
    assert _settings(tmp_path).anthropic_api_key == CLAVE_VIEJA
    assert "ANTHROPIC_API_KEY" not in ruta_ia_panel(str(entorno)).read_text(encoding="utf-8")


def test_si_la_prueba_falla_no_cambia_nada(entorno, tmp_path):
    fallida = AnthropicSimulado(error(anthropic.AuthenticationError, 401))
    with pytest.raises(ia_panel.CambioInvalido, match="No se guardó nada.*AuthenticationError 401"):
        _cambiar(entorno, _settings(tmp_path), fallida, clave=CLAVE_NUEVA)
    assert not ruta_ia_panel(str(entorno)).exists()
    assert _settings(tmp_path).ai_mode == "openai"


@pytest.mark.parametrize("datos, motivo", [
    ({"modo": "gemini"}, "Elija OpenAI"),
    ({"modelo": ""}, "nombre del modelo"),
    ({"modelo": "claude opus; rm"}, "nombre del modelo"),
    ({"clave": "corta"}, "no parece válida"),
    ({"clave": "sk-ant-con espacio-1234567890"}, "no parece válida"),
    ({"precio_entrada": "barato"}, "debe ser un número"),
    ({"precio_salida": "-1"}, "entre 0 y 1000"),
])
def test_datos_que_no_sirven(entorno, tmp_path, datos, motivo):
    with pytest.raises(ia_panel.CambioInvalido, match=motivo):
        _cambiar(entorno, _settings(tmp_path), **datos)
    assert not ruta_ia_panel(str(entorno)).exists()


def test_sin_clave_del_proveedor_la_pide(entorno, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(ia_panel.CambioInvalido, match="No hay clave de Anthropic"):
        _cambiar(entorno, _settings(tmp_path))


def test_apagar_no_llama_a_ninguna_ia(entorno, tmp_path):
    simulado = AnthropicSimulado()
    assert "apagada" in _cambiar(entorno, _settings(tmp_path), simulado, modo="none")
    assert simulado.llamadas == [] and _settings(tmp_path).ia_activa is False


# --- La página ------------------------------------------------------------------------------------------------

def _cliente(db, rol=usuarios.ADMIN):
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", CONTRASENA, rol)
    c = TestClient(app)
    assert iniciar_sesion(c).status_code == 303
    return c


def _enviar(c, **datos):
    token = token_csrf(c.get("/ia").text)
    datos = {"csrf_token": token, "modo": "anthropic", "modelo": "claude-opus-5-5", "clave": CLAVE_NUEVA,
             "precio_entrada": "5", "precio_salida": "25", "contrasena": CONTRASENA, **datos}
    return c.post("/ia", data=datos, follow_redirects=False)


def test_la_pagina_muestra_solo_el_final_de_la_clave(entorno):
    pagina = _cliente(entorno).get("/ia").text
    assert "OpenAI" in pagina and "modelo-openai-simulado" in pagina and "termina en …9999" in pagina
    assert "sk-SIMULADA-openai" not in pagina and CLAVE_VIEJA not in pagina and "Anthropic …wxyz" in pagina


def test_sin_la_contrasena_no_cambia_nada(entorno, monkeypatch):
    monkeypatch.setattr(cliente, "crear_cliente", lambda settings: AnthropicSimulado(respuesta()))
    r = _enviar(_cliente(entorno), contrasena="otra contraseña")
    assert r.status_code == 400 and "contraseña no es correcta" in r.text
    assert CLAVE_NUEVA not in r.text                               # la clave no vuelve al formulario
    assert not ruta_ia_panel(str(entorno)).exists()


def test_el_administrador_la_cambia(entorno, monkeypatch):
    monkeypatch.setattr(cliente, "crear_cliente", lambda settings: AnthropicSimulado(respuesta()))
    c = _cliente(entorno)
    r = _enviar(c)
    assert r.status_code == 303 and r.headers["location"] == "/ia"
    pagina = c.get("/ia").text
    assert "la app usa Anthropic (Claude) con el modelo claude-opus-5-5" in pagina
    assert "termina en …a1b2" in pagina and CLAVE_NUEVA not in pagina
    assert "Cambiada desde este panel" in pagina and "clave nueva · Ivania" in pagina


def test_si_la_prueba_falla_la_pagina_lo_dice(entorno, monkeypatch):
    monkeypatch.setattr(cliente, "crear_cliente",
                        lambda settings: AnthropicSimulado(error(anthropic.NotFoundError, 404)))
    r = _enviar(_cliente(entorno), modelo="claude-mal-escrito")
    assert r.status_code == 400 and "No se guardó nada" in r.text and "NotFoundError 404" in r.text
    assert 'value="claude-mal-escrito"' in r.text and CLAVE_NUEVA not in r.text


def test_un_encargado_no_entra(entorno):
    c = _cliente(entorno, usuarios.ENCARGADO)
    assert c.get("/ia").status_code == 403
    assert 'href="/ia"' not in c.get("/oportunidades").text
