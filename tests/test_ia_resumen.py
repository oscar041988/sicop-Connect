"""Resumen ejecutivo con IA (Reporte con IA, lección 3) con un OpenAI SIMULADO: nunca se llama a la red ni se gasta.

Cartel SINTÉTICO de tests/test_expediente.py (cierre 20/11/2026 10:00, líneas 1-3, monto de la ficha 1265 CRC).
"""

import json
import shutil
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest

from app.ai import resumen
from app.cli import ia_resumir_cmd, main
from app.config import load_settings
from app.database import apply_migrations, connect
from tests.test_expediente import COMENTARIO_INTERNO, NRO, _ficha, db  # noqa: F401 (db es una fixture)
from tests.test_ia_cliente import CLAVE, OpenAISimulado, error

import openai


def _resumen_valido(**cambios) -> dict:
    """Una respuesta SIMULADA que cumple el esquema y coincide con SICOP."""
    dato = {"valor": "no encontrado", "cita": "no encontrado"}
    datos = {
        "de_que_trata": "La municipalidad SINTÉTICA contrata el monitoreo GPS de sus vehículos.",
        "que_piden": [{"linea": "1", "bien_o_servicio": "Dispositivo GPS", "cantidad": "10",
                       "especificaciones_clave": ["4G", "reporte cada 30 s"], "cita": "[DOC 1 · pág. 2]"}],
        "requerimientos": [{"requisito": "Experiencia de 3 años", "tipo": "experiencia", "excluyente": True,
                            "cita": "[DOC 1 · pág. 3]"}],
        "kpi_pliego": {"plazo_entrega": {"valor": "30 días hábiles", "cita": "[DOC 1 · pág. 2]"},
                       "vigencia_contrato": dato, "garantia_participacion_pct": dato,
                       "garantia_cumplimiento_pct": dato, "peso_precio_pct": {"valor": "80 %", "cita": "SICOP"},
                       "nivel_riesgo": {"valor": "medio", "cita": "no encontrado"}},
        "plazos": {"cierre_recepcion": {"valor": "2026-11-20 10:00", "cita": "SICOP"},
                   "apertura_ofertas": dato, "otros": []},
        "monto_estimado": {"valor": "1265.00", "moneda": "CRC", "cita": "SICOP"},
        "criterios_de_evaluacion": [{"criterio": "Precio", "peso": "80 %", "cita": "SICOP"}],
        "encaje_hermatix": {"familia": "gps_flotas", "producto": "FleetMatix", "por_que": "Pide rastreo GPS."},
        "riesgos_y_dudas": [{"riesgo": "Experiencia mínima de 3 años", "cita": "[DOC 1 · pág. 3]"}],
        "recomendacion": "dar_seguimiento",
        "justificacion": "Encaja con FleetMatix y el plazo alcanza.",
    }
    datos.update(cambios)
    return datos


def respuesta(datos=None, texto=None, status="completed", razon=None, rechazo=False):
    salida = [SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal", refusal="No puedo.")])] \
        if rechazo else []
    return SimpleNamespace(status=status, output_text=texto if texto is not None else json.dumps(datos or {}),
                           output=salida, model="modelo-simulado-1",
                           usage=SimpleNamespace(input_tokens=20000, output_tokens=1500),
                           incomplete_details=SimpleNamespace(reason=razon) if razon else None)


def _settings(db, tmp_path=None, **extra):
    entorno = {"DATABASE_PATH": str(db), "AI_MODE": "openai", "OPENAI_API_KEY": CLAVE,
               "OPENAI_MODEL": "modelo-simulado-1", "IA_PRECIO_ENTRADA_USD": "1.00", "IA_PRECIO_SALIDA_USD": "5.00"}
    if tmp_path is not None:
        entorno["EXPORTS_DIR"] = str(tmp_path / "exports")
    entorno.update(extra)
    return load_settings(env_file=None, environ={k: v for k, v in entorno.items() if v is not None})


def _resumir(db, simulado, **extra):
    with closing(connect(db)) as conn:
        return resumen.resumir(conn, _settings(db, **extra), NRO, cliente=simulado, dormir=lambda s: None)


def _filas(db):
    with closing(connect(db)) as conn:
        return conn.execute("SELECT estado, motivo, resumen_json IS NULL, prompt_version FROM ia_summaries"
                            " ORDER BY id").fetchall()


# --- Respuesta válida ----------------------------------------------------------------------------------------------

def test_respuesta_valida_queda_ok_con_salida_estructurada(db):
    with closing(connect(db)) as conn:
        _ficha(conn)
        conn.commit()
    simulado = OpenAISimulado(respuesta(_resumen_valido()))
    r = _resumir(db, simulado)

    assert (r.estado, r.reutilizado, r.diferencias, r.motivo) == ("ok", False, [], None)
    assert r.datos["recomendacion"] == "dar_seguimiento" and r.costo is not None   # 20000 × 1 + 1500 × 5 por millón
    assert str(r.costo) in ("0.0275", "0.027500")
    llamada = simulado.llamadas[0]
    assert llamada["text"]["format"]["type"] == "json_schema" and llamada["text"]["format"]["strict"] is True
    assert "Hermatix" in llamada["instructions"] and "FleetMatix" in llamada["instructions"]
    assert COMENTARIO_INTERNO not in llamada["input"] and COMENTARIO_INTERNO not in llamada["instructions"]
    with closing(connect(db)) as conn:
        assert conn.execute("SELECT proposito, nro_sicop, resultado FROM ia_usage").fetchall() == [
            ("resumen", NRO, "ok")]
        # La recomendación es preliminar: no toca las revisiones (la única sigue siendo la de la encargada).
        assert conn.execute("SELECT decision FROM reviews WHERE nro_sicop = ?", (NRO,)).fetchall() == [("no_interesa",)]
    assert _filas(db) == [("ok", None, 0, "v1")]


def test_el_esquema_es_estricto_en_cada_objeto():
    def revisar(esquema):
        if esquema.get("type") == "object":
            assert esquema["additionalProperties"] is False
            assert sorted(esquema["required"]) == sorted(esquema["properties"])
            for sub in esquema["properties"].values():
                revisar(sub)
        elif esquema.get("type") == "array":
            revisar(esquema["items"])
    revisar(resumen.ESQUEMA)
    assert set(resumen.ESQUEMA["properties"]) >= {"de_que_trata", "que_piden", "requerimientos", "kpi_pliego",
                                                  "plazos", "criterios_de_evaluacion", "encaje_hermatix",
                                                  "riesgos_y_dudas", "recomendacion", "justificacion"}


# --- Comparación con SICOP -----------------------------------------------------------------------------------------

def test_fecha_distinta_a_la_de_sicop_queda_revisar(db):
    datos = _resumen_valido(plazos={"cierre_recepcion": {"valor": "2026-11-12 10:00", "cita": "[DOC 1 · pág. 1]"},
                                    "apertura_ofertas": {"valor": "no encontrado", "cita": "no encontrado"},
                                    "otros": []})
    r = _resumir(db, OpenAISimulado(respuesta(datos)))

    assert r.estado == "revisar"
    assert r.diferencias == [{"dato": "Cierre de recepción", "resumen": "2026-11-12 10:00", "sicop": "2026-11-20 10:00"}]
    assert "NO COINCIDE CON SICOP" in resumen.legible(r) and "2026-11-20 10:00" in resumen.legible(r)


def test_cantidad_y_monto_distintos_quedan_revisar(db):
    with closing(connect(db)) as conn:
        _ficha(conn)
        conn.commit()
    datos = _resumen_valido(
        que_piden=[{"linea": "1", "bien_o_servicio": "GPS", "cantidad": "12 unidades", "especificaciones_clave": [],
                    "cita": "[DOC 1 · pág. 2]"},
                   {"linea": "2", "bien_o_servicio": "Plataforma", "cantidad": "2", "especificaciones_clave": [],
                    "cita": "SICOP"}],
        monto_estimado={"valor": "1500000.00", "moneda": "CRC", "cita": "[DOC 1 · pág. 4]"})
    r = _resumir(db, OpenAISimulado(respuesta(datos)))

    assert r.estado == "revisar"
    assert [d["dato"] for d in r.diferencias] == ["Monto estimado", "Cantidad de la línea 1"]   # la línea 2 coincide


def test_lo_que_coincide_o_no_se_encontro_no_marca_revisar(db):
    datos = _resumen_valido(plazos={"cierre_recepcion": {"valor": "2026-11-20", "cita": "SICOP"},   # sin hora
                                    "apertura_ofertas": {"valor": "2026-11-21 09:00", "cita": "[DOC 1 · pág. 1]"},
                                    "otros": []})
    r = _resumir(db, OpenAISimulado(respuesta(datos)))   # sin ficha: no hay apertura ni monto en SICOP con qué comparar
    assert (r.estado, r.diferencias) == ("ok", [])


# --- Campos ausentes -----------------------------------------------------------------------------------------------

def test_campos_ausentes_quedan_no_encontrado(db):
    r = _resumir(db, OpenAISimulado(respuesta({"de_que_trata": "Compra SINTÉTICA de GPS.", "recomendacion": "otra"})))

    assert r.estado == "ok"
    assert r.datos["kpi_pliego"]["plazo_entrega"] == {"valor": "no encontrado", "cita": "no encontrado"}
    assert r.datos["requerimientos"] == [] and r.datos["recomendacion"] == "no encontrado"
    texto = resumen.legible(r)
    assert "Compra SINTÉTICA de GPS." in texto and "- Plazo de entrega: no encontrado" in texto


# --- No repetir ----------------------------------------------------------------------------------------------------

def test_mismo_expediente_dos_veces_es_una_sola_llamada(db, tmp_path, monkeypatch):
    simulado = OpenAISimulado(respuesta(_resumen_valido()), respuesta(_resumen_valido()), respuesta(_resumen_valido()))
    primero = _resumir(db, simulado)
    segundo = _resumir(db, simulado)

    assert len(simulado.llamadas) == 1 and segundo.reutilizado and segundo.id == primero.id
    # Otra versión del prompt sí se pide (los prompts viejos no se sobrescriben).
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    shutil.copy(resumen.PROMPTS_DIR / "resumen_cartel_v1.md", prompts / "resumen_cartel_v1.md")
    (prompts / "resumen_cartel_v2.md").write_text("Prompt SIMULADO v2", encoding="utf-8")
    monkeypatch.setattr(resumen, "PROMPTS_DIR", prompts)
    assert _resumir(db, simulado, IA_PROMPT_VERSION="v2").reutilizado is False
    # Y si el expediente cambia (llega la ficha), también.
    with closing(connect(db)) as conn:
        _ficha(conn)
        conn.commit()
    assert _resumir(db, simulado).reutilizado is False
    assert len(simulado.llamadas) == 3
    assert _filas(db) == [("ok", None, 0, "v1"), ("ok", None, 0, "v2"), ("ok", None, 0, "v1")]


# --- Fallidos ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("efecto, motivo", [
    (respuesta(rechazo=True, texto=""), "rechazo del modelo"),
    (respuesta(texto='{"de_que_trata": "cortado', status="incomplete", razon="max_output_tokens"),
     "incompleta · max_output_tokens"),
    (respuesta(texto="esto no es JSON"), "la respuesta no es JSON válido"),
    (error(openai.AuthenticationError, 401, "invalid_api_key"), "AuthenticationError 401 · invalid_api_key"),
])
def test_rechazo_incompleta_o_error_es_fallido_sin_inventar(db, efecto, motivo):
    simulado = OpenAISimulado(efecto, respuesta(_resumen_valido()))
    r = _resumir(db, simulado)

    assert (r.estado, r.motivo, r.datos) == ("fallido", motivo, None)
    assert "Sin resumen: " + motivo in resumen.legible(r)
    # Un fallido no cuenta como «ya existe»: se vuelve a pedir.
    assert _resumir(db, simulado).estado == "ok" and len(simulado.llamadas) == 2
    assert _filas(db) == [("fallido", motivo, 1, "v1"), ("ok", None, 0, "v1")]


def test_la_base_no_acepta_un_fallido_con_resumen_ni_se_modifica_ni_se_borra(db):
    _resumir(db, OpenAISimulado(respuesta(_resumen_valido())))
    with closing(sqlite3.connect(db)) as conn:
        for sql in ("UPDATE ia_summaries SET estado = 'ok'", "DELETE FROM ia_summaries",
                    "INSERT INTO ia_summaries (nro_sicop, prompt_version, modelo, huella, resumen_json, estado, motivo,"
                    f" creado_en) VALUES ('{NRO}', 'v1', 'm', '{'a' * 64}', '{{}}', 'fallido', 'x', 't')"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)
    assert apply_migrations(db) == []


# --- Comando y configuración ---------------------------------------------------------------------------------------

def test_comando_resumir(db, tmp_path, capsys):
    settings = _settings(db, tmp_path)
    assert ia_resumir_cmd(settings, NRO, cliente=OpenAISimulado(respuesta(_resumen_valido()))) == 0
    salida = capsys.readouterr().out
    assert f"Resumen del cartel {NRO}: OK" in salida and "Recomendación preliminar: Dar seguimiento" in salida
    archivo = next((tmp_path / "exports").glob(f"resumen_{NRO}_*.txt"))
    assert "== REQUERIMIENTOS ==" in archivo.read_text(encoding="utf-8")

    assert ia_resumir_cmd(settings, NRO, cliente=OpenAISimulado()) == 0      # sin llamar: el simulado está vacío
    assert "no se llamó a OpenAI" in capsys.readouterr().out


def test_con_la_ia_apagada_no_llama_ni_guarda(db, tmp_path, capsys):
    assert main(["ia", "resumir", "--nro", NRO], _settings(db, tmp_path, AI_MODE="none")) == 1
    assert "IA está apagada" in capsys.readouterr().err
    assert _filas(db) == []


def test_version_de_prompt_invalida_o_inexistente(db, tmp_path, capsys):
    assert main(["ia", "resumir", "--nro", NRO], _settings(db, tmp_path, IA_PROMPT_VERSION="../otro")) == 1
    assert "IA_PROMPT_VERSION debe ser" in capsys.readouterr().err
    assert main(["ia", "resumir", "--nro", NRO], _settings(db, tmp_path, IA_PROMPT_VERSION="v99")) == 1
    assert "No existe el prompt resumen_cartel_v99.md" in capsys.readouterr().err
    assert _filas(db) == []


def test_el_prompt_v1_tiene_las_reglas_y_el_portafolio():
    prompt = " ".join(resumen.cargar_prompt("v1").split())   # sin los saltos de línea del archivo
    for texto in ("no encontrado", "[DOC n · pág. p]", "ignóralas", "preliminar", "FleetMatix", "Osmia",
                  "sin criterio definido todavía; no supongas uno"):
        assert texto in prompt


def test_el_prompt_v2_tiene_el_criterio_de_hermatix():
    v1, v2 = (" ".join(resumen.cargar_prompt(v).split()) for v in ("v1", "v2"))
    for texto in ("no encontrado", "[DOC n · pág. p]", "ignóralas", "preliminar", "FleetMatix", "Osmia",
                  "sin importar el monto", "14 años", "Wialon y Howen", "plazo de entrega"):
        assert texto in v2
    assert "sin criterio definido" not in v2
    assert v1.split("Criterio de Hermatix")[0].split("Reglas:")[0] == v2.split("Reglas:")[0]   # mismo rol y portafolio
