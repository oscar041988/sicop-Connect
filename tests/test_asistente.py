"""Asistente de elegibilidad (lección 3): recorre la lista, pregunta sin suponer y guarda las respuestas.

Base SINTÉTICA de tests/test_panel.py; requisitos, perfil y documentos INVENTADOS en tmp_path (nunca de Hermatix).
Nunca se llama a OpenAI.
"""

import io
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app import asistente, perfil
from app.ai import asistente as ia_asistente
from app.ai import verificacion
from app.archivos import ArchivoInvalido
from app.config import load_settings
from app.database import connect
from app.historial import Quien
from tests.test_panel import db  # noqa: F401 (db es una fixture)

NRO = "00000000001"
ANA = Quien(None, "Ana Sintética")
LUIS = Quien(None, "Luis Sintético")
AHORA = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
PDF = b"%PDF-1.4\n% permiso SINTETICO TEXTO-UNICO-DEL-ARCHIVO\n"


def _req(texto, evidencia="si_no", excluyente=False, unidad="", minimo="", numero=""):
    return verificacion.Cambios(texto, "legal", evidencia, minimo, numero, "", unidad, excluyente)


@pytest.fixture
def lista(db, tmp_path):  # noqa: F811
    """Lista SINTÉTICA del cartel NRO: excluyentes y no excluyentes en distintas páginas, una multa y una condición."""
    with closing(connect(db)) as conn:
        ids = {
            "patente": verificacion.agregar(conn, NRO, _req("Aportar patente municipal vigente. [DOC 1 · pág. 9]",
                                                            "documento"), ANA),
            "anos": verificacion.agregar(conn, NRO, _req(
                "Al menos tres años de experiencia en GPS. [DOC 1 · pág. 7]", "numero", True, "años",
                "al menos 3 años", "3"), ANA),
            "multa": verificacion.agregar(conn, NRO, _req(
                "Multa / cláusula penal: 1 % por día de atraso. [DOC 1 · pág. 10]", "texto"), ANA),
            "sicop": verificacion.agregar(conn, NRO, _req("Ofertar por SICOP. [DOC 1 · pág. 1]", "si_no", True), ANA),
            "cond": verificacion.agregar(conn, NRO, _req(
                "Condición de la institución: pago a 30 días. [DOC 1 · pág. 4]", "texto"), ANA),
            "cierre": verificacion.agregar(conn, NRO, _req("Fecha de inicio del servicio. [DOC 1 · pág. 3]", "fecha"),
                                           ANA),
            "soporte": verificacion.agregar(conn, NRO, _req("Soporte <script>alert(1)</script> 24/7. [DOC 1 · pág. 2]",
                                                            "texto"), ANA),
        }
    settings = load_settings(env_file=None, environ={
        "DATABASE_PATH": str(db), "ASSISTANT_DOCS_DIR": str(tmp_path / "asistente"),
        "PROFILE_DOCS_DIR": str(tmp_path / "perfil"), "ASSISTANT_DOC_MAX_MB": "1"})
    return db, ids, settings


def _pasos(db):
    with closing(connect(db)) as conn:
        return asistente.recorrido(conn, NRO, AHORA.date())


def _responder(db, settings, item_id, quien=ANA, archivo=None, guardar=False, **entrada):
    with closing(connect(db)) as conn:
        return asistente.responder(conn, settings, NRO, item_id, asistente.Entrada(**entrada),
                                   (io.BytesIO(archivo), "permiso.pdf") if archivo is not None else None, quien,
                                   AHORA, guardar_en_perfil=guardar)


def _empezar(db):
    with closing(connect(db)) as conn:
        return asistente.empezar(conn, NRO, ANA, AHORA)


# --- Orden y preguntas --------------------------------------------------------------------------------------------

def test_primero_los_excluyentes_luego_el_resto_y_no_pregunta_multas_ni_condiciones(lista):
    db, ids, _ = lista
    _empezar(db)
    orden = [p.item.id for p in _pasos(db)]
    assert orden == [ids["sicop"], ids["anos"], ids["soporte"], ids["cierre"], ids["patente"]]   # cada grupo por página
    with closing(connect(db)) as conn:
        assert [i.id for i in asistente.informativos(conn, NRO)] == [ids["cond"], ids["multa"]]
    assert asistente.siguiente(_pasos(db)).item.id == ids["sicop"]


def test_la_pregunta_de_la_app_trae_el_requisito_su_minimo_y_la_cita(lista):
    db, ids, _ = lista
    pasos = {p.item.id: p for p in _pasos(db)}
    anos = pasos[ids["anos"]]
    assert anos.origen == "app"
    assert anos.pregunta == ("El cartel pide: «Al menos tres años de experiencia en GPS.» (mínimo: al menos 3 años)."
                             " [DOC 1 · pág. 7] ¿Cuántos años tiene Hermatix?")
    assert "Súbelo" in pasos[ids["patente"]].pregunta


def test_la_pregunta_de_la_ia_vale_mientras_no_corrijan_el_requisito(lista):
    db, ids, _ = lista
    s = _empezar(db)
    with closing(connect(db)) as conn:
        uso = conn.execute("INSERT INTO ia_usage (creado_en, proposito, modelo, duracion_s, intentos, resultado)"
                           " VALUES ('2026-11-03', 'asistente', 'm', 1, 1, 'ok')").lastrowid
        conn.commit()
        item = next(i for i in verificacion.listar(conn, NRO) if i.id == ids["anos"])
        asistente.guardar_preguntas(conn, s.id, {item.id: (item.requisito, "¿Cuántos años lleva Hermatix con GPS?")},
                                    uso, "v1", AHORA)
    paso = next(p for p in _pasos(db) if p.item.id == ids["anos"])
    assert (paso.origen, paso.pregunta) == ("ia", "¿Cuántos años lleva Hermatix con GPS? [DOC 1 · pág. 7]")
    with closing(connect(db)) as conn:
        verificacion.corregir(conn, NRO, ids["anos"], _req("Al menos cinco años de experiencia en GPS.", "numero", True,
                                                           "años"), ANA)
    paso = next(p for p in _pasos(db) if p.item.id == ids["anos"])
    assert paso.origen == "app" and "cinco años" in paso.pregunta


# --- Perfil sin suponer -------------------------------------------------------------------------------------------

def test_el_dato_vigente_del_perfil_se_muestra_pero_no_cuenta_sin_confirmar(lista):
    db, ids, settings = lista
    _empezar(db)
    with closing(connect(db)) as conn:
        anos = perfil.crear(conn, "experiencia", "Años de experiencia en GPS", ANA, AHORA)
        perfil.nueva_version(conn, settings.profile_docs_dir, anos, perfil.Datos(numero="8", unidad="años"), None,
                             1024, ANA, AHORA)
        patente = perfil.crear(conn, "permiso", "Patente municipal", ANA, AHORA)
        perfil.nueva_version(conn, settings.profile_docs_dir, patente, perfil.Datos(valor="Patente",
                             vence_el="2026-10-01"), None, 1024, ANA, AHORA)                          # vencida
        verificacion.elegir_perfil(conn, NRO, ids["anos"], anos, ANA)
        verificacion.elegir_perfil(conn, NRO, ids["patente"], patente, ANA)
    pasos = {p.item.id: p for p in _pasos(db)}
    assert pasos[ids["anos"]].perfil.vigente.numero == "8" and pasos[ids["anos"]].respuesta is None
    assert pasos[ids["patente"]].perfil is None                              # vencido: se pregunta
    with closing(connect(db)) as conn:
        asistente.confirmar_perfil(conn, NRO, ids["anos"], ANA, AHORA)
        with pytest.raises(asistente.AsistenteInvalido, match="no tiene un dato vigente"):
            asistente.confirmar_perfil(conn, NRO, ids["patente"], ANA, AHORA)
    r = next(p for p in _pasos(db) if p.item.id == ids["anos"]).respuesta
    assert (r.fuente, r.valor_numero, r.unidad) == ("perfil", "8", "años")


# --- Respuestas ---------------------------------------------------------------------------------------------------

def test_cada_tipo_pide_su_dato_exacto(lista):
    db, ids, settings = lista
    _empezar(db)
    with pytest.raises(asistente.AsistenteInvalido, match="no es un número"):
        _responder(db, settings, ids["anos"], valor_numero="varios años")
    with pytest.raises(asistente.AsistenteInvalido, match="«Sí» o «No»"):
        _responder(db, settings, ids["sicop"])
    with pytest.raises(asistente.AsistenteInvalido, match="Escribe la fecha"):
        _responder(db, settings, ids["cierre"])
    with pytest.raises(asistente.AsistenteInvalido, match="Sube el documento"):
        _responder(db, settings, ids["patente"])
    with pytest.raises(asistente.AsistenteInvalido, match="solo para documentos"):
        _responder(db, settings, ids["anos"], estado="no_lo_tiene")
    with pytest.raises(asistente.AsistenteInvalido, match="no está en el asistente"):
        _responder(db, settings, ids["multa"], valor_texto="x")
    _responder(db, settings, ids["anos"], valor_numero="8")
    _responder(db, settings, ids["sicop"], valor_si_no="1")
    _responder(db, settings, ids["cierre"], estado="no_se")
    pasos = {p.item.id: p for p in _pasos(db)}
    assert pasos[ids["anos"]].respuesta.resumen == "8 años"
    assert pasos[ids["sicop"]].respuesta.resumen == "Sí"
    assert pasos[ids["cierre"]].respuesta.resumen == "Todavía no lo sé"
    assert asistente.avance(list(pasos.values())) == {"total": 5, "respondidos": 3, "excluyentes": 2,
                                                       "excluyentes_respondidos": 2, "no_se": 1}


def test_documento_validado_y_fuera_de_git(lista):
    db, ids, settings = lista
    _empezar(db)
    with pytest.raises(ArchivoInvalido, match="no es un PDF de verdad"):
        _responder(db, settings, ids["patente"], archivo=b"no soy un pdf")
    with pytest.raises(ArchivoInvalido, match="ASSISTANT_DOC_MAX_MB"):
        _responder(db, settings, ids["patente"], archivo=PDF + b"x" * (1024 * 1024))
    rid = _responder(db, settings, ids["patente"], archivo=PDF, vence_el="2027-01-15")
    with closing(connect(db)) as conn:
        ruta, r = asistente.documento(conn, settings.assistant_docs_dir, NRO, rid)
        assert ruta.parent == settings.assistant_docs_dir / NRO and ruta.read_bytes() == PDF
        assert r.resumen == "permiso.pdf · vence 15/01/2027"
        assert asistente.documento(conn, settings.assistant_docs_dir, "00000000002", rid) is None   # otro cartel


def test_con_send_documents_true_no_se_guarda_ni_se_envia_nada(lista):
    db, ids, settings = lista
    _empezar(db)
    con_true = load_settings(env_file=None, environ={**settings.raw, "ASSISTANT_SEND_DOCUMENTS": "true"})
    with pytest.raises(asistente.AsistenteInvalido, match="todavía no está construido"):
        _responder(db, con_true, ids["patente"], archivo=PDF)
    assert not settings.assistant_docs_dir.exists()
    assert next(p for p in _pasos(db) if p.item.id == ids["patente"]).respuesta is None


def test_pausar_y_retomar_otra_persona_sigue_donde_quedo(lista):
    db, ids, settings = lista
    _empezar(db)
    _responder(db, settings, ids["sicop"], valor_si_no="1")
    assert _empezar(db).iniciada_por == ANA.nombre                         # retomar no duplica la sesión
    assert asistente.siguiente(_pasos(db)).item.id == ids["anos"]          # otra conexión, otro día: sigue ahí
    _responder(db, settings, ids["anos"], LUIS, valor_numero="8")
    _responder(db, settings, ids["anos"], LUIS, valor_numero="9")         # cambiar la respuesta agrega otra
    with closing(connect(db)) as conn:
        s = asistente.sesion(conn, NRO)
        assert [r.valor_numero for r in asistente.historial_de(conn, s.id, ids["anos"])] == ["9", "8"]
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE eligibility_answers SET valor_numero = '20'")
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM eligibility_answers")
        acciones = [a for (a,) in conn.execute("SELECT accion FROM audit_log WHERE accion LIKE '%asistente%'")]
        detalles = " ".join(d for (d,) in conn.execute("SELECT detalle FROM audit_log"))
    assert acciones.count("responder_asistente") == 3 and "empezar_asistente" in acciones
    assert "9" not in detalles.replace(NRO, "").replace(f"#{ids['anos']}", "")   # el contenido no va al historial
    assert asistente.siguiente(_pasos(db)).item.id == ids["soporte"]


def test_guardar_tambien_en_el_perfil(lista):
    db, ids, settings = lista
    _empezar(db)
    with closing(connect(db)) as conn:
        patente = perfil.crear(conn, "permiso", "Patente municipal", ANA, AHORA)
        verificacion.elegir_perfil(conn, NRO, ids["patente"], patente, ANA)
    _responder(db, settings, ids["patente"], archivo=PDF, vence_el="2027-01-15", guardar=True)
    with closing(connect(db)) as conn:
        e = perfil.obtener(conn, patente, AHORA.date())
    assert (e.estado, e.vigente.vence_el, e.vigente.archivo_nombre) == ("vigente", "2027-01-15", "permiso.pdf")
    with pytest.raises(asistente.AsistenteInvalido, match="no se puede guardar en el perfil"):
        _responder(db, settings, ids["sicop"], valor_si_no="1", guardar=True)


def test_sin_lista_no_se_empieza(db):  # noqa: F811
    with closing(connect(db)) as conn:
        with pytest.raises(asistente.AsistenteInvalido, match="no tiene lista"):
            asistente.empezar(conn, NRO, ANA, AHORA)


# --- Preguntas redactadas con IA (OpenAI SIMULADO) ----------------------------------------------------------------

class OpenAISimulado:
    """Imita client.responses.create: una pregunta por cada R de la lista recibida; anota lo que se le mandó."""

    def __init__(self, falla=False):
        self.llamadas, self.falla = [], falla
        self.responses = SimpleNamespace(create=self._crear)

    def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        if self.falla:
            raise RuntimeError("simulado")
        refs = re.findall(r"^(R\d+) ·", kwargs["input"], flags=re.M)
        datos = {"preguntas": [{"ref": r, "pregunta": f"Pregunta <b>{r}</b> de la IA."} for r in refs]}
        return SimpleNamespace(status="completed", output_text=json.dumps(datos), output=[], model="modelo-simulado",
                               usage=SimpleNamespace(input_tokens=500, output_tokens=100), incomplete_details=None)


def _con_ia(settings, **extra):
    return load_settings(env_file=None, environ={
        **settings.raw, "AI_MODE": "openai", "OPENAI_API_KEY": "clave-simulada", "OPENAI_MODEL": "modelo-simulado",
        "IA_PRECIO_ENTRADA_USD": "1.00", "IA_PRECIO_SALIDA_USD": "5.00", "IA_MAX_DAILY_COST": "1.00", **extra})


def _redactar(db, settings, simulado):
    with closing(connect(db)) as conn:
        return ia_asistente.redactar(conn, settings, NRO, ANA, AHORA, cliente=simulado, dormir=lambda s: None)


def test_la_ia_redacta_en_tandas_y_solo_recibe_la_lista(lista, monkeypatch):
    db, ids, settings = lista
    _empezar(db)
    with closing(connect(db)) as conn:
        anos = perfil.crear(conn, "experiencia", "Años de experiencia en GPS", ANA, AHORA)
        perfil.nueva_version(conn, settings.profile_docs_dir, anos, perfil.Datos(valor="SECRETO-DEL-PERFIL",
                             numero="8"), None, 1024, ANA, AHORA)
        verificacion.elegir_perfil(conn, NRO, ids["anos"], anos, ANA)
    _responder(db, settings, ids["patente"], archivo=PDF)                      # un documento ya subido
    monkeypatch.setattr(ia_asistente, "TANDA", 2)
    simulado = OpenAISimulado()
    r = _redactar(db, _con_ia(settings), simulado)
    assert (r.redactadas, r.motivo) == (5, None) and len(simulado.llamadas) == 3     # 5 requisitos en tandas de 2
    enviado = " ".join(c["input"] + c["instructions"] for c in simulado.llamadas)
    assert "TEXTO-UNICO-DEL-ARCHIVO" not in enviado and "SECRETO-DEL-PERFIL" not in enviado
    assert "Multa" not in enviado and "Condición de la institución" not in enviado
    assert "Nunca supongas" in simulado.llamadas[0]["instructions"]
    pasos = {p.item.id: p for p in _pasos(db)}
    assert all(p.origen == "ia" for p in pasos.values())
    assert pasos[ids["sicop"]].pregunta == "Pregunta <b>R1</b> de la IA. [DOC 1 · pág. 1]"   # la app agrega la cita
    assert _redactar(db, _con_ia(settings), simulado).redactadas == 0 and len(simulado.llamadas) == 3   # ya están
    with closing(connect(db)) as conn:
        assert {p for (p,) in conn.execute("SELECT proposito FROM ia_usage")} == {"asistente"}


@pytest.mark.parametrize("caso", ["ia_apagada", "sin_presupuesto", "fallo"])
def test_sin_ia_quedan_las_preguntas_de_la_app(lista, caso):
    db, ids, settings = lista
    _empezar(db)
    simulado = OpenAISimulado(falla=caso == "fallo")
    if caso == "ia_apagada":
        usar = settings
    elif caso == "sin_presupuesto":
        usar = _con_ia(settings, IA_MAX_DAILY_COST="0")
    else:
        usar = _con_ia(settings)
    r = _redactar(db, usar, simulado)
    assert r.redactadas == 0 and "preguntas de la app" in r.motivo
    assert len(simulado.llamadas) == (1 if caso == "fallo" else 0)
    assert all(p.origen == "app" for p in _pasos(db))
