"""Lista de verificación del cartel (asistente de elegibilidad, lección 2) con un OpenAI SIMULADO.

Base SINTÉTICA de tests/test_panel.py; requerimientos y perfil INVENTADOS. Nunca se llama a la red ni se gasta.
"""

import dataclasses
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import perfil, usuarios
from app.ai import verificacion
from app.config import load_settings
from app.database import MIGRATIONS_DIR, apply_migrations, connect
from app.historial import Quien
from app.importers.comun import HORA_CR
from app.main import app
from tests.test_panel import CONTRASENA, db, iniciar_sesion, token_csrf  # noqa: F401 (db es una fixture)

NRO = "00000000001"   # «Servicio de monitoreo GPS de vehículos» (test_panel.CARTELES)
ANA = Quien(None, "Ana Sintética")
REQUERIMIENTOS = [
    {"requisito": "Acreditar al menos tres años de experiencia en monitoreo GPS.", "tipo": "experiencia",
     "excluyente": True, "cita": "[DOC 1 · pág. 2]"},
    {"requisito": "Presentar póliza de riesgos del trabajo vigente.", "tipo": "legal", "excluyente": True,
     "cita": "SICOP"},
    {"requisito": "Aportar patente municipal vigente.", "tipo": "legal", "excluyente": False,
     "cita": "[DOC 1 · pág. 4]"},
    {"requisito": "Presentar la póliza de riesgos del trabajo del INS.", "tipo": "legal", "excluyente": False,
     "cita": "[DOC 1 · pág. 9]"},
    {"requisito": "Contar con soporte técnico <script>alert(1)</script> todo el día.", "tipo": "tecnico",
     "excluyente": False, "cita": "no encontrado"},
]
NADA = "no indicado"
RESPUESTA = {"items": [
    {"ref": "R1", "tipo_evidencia": "numero", "minimo": "al menos 3 años", "minimo_numero": "3", "minimo_fecha": NADA,
     "unidad": "años", "igual_a": "ninguno", "citas": ["[DOC 1 · pág. 2]"]},
    {"ref": "R2", "tipo_evidencia": "fecha", "minimo": "vigente al cierre", "minimo_numero": NADA,
     "minimo_fecha": NADA, "unidad": NADA, "igual_a": "ninguno", "citas": ["SICOP"]},
    {"ref": "R3", "tipo_evidencia": "documento", "minimo": "5 años de antigüedad", "minimo_numero": "5",   # inventado
     "minimo_fecha": NADA, "unidad": "años", "igual_a": "ninguno", "citas": ["[DOC 1 · pág. 4]"]},
    {"ref": "R4", "tipo_evidencia": "documento", "minimo": NADA, "minimo_numero": NADA, "minimo_fecha": NADA,
     "unidad": NADA, "igual_a": "R2", "citas": ["[DOC 1 · pág. 9]"]},
    # R5 no viene: igual debe quedar en la lista
]}


class OpenAISimulado:
    """Imita client.responses.create con una respuesta fija y anota lo que se le mandó."""

    def __init__(self, datos=RESPUESTA):
        self.llamadas = []
        self.responses = SimpleNamespace(create=self._crear)
        self.datos = datos

    def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        return SimpleNamespace(status="completed", output_text=json.dumps(self.datos), output=[],
                               model="modelo-simulado", usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
                               incomplete_details=None)


def _settings(db, **extra):
    entorno = {"DATABASE_PATH": str(db), "AI_MODE": "openai", "OPENAI_API_KEY": "clave-simulada",
               "OPENAI_MODEL": "modelo-simulado", "IA_PRECIO_ENTRADA_USD": "1.00", "IA_PRECIO_SALIDA_USD": "5.00",
               "IA_MAX_DAILY_COST": "1.00", **extra}
    return load_settings(env_file=None, environ=entorno)


@pytest.fixture
def base(db):  # noqa: F811
    """La base de test_panel con el resumen SINTÉTICO del cartel NRO y dos elementos del perfil."""
    with closing(connect(db)) as conn:
        conn.execute("INSERT INTO ia_summaries (nro_sicop, prompt_version, modelo, huella, resumen_json, estado,"
                     " creado_en) VALUES (?, 'v2', 'modelo-simulado', ?, ?, 'ok', '2026-11-02T09:00:00-06:00')",
                     (NRO, "a" * 64, json.dumps({"requerimientos": REQUERIMIENTOS}, ensure_ascii=False)))
        ahora = datetime.now(timezone.utc)
        poliza = perfil.crear(conn, "poliza", "Póliza de riesgos del trabajo (INS)", ANA, ahora)
        anos = perfil.crear(conn, "experiencia", "Años de experiencia en GPS y gestión de flotas", ANA, ahora)
        perfil.nueva_version(conn, db.parent / "perfil", anos, perfil.Datos(valor="SECRETO-DEL-PERFIL", numero="14"),
                             None, 1024, ANA, ahora)
    return db, {"poliza": poliza, "anos": anos}


def _generar(db, simulado=None, **extra):
    simulado = simulado or OpenAISimulado()
    with closing(connect(db)) as conn:
        verificacion.generar(conn, _settings(db, **extra), NRO, ANA, cliente=simulado, dormir=lambda s: None)
        return verificacion.listar(conn, NRO), simulado


def _por_texto(items, inicio):
    return next(i for i in items if i.requisito.startswith(inicio))


# --- Generación ---------------------------------------------------------------------------------------------------

def test_cada_requerimiento_tiene_su_item_con_cita_y_el_minimo_no_se_inventa(base):
    db, ids = base
    items, simulado = _generar(db)
    assert len(simulado.llamadas) == 1
    assert len(items) == 4                                        # R4 se juntó con R2
    r1 = _por_texto(items, "Acreditar")
    assert (r1.tipo_evidencia, r1.minimo, r1.minimo_numero, r1.unidad) == ("numero", "al menos 3 años", "3", "años")
    assert r1.citas == ["[DOC 1 · pág. 2]"] and r1.excluyente               # «tres» en palabras cuenta como 3
    r2 = _por_texto(items, "Presentar póliza")
    assert r2.citas == ["SICOP", "[DOC 1 · pág. 9]"] and r2.excluyente     # las dos citas del requisito repetido
    r3 = _por_texto(items, "Aportar patente")
    assert (r3.minimo, r3.minimo_numero) == (NADA, None)                    # el 5 no está en el texto: no indicado
    r5 = _por_texto(items, "Contar con soporte")
    assert (r5.tipo_evidencia, r5.minimo, r5.citas) == ("texto", NADA, [])  # la IA lo omitió y no se perdió
    assert items == [r1, r3, r2, r5]                                        # por página: 2, 4, 9 y sin cita al final
    assert r1.perfil_item_id == ids["anos"] and r2.perfil_item_id == ids["poliza"]
    assert not r1.perfil_confirmado and r3.perfil_item_id is None


def test_el_orden_sigue_al_expediente_documento_y_pagina(base):
    db, _ = base
    items, _ = _generar(db)
    i = items[0]
    casos = {"zip": ["[DOC 2 · Anexos.zip › tecnico.pdf · pág. 1]"], "doc1_p12": ["[DOC 1 · pág. 12]"],
             "sicop": ["SICOP"], "sin_cita": [], "doc1_p3": ["SICOP", "[DOC 1 · pág. 3]"],
             "doc10": ["[DOC 10 · pág. 1]"]}
    orden = sorted(casos, key=lambda k: verificacion._lugar(dataclasses.replace(i, citas=casos[k])))
    assert orden == ["doc1_p3", "doc1_p12", "zip", "doc10", "sicop", "sin_cita"]   # DOC 10 va después de DOC 2
    # Agregado a mano, sin citas: vale la marca escrita en el texto (si no tiene, va al final).
    a_mano = dataclasses.replace(i, citas=[], requisito="Garantía de cumplimiento del 5 % [DOC 1 · pág. 5-6]")
    assert verificacion._lugar(a_mano)[:3] == (0, 1, 5)
    assert verificacion._lugar(dataclasses.replace(a_mano, requisito="Sin marca"))[:3] == (2, 0, 0)


def test_el_prompt_v2_pide_documento_cuando_el_pliego_pide_presentar_algo(base):
    # Revisión de Ivania (2026-11-03): «Sí o no» salía para cosas que el pliego pide presentar (CCSS en
    # «documentos por aportar»). La v1 queda igual: ya se usó.
    v1, v2 = ((verificacion.PROMPTS_DIR / f"lista_verificacion_{v}.md").read_text(encoding="utf-8") for v in ("v1", "v2"))
    v1, v2 = " ".join(v1.split()), " ".join(v2.split())
    assert "si_no: una afirmación (estar al día con la CCSS" in v1
    assert "si_no: SOLO un compromiso que no se prueba con un papel" in v2 and "Si dudas entre documento" in v2
    assert v2.index("documento: si el pliego dice que hay que presentar") < v2.index("si_no:")
    assert "estar al día con la CCSS" in v2.split("documento:")[1].split("numero:")[0]   # la CCSS va en documento
    db, _ = base
    _, simulado = _generar(db)
    assert "si_no: SOLO un compromiso" in " ".join(simulado.llamadas[0]["instructions"].split())
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT prompt_version FROM eligibility_generations").fetchall() == [("v2",)]


def test_lo_que_se_manda_a_la_ia_no_lleva_datos_del_perfil(base):
    db, _ = base
    _, simulado = _generar(db)
    enviado = simulado.llamadas[0]["input"]
    assert "R1 · experiencia · excluyente: sí" in enviado and "EXPEDIENTE:" in enviado
    assert "SECRETO-DEL-PERFIL" not in enviado and "Años de experiencia en GPS y gestión" not in enviado
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT proposito FROM ia_usage").fetchall() == [("verificacion",)]


def test_volver_a_generar_respeta_lo_que_hizo_una_persona(base):
    db, ids = base
    items, _ = _generar(db)
    r1, r3 = _por_texto(items, "Acreditar"), _por_texto(items, "Aportar patente")
    with closing(connect(db)) as conn:
        verificacion.corregir(conn, NRO, r1.id, verificacion.Cambios(
            r1.requisito, "experiencia", "numero", "al menos 4 años", "4", "", "años", True), ANA)
        verificacion.quitar(conn, NRO, r3.id, ANA)
        verificacion.agregar(conn, NRO, verificacion.Cambios(
            "Tener oficina en Costa Rica.", "legal", "si_no", "", "", "", "", False), ANA)
        verificacion.elegir_perfil(conn, NRO, _por_texto(items, "Presentar póliza").id, None, ANA)
    items, _ = _generar(db)                                          # la IA responde lo mismo de antes
    assert _por_texto(items, "Acreditar").minimo == "al menos 4 años"
    assert any(i.requisito == "Tener oficina en Costa Rica." and i.origen == "usuario" for i in items)
    assert not any(i.requisito.startswith("Aportar patente") for i in items)
    poliza = _por_texto(items, "Presentar póliza")
    assert poliza.perfil_item_id is None and poliza.perfil_confirmado       # «ninguno» confirmado se respeta
    with closing(connect(db)) as conn:
        assert [i.requisito for i in verificacion.listar(conn, NRO, activos=False)] == [r3.requisito]
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM eligibility_items")


def test_la_marca_de_pagina_escrita_va_a_cita_y_no_al_titulo(base):
    # Pedido de Ivania (2026-11-03): «1.5 Tamaño de 60 x 25 mm. [DOC 1 · pág. 1]» mostraba la marca en el título.
    db, _ = base
    items, _ = _generar(db)
    r1 = _por_texto(items, "Acreditar")
    with closing(connect(db)) as conn:
        nuevo = verificacion.agregar(conn, NRO, verificacion.Cambios(
            "1.5 Tamaño de 60 x 25 ± 10 mm. [DOC 1 · pág. 1]", "tecnico", "documento", "", "", "", "", False), ANA)
        verificacion.corregir(conn, NRO, r1.id, verificacion.Cambios(
            r1.requisito + " [DOC 1 · pág. 3] [SICOP]", "experiencia", "numero", "", "", "", "", True), ANA)
        items = {i.id: i for i in verificacion.listar(conn, NRO)}
        with pytest.raises(verificacion.VerificacionError, match="Escribe el requisito"):
            verificacion.agregar(conn, NRO, verificacion.Cambios(
                "[DOC 1 · pág. 2]", "tecnico", "documento", "", "", "", "", False), ANA)
    assert (items[nuevo].requisito, items[nuevo].citas) == ("1.5 Tamaño de 60 x 25 ± 10 mm.", ["[DOC 1 · pág. 1]"])
    assert items[r1.id].requisito == r1.requisito                                  # la corrección suma sus citas
    assert items[r1.id].citas == ["[DOC 1 · pág. 2]", "[DOC 1 · pág. 3]", "SICOP"]


@pytest.mark.parametrize("caso", ["sin_resumen", "ia_apagada", "sin_presupuesto"])
def test_no_se_llama_a_openai_cuando_no_corresponde(base, caso):
    db, _ = base
    extra = {}
    with closing(connect(db)) as conn:
        nro = "00000000002" if caso == "sin_resumen" else NRO     # el cartel 2 no tiene resumen
        if caso == "ia_apagada":
            extra["AI_MODE"] = "none"
        if caso == "sin_presupuesto":
            conn.execute("INSERT INTO ia_usage (creado_en, proposito, nro_sicop, modelo, costo_estimado, moneda,"
                         " duracion_s, intentos, resultado) VALUES (?, 'resumen', ?, 'm', '1.50', 'USD', 1, 1, 'ok')",
                         (datetime.now(HORA_CR).isoformat(timespec="seconds"), NRO))
        simulado = OpenAISimulado()
        with pytest.raises(verificacion.VerificacionError):
            verificacion.generar(conn, _settings(db, **extra), nro, ANA, cliente=simulado)
    assert simulado.llamadas == []


def test_una_respuesta_rota_no_cambia_la_lista(base):
    db, _ = base
    _generar(db)
    rota = OpenAISimulado()
    rota.responses = SimpleNamespace(create=lambda **k: SimpleNamespace(
        status="completed", output_text="no es json", output=[], model="m",
        usage=SimpleNamespace(input_tokens=10, output_tokens=1), incomplete_details=None))
    with closing(connect(db)) as conn:
        antes = verificacion.listar(conn, NRO)
        with pytest.raises(verificacion.VerificacionError, match="no sirvió"):
            verificacion.generar(conn, _settings(db), NRO, ANA, cliente=rota)
        assert verificacion.listar(conn, NRO) == antes
        assert verificacion.ultima_generacion(conn, NRO).estado == "fallido"


def test_la_propuesta_de_perfil_por_palabras_del_titulo(base):
    db, ids = base
    with closing(connect(db)) as conn:
        otro = perfil.crear(conn, "certificacion", "Certificado ISO de calidad del servicio", ANA, datetime.now(timezone.utc))
        assert verificacion.proponer_perfil(conn, "Aportar certificado de calidad ISO vigente", {}) == otro
        assert verificacion.proponer_perfil(conn, "Ofertar en colones", {}) is None


# --- Pantalla -----------------------------------------------------------------------------------------------------

def test_empezar_el_asistente_genera_la_lista_y_ya_no_hay_pagina(base, monkeypatch):
    """Pedido de Ivania (2026-11-09): la lista ya no tiene página; «Empezar el asistente» la genera si falta."""
    from app import seguimiento
    db, _ = base
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setenv("ASSISTANT_ENABLED", "true")
    monkeypatch.setenv("AI_MODE", "none")                     # las preguntas no van a OpenAI
    original = verificacion.generar
    monkeypatch.setattr(verificacion, "generar", lambda conn, settings, nro, quien: original(
        conn, _settings(db), nro, quien, cliente=OpenAISimulado(), dormir=lambda s: None))   # OpenAI SIMULADO
    with closing(connect(db)) as conn:
        admin = usuarios.crear_usuario(conn, "admin@ejemplo.test", "Admin Sintético", CONTRASENA, usuarios.ADMIN)
        seguimiento.abrir(conn, NRO, Quien(admin, "Admin Sintético"), datetime.now(HORA_CR))
        assert verificacion.listar(conn, NRO) == []
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, "admin@ejemplo.test").status_code == 303
    html = cliente.get(f"/oportunidades/{NRO}").text
    assert "Lista de verificación para el asistente" not in html and "Primero la IA saca los requisitos" in html
    assert cliente.get(f"/oportunidades/{NRO}/verificacion").status_code == 404
    r = cliente.post(f"/oportunidades/{NRO}/asistente/empezar", data={"csrf_token": token_csrf(html)},
                     follow_redirects=False)
    assert r.status_code == 303
    with closing(connect(db)) as conn:
        assert len(verificacion.listar(conn, NRO)) == 4
        assert conn.execute("SELECT COUNT(*) FROM eligibility_sessions").fetchone()[0] == 1


def test_el_comando_ia_verificar(base, capsys):
    from app.cli import ia_verificar_cmd
    db, _ = base
    assert ia_verificar_cmd(_settings(db), "12ab") == 1
    assert ia_verificar_cmd(_settings(db), NRO, cliente=OpenAISimulado()) == 0
    salida = capsys.readouterr().out
    assert "4 requisitos" in salida and "EXCLUYENTE · Acreditar" in salida and "mínimo: al menos 3 años" in salida


# --- Migración 0030 -----------------------------------------------------------------------------------------------

def test_0030_conserva_ia_usage_y_las_referencias_de_los_resumenes(tmp_path):
    hasta_0029 = tmp_path / "hasta_0029"
    hasta_0029.mkdir()
    for archivo in MIGRATIONS_DIR.glob("*.sql"):
        if archivo.name < "0030":
            shutil.copy(archivo, hasta_0029)
    base = tmp_path / "sicop.db"
    apply_migrations(base, hasta_0029)
    with closing(sqlite3.connect(base)) as conn:
        conn.execute("INSERT INTO tenders (nro_sicop, descripcion, content_hash, first_seen, last_seen)"
                     " VALUES (?, 'x', 'h', 't', 't')", (NRO,))
        conn.execute("INSERT INTO ia_usage (creado_en, proposito, nro_sicop, modelo, duracion_s, intentos, resultado)"
                     " VALUES ('2026-11-02', 'resumen', ?, 'm', 1, 1, 'ok')", (NRO,))
        conn.execute("INSERT INTO ia_summaries (nro_sicop, prompt_version, modelo, huella, estado, motivo, ia_usage_id,"
                     " creado_en) VALUES (?, 'v1', 'm', ?, 'fallido', 'prueba', 1, 't')", (NRO, "a" * 64))
        conn.commit()
    assert apply_migrations(base) == ["0030_lista_verificacion.sql", "0031_asistente.sql", "0032_archivo_pendiente.sql", "0033_resultado_elegibilidad.sql", "0034_revision_rapida.sql", "0035_perfil_tipos_nuevos.sql", "0036_reportes_cartel.sql", "0037_ayuda_votos.sql", "0038_cumplimiento_resumen.sql", "0039_reporte_tres_paginas.sql", "0040_enriquecimiento_remoto.sql", "0041_oferta_borrador.sql", "0042_respuesta_tecnica.sql", "0043_oferta_completa.sql", "0044_asistente_chat.sql"]
    with closing(connect(base)) as conn:
        assert conn.execute("SELECT id, proposito FROM ia_usage").fetchall() == [(1, "resumen")]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA foreign_keys").fetchone() == (1,)
        with pytest.raises(sqlite3.IntegrityError, match="no se borra"):
            conn.execute("DELETE FROM ia_usage")
    assert apply_migrations(base) == []
