"""Cliente de la IA con AI_MODE=anthropic (DECISION_IA.md §8) con un Anthropic SIMULADO: nunca se llama a la red ni
se gasta.

Las respuestas son objetos simulados con los campos que usa la app; los errores son las clases reales del SDK
(anthropic 2.8.0), armadas con respuestas HTTP SIMULADAS. La clave es SIMULADA.
"""

import sqlite3
import sys
from contextlib import closing
from decimal import Decimal
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.ai import cliente
from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect

CLAVE = "sk-ant-SIMULADA-no-es-real-1234567890"
TEXTO = "EXPEDIENTE SIMULADO: monitoreo GPS de 10 vehículos, texto que nunca debe guardarse"
RESPUESTA = "RESUMEN SIMULADO que tampoco debe guardarse"
PETICION = httpx2.Request("POST", "https://api.anthropic.example/v1/messages")
FORMATO = {"type": "json_schema", "name": "prueba", "strict": True,
           "schema": {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"],
                      "additionalProperties": False}}


class AnthropicSimulado:
    """Imita client.messages.create: devuelve o lanza, en orden, lo que se le dé. Anota cada llamada."""

    def __init__(self, *efectos):
        self.efectos, self.llamadas, self.messages = list(efectos), [], self

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        efecto = self.efectos.pop(0)
        if isinstance(efecto, Exception):
            raise efecto
        return efecto


def respuesta(stop_reason="end_turn", entrada=1200, salida=300, cache_leida=0, cache_escrita=0):
    # Un bloque de razonamiento (sin texto visible) antes del texto, como con el razonamiento adaptativo.
    return SimpleNamespace(stop_reason=stop_reason, model="modelo-anthropic-simulado",
                           content=[SimpleNamespace(type="thinking", thinking=""),
                                    SimpleNamespace(type="text", text=RESPUESTA)],
                           usage=SimpleNamespace(input_tokens=entrada, output_tokens=salida,
                                                 cache_read_input_tokens=cache_leida,
                                                 cache_creation_input_tokens=cache_escrita))


def error(clase, estado):
    # El mensaje podría traer parte de la clave: por eso nunca se guarda ni se muestra.
    return clase(f"invalid x-api-key {CLAVE[:12]}***", response=httpx2.Response(estado, request=PETICION), body=None)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    return path


def _settings(db, **extra):
    entorno = {"DATABASE_PATH": str(db), "AI_MODE": "anthropic", "ANTHROPIC_API_KEY": CLAVE,
               "ANTHROPIC_MODEL": "modelo-anthropic-simulado", "IA_PRECIO_ENTRADA_USD": "2",
               "IA_PRECIO_SALIDA_USD": "10"}
    entorno.update(extra)
    return load_settings(env_file=None, environ={k: v for k, v in entorno.items() if v is not None})


def _pedir(db, simulado, formato=None, **extra):
    pausas = []
    with closing(connect(db)) as conn:
        return cliente.pedir(conn, _settings(db, **extra), "Instrucciones SIMULADAS", TEXTO, "prueba",
                             cliente=simulado, dormir=pausas.append, formato=formato), pausas


def _usos(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT proposito, modelo, tokens_entrada, tokens_salida, costo_estimado, moneda,"
                            " intentos, resultado, motivo FROM ia_usage ORDER BY id").fetchall()


def test_con_anthropic_no_se_carga_el_sdk_de_openai(db, monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)        # si algo intentara importar el SDK de OpenAI, fallaría
    r, _ = _pedir(db, AnthropicSimulado(respuesta()))
    assert r.resultado == "ok"


def test_sin_clave_o_sin_modelo_no_llama(db):
    for falta in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
        simulado = AnthropicSimulado(respuesta())
        with closing(connect(db)) as conn, pytest.raises(cliente.IaConfiguracion, match=falta):
            cliente.pedir(conn, _settings(db, **{falta: None}), "x", TEXTO, "prueba", cliente=simulado)
        assert simulado.llamadas == []
    assert _usos(db) == []


def test_respuesta_valida_guarda_tokens_y_costo(db):
    simulado = AnthropicSimulado(respuesta())
    r, pausas = _pedir(db, simulado)
    assert (r.texto, r.modelo, r.tokens_entrada, r.tokens_salida, r.intentos, r.resultado) == (
        RESPUESTA, "modelo-anthropic-simulado", 1200, 300, 1, "ok")
    assert r.costo == Decimal("0.005400")                   # (1200 × 2 + 300 × 10) / 1 000 000 USD
    assert pausas == []
    llamada = simulado.llamadas[0]
    assert llamada["model"] == "modelo-anthropic-simulado" and llamada["system"] == "Instrucciones SIMULADAS"
    assert llamada["messages"] == [{"role": "user", "content": TEXTO}] and llamada["max_tokens"] == 4000
    assert "output_config" not in llamada                   # sin formato ni esfuerzo: nada extra
    assert _usos(db) == [("prueba", "modelo-anthropic-simulado", 1200, 300, "0.005400", "USD", 1, "ok", None)]


def test_formato_y_esfuerzo_van_en_output_config(db):
    simulado = AnthropicSimulado(respuesta())
    _pedir(db, simulado, formato=FORMATO, ANTHROPIC_EFFORT="Low")
    assert simulado.llamadas[0]["output_config"] == {"format": {"type": "json_schema", "schema": FORMATO["schema"]},
                                                      "effort": "low"}


def test_los_tokens_de_cache_cuentan_como_entrada(db):
    r, _ = _pedir(db, AnthropicSimulado(respuesta(entrada=200, cache_leida=1000, cache_escrita=50)))
    assert r.tokens_entrada == 1250


@pytest.mark.parametrize("razon", ["max_tokens", "model_context_window_exceeded"])
def test_respuesta_cortada_queda_incompleta(db, razon):
    r, _ = _pedir(db, AnthropicSimulado(respuesta(stop_reason=razon)))
    assert (r.resultado, r.motivo) == ("incompleta", f"incompleta · {razon}")
    assert _usos(db)[0][7:] == ("incompleta", f"incompleta · {razon}")


def test_rechazo_del_modelo_es_fallo(db):
    with pytest.raises(cliente.IaFallo) as fallo:
        _pedir(db, AnthropicSimulado(respuesta(stop_reason="refusal")))
    assert fallo.value.motivo == "rechazo del modelo"
    assert _usos(db)[0][7:] == ("fallo", "rechazo del modelo")


@pytest.mark.parametrize("exc, motivo", [
    (error(anthropic.AuthenticationError, 401), "AuthenticationError 401"),
    (error(anthropic.BadRequestError, 400), "BadRequestError 400"),          # p. ej. falta de saldo
    (error(anthropic.NotFoundError, 404), "NotFoundError 404"),              # modelo mal escrito
    (error(anthropic.EnforcedSpendLimitReachedError, 429), "EnforcedSpendLimitReachedError 429"),
])
def test_errores_que_no_se_reintentan(db, exc, motivo):
    simulado = AnthropicSimulado(exc, respuesta())
    with pytest.raises(cliente.IaFallo) as fallo:
        _pedir(db, simulado)
    assert len(simulado.llamadas) == 1 and fallo.value.intentos == 1 and fallo.value.motivo == motivo
    assert fallo.value.__cause__ is None and fallo.value.__suppress_context__   # el error original no se encadena
    assert _usos(db) == [("prueba", "modelo-anthropic-simulado", None, None, None, None, 1, "fallo", motivo)]


@pytest.mark.parametrize("temporal", [
    lambda: error(anthropic.RateLimitError, 429),
    lambda: error(anthropic.OverloadedError, 529),
    lambda: error(anthropic.InternalServerError, 500),
    lambda: anthropic.APITimeoutError(request=PETICION),
])
def test_un_error_temporal_se_reintenta_como_maximo_dos_veces(db, temporal):
    simulado = AnthropicSimulado(temporal(), temporal(), temporal(), respuesta())
    with pytest.raises(cliente.IaFallo) as fallo:
        _pedir(db, simulado)
    assert len(simulado.llamadas) == 3 and fallo.value.intentos == 3      # 1 + 2 reintentos, nunca un 4.º
    assert _usos(db)[0][6:8] == (3, "fallo")


def test_si_el_reintento_sale_bien_queda_ok(db):
    simulado = AnthropicSimulado(error(anthropic.OverloadedError, 529), respuesta())
    r, pausas = _pedir(db, simulado)
    assert (r.resultado, r.intentos, len(simulado.llamadas)) == ("ok", 2, 2)
    assert pausas == [cliente.PAUSAS_S[0]]


def test_la_base_nunca_guarda_el_texto_la_respuesta_ni_la_clave(db, tmp_path):
    _pedir(db, AnthropicSimulado(respuesta()))
    with pytest.raises(cliente.IaFallo):
        _pedir(db, AnthropicSimulado(error(anthropic.AuthenticationError, 401)))
    contenido = b"".join(p.read_bytes() for p in tmp_path.iterdir() if p.is_file())   # la base y su WAL, si hay
    for secreto in (TEXTO, RESPUESTA, CLAVE, CLAVE[:12], "invalid x-api-key"):
        assert secreto.encode("utf-8") not in contenido


def test_comando_ia_probar(db, monkeypatch, capsys):
    simulado = AnthropicSimulado(respuesta())
    monkeypatch.setattr(cliente, "crear_cliente", lambda settings: simulado)
    assert main(["ia", "probar"], _settings(db)) == 0
    salida = capsys.readouterr().out
    assert "Prueba de Anthropic: ok" in salida and "modelo modelo-anthropic-simulado" in salida
    assert "panel de Anthropic" in salida and CLAVE not in salida


def test_doctor_oculta_la_clave(db, capsys):
    assert main(["doctor"], _settings(db)) == 0
    salida = capsys.readouterr().out
    assert CLAVE not in salida
    assert any(l.split()[:1] == ["ANTHROPIC_API_KEY"] and "configurado (oculto)" in l for l in salida.splitlines())


def test_configuracion_de_anthropic_se_valida(db):
    s = _settings(db)
    assert (s.ai_mode, s.ia_activa, s.ia_modelo) == ("anthropic", True, "modelo-anthropic-simulado")
    assert s.anthropic_effort is None
    with pytest.raises(ValueError, match="ANTHROPIC_EFFORT"):
        _ = _settings(db, ANTHROPIC_EFFORT="muchisimo").anthropic_effort
    apagada = _settings(db, AI_MODE="none")
    assert (apagada.ia_activa, apagada.ia_modelo) == (False, "")
    assert _settings(db, AI_MODE="openai", OPENAI_MODEL="otro").ia_modelo == "otro"
