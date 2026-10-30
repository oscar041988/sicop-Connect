"""Cola automática de resúmenes (Reporte con IA, lección 5) con un OpenAI SIMULADO: nunca se llama a la red ni se gasta.

Carteles SINTÉTICOS: el de tests/test_expediente.py (Alta) y otros cuatro copiados de él, con fichas y pliegos
SIMULADOS. Las fechas de
cierre se calculan desde hoy, porque la cola cuenta «lo de hoy» con el reloj real (ia_summaries.creado_en).
"""

from contextlib import closing
from datetime import datetime, timedelta

import openai
import pytest
from fastapi.testclient import TestClient

from app.ai import cliente as ia_cliente, cola, resumen
from app.cli import ia_cola_cmd
from app.database import connect
from app.importers.comun import HORA_CR
from app.main import app
from tests.test_expediente import NRO, T, _paginas, db  # noqa: F401 (db es una fixture)
from tests.test_ia_cliente import OpenAISimulado, error
from tests.test_ia_resumen import _resumen_valido, _settings, respuesta
from tests.test_panel import iniciar_sesion

MEDIA, SIN_FICHA, BAJA, CERRADO = "00000000002", "00000000003", "00000000004", "00000000005"
SIN_DORMIR = {"dormir": lambda s: None}


def _iso(dias: int) -> str:
    return (datetime.now(HORA_CR) + timedelta(days=dias)).replace(microsecond=0).isoformat()


@pytest.fixture
def carteles(db):
    """NRO Alta enriquecido (cierra en 20 días) · MEDIA enriquecido (cierra en 5) · SIN_FICHA Alta sin enriquecer ·
    BAJA enriquecido · CERRADO Alta enriquecido que ya cerró. Las fichas se crean aquí (no se pueden modificar)."""
    with closing(connect(db)) as conn, conn:
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = ? WHERE nro_sicop = ?", (_iso(20), NRO))
        for nro, dias, ficha in ((NRO, 20, True), (MEDIA, 5, True), (SIN_FICHA, 5, False), (BAJA, 5, True),
                                 (CERRADO, -1, True)):
            if nro != NRO:
                conn.execute("INSERT INTO tenders (nro_sicop, institution_cedula, descripcion, fecha_cierre_recepcion,"
                             " content_hash, first_seen, last_seen) SELECT ?, institution_cedula,"
                             " descripcion || ' ' || ?, ?, 'h', first_seen, last_seen FROM tenders WHERE nro_sicop = ?",
                             (nro, nro, _iso(dias), NRO))
            if ficha:
                detalle = conn.execute(
                    "INSERT INTO tender_details (nro_sicop, consultado_en, content_hash, copia_fiel, campos_quitados,"
                    " cierre_recepcion) VALUES (?, ?, 'f', '{}', '[]', ?)", (nro, T, _iso(dias))).lastrowid
                doc = conn.execute(
                    "INSERT INTO tender_documents (nro_sicop, detalle_id, tipo_documento, nombre_documento,"
                    " nombre_original, server_file, sha256, ruta_local, registrado_en, estado, texto_estado, paginas)"
                    " VALUES (?, ?, 'Pliego', 'Pliego', 'pliego.pdf', 's', 'sha', 'x', ?, 'guardado', 'extraido', 1)",
                    (nro, detalle, T)).lastrowid
                _paginas(conn, doc, [f"Pliego SINTÉTICO del cartel {nro}."])
        for nro, encaje in ((NRO, "alta"), (MEDIA, "media"), (SIN_FICHA, "alta"), (BAJA, "baja"), (CERRADO, "alta")):
            conn.execute("INSERT INTO opportunity_assessments (nro_sicop, familia, encaje, evidencia, rules_version,"
                         " evaluated_at) VALUES (?, 'gps_flotas', ?, 'gps', 'reglas-sinteticas', ?)", (nro, encaje, T))
    return db


def _cola(db, ahora=None, **extra):
    with closing(connect(db)) as conn:
        return [e.nro_sicop for e in cola.cola(conn, _settings(db, **extra), ahora or datetime.now(HORA_CR))]


def _correr(db, simulado, **extra):
    return cola.correr(_settings(db, **extra), cliente=simulado, **SIN_DORMIR)


def _ok():
    return respuesta(_resumen_valido())


def _resumidos(db):
    with closing(connect(db)) as conn:
        return conn.execute("SELECT nro_sicop, estado FROM ia_summaries ORDER BY id").fetchall()


# --- Qué entra en la cola ------------------------------------------------------------------------------------------

def test_solo_alta_y_media_enriquecidos_con_plazo_abierto_y_alta_primero(carteles):
    assert _cola(carteles) == [NRO, MEDIA]   # Alta antes que Media, aunque MEDIA cierre antes


def test_un_cartel_resumido_sale_y_vuelve_si_su_expediente_cambia(carteles):
    simulado = OpenAISimulado(_ok(), _ok())
    corrida = _correr(carteles, simulado)

    assert (corrida.estado, len(corrida.resultados), corrida.pendientes) == ("ok", 2, 0)
    assert [n for n, _ in _resumidos(carteles)] == [NRO, MEDIA]
    assert _correr(carteles, OpenAISimulado()).estado == "sin_cola"   # nada nuevo: no se llama a OpenAI
    manana = datetime.now(HORA_CR) + timedelta(days=1)
    assert _cola(carteles, manana) == []
    with closing(connect(carteles)) as conn, conn:   # llega un documento nuevo: cambia la huella del expediente
        doc = conn.execute("SELECT id FROM tender_documents WHERE nro_sicop = ? LIMIT 1", (MEDIA,)).fetchone()[0]
        conn.execute("INSERT INTO tender_document_text (documento_id, archivo_interno, pagina, texto)"
                     " VALUES (?, '', 2, 'Adenda SINTÉTICA: cambia el plazo.')", (doc,))
    assert _cola(carteles, manana) == [MEDIA]
    assert _cola(carteles) == []   # pero hoy ya se intentó: no se repite hoy


# --- Presupuesto diario --------------------------------------------------------------------------------------------

def test_tope_de_resumenes_por_dia(carteles):
    corrida = _correr(carteles, OpenAISimulado(_ok()), IA_MAX_SUMMARIES_PER_DAY="1")

    assert (corrida.estado, len(corrida.resultados), corrida.pendientes) == ("tope", 1, 1)
    assert "IA_MAX_SUMMARIES_PER_DAY" in corrida.motivo
    assert _correr(carteles, OpenAISimulado(), IA_MAX_SUMMARIES_PER_DAY="1").estado == "tope"   # ni uno más hoy


def test_tope_de_costo_antes_de_llamar(carteles):
    simulado = OpenAISimulado()
    corrida = _correr(carteles, simulado, IA_MAX_DAILY_COST="0.01")   # cada resumen podría costar más de 0.02

    assert (corrida.estado, corrida.pendientes, simulado.llamadas) == ("tope", 2, [])
    assert "IA_MAX_DAILY_COST" in corrida.motivo


def test_el_costo_de_hoy_cuenta_toda_la_ia(carteles):
    # Primer resumen: 20000 × 1 + 1500 × 5 por millón = 0.0275 USD. El siguiente podría costar hasta ~0.0205
    # (su expediente + 4000 tokens de salida): 0.048 no cabe en un tope de 0.045.
    corrida = _correr(carteles, OpenAISimulado(_ok(), _ok()), IA_MAX_DAILY_COST="0.045")
    assert (corrida.estado, len(corrida.resultados), corrida.pendientes) == ("tope", 1, 1)
    assert str(corrida.costo_hoy) in ("0.0275", "0.027500")


# --- Fallos ---------------------------------------------------------------------------------------------------------

def test_un_fallo_no_detiene_la_cola(carteles):
    simulado = OpenAISimulado(error(openai.BadRequestError, 400), _ok())
    corrida = _correr(carteles, simulado)

    # «revisar» y no «ok»: la respuesta simulada dice otro cierre que el de SICOP (eso es correcto).
    assert corrida.estado == "con_fallos" and [r.estado for r in corrida.resultados] == ["fallido", "revisar"]
    assert _resumidos(carteles) == [(NRO, "fallido"), (MEDIA, "revisar")]
    assert _cola(carteles) == []   # el fallido no se vuelve a pagar hoy…
    assert _cola(carteles, datetime.now(HORA_CR) + timedelta(days=1)) == [NRO]   # …mañana sí


@pytest.mark.parametrize("efecto", [error(openai.RateLimitError, 429, "insufficient_quota"),
                                    error(openai.AuthenticationError, 401)])
def test_sin_saldo_o_clave_rechazada_detienen_la_cola(carteles, efecto):
    simulado = OpenAISimulado(efecto)
    corrida = _correr(carteles, simulado)

    assert (corrida.estado, len(simulado.llamadas), corrida.pendientes) == ("detenida", 1, 1)


def test_ia_apagada_no_hace_nada_y_sin_precios_no_arranca(carteles):
    simulado = OpenAISimulado()
    assert _correr(carteles, simulado, AI_MODE="none").estado == "apagada" and simulado.llamadas == []
    with pytest.raises(ia_cliente.IaConfiguracion, match="IA_MAX_DAILY_COST"):
        _correr(carteles, simulado, IA_PRECIO_SALIDA_USD="")
    assert _resumidos(carteles) == []


# --- Comando -------------------------------------------------------------------------------------------------------

def test_comando_ver_no_llama_y_comando_corre(carteles, capsys):
    simulado = OpenAISimulado(_ok(), error(openai.BadRequestError, 400))
    assert ia_cola_cmd(_settings(carteles), ver=True, cliente=simulado) == 0
    salida = capsys.readouterr().out
    assert "no se llamó a OpenAI): 2" in salida and f"{NRO} · Alta" in salida and simulado.llamadas == []

    assert ia_cola_cmd(_settings(carteles), ver=False, cliente=simulado, **SIN_DORMIR) == 1   # hubo un fallido
    salida = capsys.readouterr().out
    assert "Resúmenes: 2 nuevos (1 para revisar, 1 fallidos)" in salida
    assert ia_cola_cmd(_settings(carteles, AI_MODE="none"), ver=False) == 0
    assert "La IA está apagada" in capsys.readouterr().out


# --- Panel ---------------------------------------------------------------------------------------------------------

def _panel(db, monkeypatch, ai_mode):
    for clave, valor in {"DATABASE_PATH": str(db), "AI_MODE": ai_mode}.items():
        monkeypatch.setenv(clave, valor)
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, "encargada@ejemplo.test").status_code == 303
    return cliente


def test_el_panel_muestra_el_resumen_con_su_etiqueta_escapado_y_su_historial(carteles, monkeypatch):
    malicioso = respuesta(_resumen_valido(justificacion="<script>alert(1)</script> Encaja con FleetMatix."))
    _correr(carteles, OpenAISimulado(error(openai.BadRequestError, 400), _ok()))   # NRO fallido, MEDIA con resumen
    with closing(connect(carteles)) as conn:   # NRO otra vez (a mano, como ia resumir): ahora con respuesta
        resumen.resumir(conn, _settings(carteles), NRO, cliente=OpenAISimulado(malicioso), **SIN_DORMIR)

    pagina = _panel(carteles, monkeypatch, "openai").get(f"/oportunidades/{NRO}").text
    assert "Generado por IA · verificar con el pliego" in pagina
    assert "Recomendación preliminar: Dar seguimiento." in pagina and "La decisión es del encargado." in pagina
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in pagina and "<script>alert(1)" not in pagina
    assert "[DOC 1 · pág. 2]" in pagina and "Historial de resúmenes (2)" in pagina


def test_sin_resumen_lo_dice_y_con_la_ia_apagada_no_hay_bloque(carteles, monkeypatch):
    cliente = _panel(carteles, monkeypatch, "openai")
    assert "Todavía no tiene resumen" in cliente.get(f"/oportunidades/{NRO}").text
    assert "Resumen ejecutivo" not in cliente.get(f"/oportunidades/{BAJA}").text   # Baja sin resumen: sin bloque

    _correr(carteles, OpenAISimulado(_ok(), _ok()))
    apagada = _panel(carteles, monkeypatch, "none").get(f"/oportunidades/{NRO}")
    assert apagada.status_code == 200 and "Resumen ejecutivo" not in apagada.text
