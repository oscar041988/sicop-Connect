"""Cliente de OpenAI (Reporte con IA, lección 2) con un OpenAI SIMULADO: nunca se llama a la red ni se gasta.

Las respuestas son objetos simulados con los campos que usa la app; los errores son las clases reales del SDK
(openai 3.40.0), armadas con respuestas HTTP SIMULADAS. La clave es SIMULADA.
"""

import sqlite3
import sys
from contextlib import closing
from decimal import Decimal
from types import SimpleNamespace

import httpx2
import openai
import pytest

from app.ai import cliente
from app.cli import main
from app.config import load_settings
from app.database import apply_migrations, connect

CLAVE = "sk-SIMULADA-no-es-real-1234567890"
TEXTO = "EXPEDIENTE SIMULADO: monitoreo GPS de 10 vehículos, texto que nunca debe guardarse"
RESPUESTA = "RESUMEN SIMULADO que tampoco debe guardarse"
PETICION = httpx2.Request("POST", "https://api.openai.example/v1/responses")


class OpenAISimulado:
    """Imita client.responses.create: devuelve o lanza, en orden, lo que se le dé. Anota cada llamada."""

    def __init__(self, *efectos):
        self.efectos, self.llamadas, self.responses = list(efectos), [], self

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        efecto = self.efectos.pop(0)
        if isinstance(efecto, Exception):
            raise efecto
        return efecto


def respuesta(status="completed", entrada=1200, salida=300, razon=None):
    return SimpleNamespace(status=status, output_text=RESPUESTA, model="modelo-simulado-1",
                           usage=SimpleNamespace(input_tokens=entrada, output_tokens=salida),
                           incomplete_details=SimpleNamespace(reason=razon) if razon else None)


def error(clase, estado, codigo=None):
    # El mensaje imita el de OpenAI ante una clave mala: trae parte de la clave, por eso nunca se guarda.
    return clase(f"Incorrect API key provided: {CLAVE[:12]}***", response=httpx2.Response(estado, request=PETICION),
                 body={"code": codigo} if codigo else None)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    return path


def _settings(db, **extra):
    entorno = {"DATABASE_PATH": str(db), "AI_MODE": "openai", "OPENAI_API_KEY": CLAVE,
               "OPENAI_MODEL": "modelo-simulado-1", "IA_PRECIO_ENTRADA_USD": "2.5", "IA_PRECIO_SALIDA_USD": "10"}
    entorno.update(extra)
    return load_settings(env_file=None, environ={k: v for k, v in entorno.items() if v is not None})


def _pedir(db, simulado, **extra):
    pausas = []
    with closing(connect(db)) as conn:
        try:
            return cliente.pedir(conn, _settings(db, **extra), "Instrucciones SIMULADAS", TEXTO, "prueba",
                                 cliente=simulado, dormir=pausas.append), pausas
        finally:
            conn.close()


def _usos(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT proposito, modelo, tokens_entrada, tokens_salida, costo_estimado, moneda,"
                            " intentos, resultado, motivo FROM ia_usage ORDER BY id").fetchall()


def test_con_ai_mode_none_no_llama_ni_carga_el_sdk(db, monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)        # si algo intentara importar el SDK, fallaría aquí
    simulado = OpenAISimulado(respuesta())
    with closing(connect(db)) as conn, pytest.raises(cliente.IaApagada):
        cliente.pedir(conn, _settings(db, AI_MODE="none"), "x", TEXTO, "prueba", cliente=simulado)
    assert simulado.llamadas == [] and _usos(db) == []


def test_sin_clave_o_sin_modelo_no_llama(db):
    for falta in ("OPENAI_API_KEY", "OPENAI_MODEL"):
        simulado = OpenAISimulado(respuesta())
        with closing(connect(db)) as conn, pytest.raises(cliente.IaConfiguracion, match=falta):
            cliente.pedir(conn, _settings(db, **{falta: None}), "x", TEXTO, "prueba", cliente=simulado)
        assert simulado.llamadas == []
    assert _usos(db) == []


def test_respuesta_valida_guarda_tokens_y_costo(db):
    simulado = OpenAISimulado(respuesta())
    r, pausas = _pedir(db, simulado)
    assert (r.texto, r.tokens_entrada, r.tokens_salida, r.intentos, r.resultado) == (RESPUESTA, 1200, 300, 1, "ok")
    assert r.costo == Decimal("0.006000")                   # (1200 × 2.5 + 300 × 10) / 1 000 000 USD
    assert pausas == []
    llamada = simulado.llamadas[0]
    assert llamada["model"] == "modelo-simulado-1" and llamada["input"] == TEXTO and llamada["store"] is False
    assert llamada["max_output_tokens"] == 4000
    assert _usos(db) == [("prueba", "modelo-simulado-1", 1200, 300, "0.006000", "USD", 1, "ok", None)]


def test_sin_precio_el_costo_queda_vacio(db):
    r, _ = _pedir(db, OpenAISimulado(respuesta()), IA_PRECIO_SALIDA_USD=None)
    assert r.costo is None
    assert _usos(db)[0][4:6] == (None, None)


def test_respuesta_incompleta_se_anota(db):
    r, _ = _pedir(db, OpenAISimulado(respuesta(status="incomplete", razon="max_output_tokens")))
    assert r.resultado == "incompleta" and r.motivo == "incompleta · max_output_tokens"
    assert _usos(db)[0][7:] == ("incompleta", "incompleta · max_output_tokens")


@pytest.mark.parametrize("exc, motivo", [
    (error(openai.AuthenticationError, 401, "invalid_api_key"), "AuthenticationError 401 · invalid_api_key"),
    (error(openai.RateLimitError, 429, "insufficient_quota"), "RateLimitError 429 · insufficient_quota"),
    (error(openai.NotFoundError, 404, "model_not_found"), "NotFoundError 404 · model_not_found"),
    (error(openai.BadRequestError, 400), "BadRequestError 400"),
])
def test_errores_que_no_se_reintentan(db, exc, motivo):
    simulado = OpenAISimulado(exc, respuesta())
    with pytest.raises(cliente.IaFallo) as fallo:
        _pedir(db, simulado)
    assert len(simulado.llamadas) == 1 and fallo.value.intentos == 1 and fallo.value.motivo == motivo
    assert fallo.value.__cause__ is None and fallo.value.__suppress_context__   # el error original no se encadena
    assert _usos(db) == [("prueba", "modelo-simulado-1", None, None, None, None, 1, "fallo", motivo)]


@pytest.mark.parametrize("temporal", [
    lambda: error(openai.RateLimitError, 429, "rate_limit_exceeded"),
    lambda: error(openai.InternalServerError, 500),
    lambda: openai.APITimeoutError(request=PETICION),
])
def test_un_error_temporal_se_reintenta_como_maximo_dos_veces(db, temporal):
    simulado = OpenAISimulado(temporal(), temporal(), temporal(), respuesta())
    with pytest.raises(cliente.IaFallo) as fallo:
        _pedir(db, simulado)
    assert len(simulado.llamadas) == 3 and fallo.value.intentos == 3      # 1 + 2 reintentos, nunca un 4.º
    assert _usos(db)[0][6:8] == (3, "fallo")


def test_si_el_reintento_sale_bien_queda_ok(db):
    simulado = OpenAISimulado(error(openai.InternalServerError, 503), respuesta())
    r, pausas = _pedir(db, simulado)
    assert (r.resultado, r.intentos, len(simulado.llamadas)) == ("ok", 2, 2)
    assert pausas == [cliente.PAUSAS_S[0]]


def test_la_base_nunca_guarda_el_texto_la_respuesta_ni_la_clave(db, tmp_path):
    _pedir(db, OpenAISimulado(respuesta()))
    with pytest.raises(cliente.IaFallo):
        _pedir(db, OpenAISimulado(error(openai.AuthenticationError, 401, "invalid_api_key")))
    contenido = b"".join(p.read_bytes() for p in tmp_path.iterdir() if p.is_file())   # la base y su WAL, si hay
    for secreto in (TEXTO, RESPUESTA, CLAVE, CLAVE[:12], "Incorrect API key"):
        assert secreto.encode("utf-8") not in contenido


def test_ia_usage_no_se_modifica_ni_se_borra_y_migrate_es_repetible(db):
    _pedir(db, OpenAISimulado(respuesta()))
    assert apply_migrations(db) == []
    with closing(sqlite3.connect(db)) as conn:
        for sql in ("UPDATE ia_usage SET modelo = 'otro'", "DELETE FROM ia_usage"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


def test_comando_ia_probar(db, monkeypatch, capsys):
    simulado = OpenAISimulado(respuesta())
    monkeypatch.setattr(cliente, "crear_cliente", lambda settings: simulado)
    assert main(["ia", "probar"], _settings(db)) == 0
    salida = capsys.readouterr().out
    assert "modelo modelo-simulado-1" in salida and "entrada 1200 · salida 300" in salida
    assert "0.006000 USD (estimado)" in salida and CLAVE not in salida
    assert main(["ia", "probar"], _settings(db, AI_MODE="none")) == 1
    assert "La IA está apagada" in capsys.readouterr().out and len(simulado.llamadas) == 1


def test_comando_ia_probar_con_fallo_no_muestra_la_clave(db, monkeypatch, capsys):
    simulado = OpenAISimulado(error(openai.AuthenticationError, 401, "invalid_api_key"))
    monkeypatch.setattr(cliente, "crear_cliente", lambda settings: simulado)
    assert main(["ia", "probar"], _settings(db)) == 1
    salida = capsys.readouterr()
    assert "FALLO: AuthenticationError 401 · invalid_api_key" in salida.err
    assert CLAVE[:12] not in salida.out + salida.err


def test_doctor_oculta_la_clave(db, capsys):
    assert main(["doctor"], _settings(db)) == 0
    salida = capsys.readouterr().out
    assert CLAVE not in salida
    assert any(l.split()[:1] == ["OPENAI_API_KEY"] and "configurado (oculto)" in l for l in salida.splitlines())


def test_configuracion_de_la_ia_se_valida(db):
    with pytest.raises(ValueError, match="AI_MODE"):
        _ = _settings(db, AI_MODE="chatgpt").ai_mode
    with pytest.raises(ValueError, match="IA_PRECIO_ENTRADA_USD"):
        _ = _settings(db, IA_PRECIO_ENTRADA_USD="2,5").ia_precio_entrada_usd
    with pytest.raises(ValueError, match="IA_TIMEOUT_SECONDS"):
        _ = _settings(db, IA_TIMEOUT_SECONDS="5").ia_timeout_seconds
    defecto = load_settings(env_file=None, environ={})
    assert defecto.ai_mode == "none" and defecto.ia_timeout_seconds == 120 and defecto.ia_max_output_tokens == 4000
    assert defecto.ia_precio_entrada_usd is None and defecto.openai_model == ""
