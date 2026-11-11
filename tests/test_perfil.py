"""Perfil de Hermatix (asistente de elegibilidad, lección 1): datos y documentos con vencimiento e historial.

Base SINTÉTICA de tests/test_panel.py; documentos INVENTADOS en tmp_path (nunca de Hermatix). Nunca toca data/.
"""

import io
import sqlite3
import subprocess
import zipfile
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import perfil, respaldo, usuarios
from app.database import apply_migrations, connect
from app.historial import Quien
from app.main import app
from tests.test_panel import CONTRASENA, db, iniciar_sesion, token_csrf  # noqa: F401 (db es una fixture)

PDF = b"%PDF-1.4\n% documento SINTETICO del perfil\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"SINTETICO" * 4
AHORA = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
HOY = date(2026, 11, 2)
ANA = Quien(None, "Ana Sintética")


@pytest.fixture
def entorno(db, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setenv("PROFILE_DOCS_DIR", str(tmp_path / "perfil"))
    with closing(connect(db)) as conn:
        usuarios.crear_usuario(conn, "admin@ejemplo.test", "Admin Sintética", CONTRASENA, rol=usuarios.ADMIN)
        usuarios.crear_usuario(conn, "encargada@ejemplo.test", "Encargada Sintética", CONTRASENA)
    return db, tmp_path / "perfil"


def _cliente(email):
    cliente = TestClient(app)
    assert iniciar_sesion(cliente, email).status_code == 303
    return cliente


def _version(conn, base, item_id, archivo=None, nombre="poliza.pdf", **datos):
    return perfil.nueva_version(conn, base, item_id, perfil.Datos(**datos),
                                (io.BytesIO(archivo), nombre) if archivo is not None else None,
                                1024 * 1024, ANA, AHORA)


# --- Datos, historial y estados -----------------------------------------------------------------------------------

def test_crear_y_reemplazar_conserva_el_historial(entorno):
    db, base = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "poliza", "Póliza de riesgos del trabajo", ANA, AHORA)
        assert perfil.obtener(conn, item, HOY).estado == "pendiente"
        primera = _version(conn, base, item, PDF, valor="Póliza INS sintética", vence_el="2026-12-31")
        segunda = _version(conn, base, item, PDF + b"renovada", valor="Póliza renovada", vence_el="2027-12-31")
        elemento = perfil.obtener(conn, item, HOY)
        assert elemento.vigente.id == segunda and elemento.vigente.valor == "Póliza renovada"
        assert [v.id for v in perfil.versiones(conn, item)] == [segunda, primera]
        assert len(list((base / str(item)).glob("*.pdf"))) == 2
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM company_profile_versions WHERE id = ?", (primera,))
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE company_profile_versions SET valor = 'otro' WHERE id = ?", (primera,))
        with pytest.raises(perfil.PerfilInvalido, match="Ya existe"):
            perfil.crear(conn, "poliza", "PÓLIZA de riesgos del trabajo", ANA, AHORA)


@pytest.mark.parametrize("vence, estado, dias", [
    ("2026-11-01", "vencido", -1), ("2026-11-02", "por_vencer", 0), ("2026-12-02", "por_vencer", 30),
    ("2026-12-03", "vigente", 31), (None, "vigente", None),
])
def test_estado_segun_el_vencimiento(vence, estado, dias):
    v = perfil.Version(1, 1, "x", None, None, None, vence, False, None, None, None, None, "Ana", "2026-11-02")
    assert perfil.estado_de(v, HOY) == (estado, dias)
    assert perfil.estado_de(None, HOY) == ("pendiente", None)


def test_pendiente_numero_y_fechas(entorno):
    db, base = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "experiencia", "Años de experiencia en GPS", ANA, AHORA)
        _version(conn, base, item, numero="14", unidad="años")
        assert perfil.obtener(conn, item, HOY).vigente.numero == "14"
        perfil.marcar_pendiente(conn, item, "falta la declaración jurada", ANA, AHORA)
        assert perfil.obtener(conn, item, HOY).estado == "pendiente"
        for datos, mensaje in [({"numero": "varios"}, "no es un número"), ({"vence_el": "31/12/2026"}, "fecha"),
                               ({"valor": "x", "vigente_desde": "2027-01-01", "vence_el": "2026-01-01"}, "antes"),
                               ({}, "Escribe un valor")]:
            with pytest.raises(perfil.PerfilInvalido, match=mensaje):
                _version(conn, base, item, **datos)


def test_las_sugerencias_que_ya_existen_no_se_repiten(entorno):
    db, _ = entorno
    with closing(connect(db)) as conn:
        antes = perfil.sugerencias(conn)
        assert "Póliza de riesgos del trabajo (INS)" in antes["poliza"]
        perfil.crear(conn, "poliza", "Póliza de riesgos del trabajo (INS)", ANA, AHORA)
        assert "Póliza de riesgos del trabajo (INS)" not in perfil.sugerencias(conn).get("poliza", [])


def test_tipos_nuevos_capacidad_y_evaluacion_con_la_parte_a(entorno):
    """Migración 0035 (2026-11-04): la parte A del perfil trae soporte, taller, PYME, ISO 14001…"""
    db, _ = entorno
    with closing(connect(db)) as conn:
        sugeridas = perfil.sugerencias(conn)
        assert "Soporte técnico (horario y tiempo de atención)" in sugeridas["capacidad"]
        assert "Condición PYME (certificación del MEIC)" in sugeridas["evaluacion"]
        soporte = perfil.crear(conn, "capacidad", "Soporte técnico (horario y tiempo de atención)", ANA, AHORA)
        pyme = perfil.crear(conn, "evaluacion", "Condición PYME (certificación del MEIC)", ANA, AHORA)
        assert (perfil.obtener(conn, soporte, HOY).tipo_texto, perfil.obtener(conn, pyme, HOY).tipo_texto) == (
            "Capacidad", "Evaluación")
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute("INSERT INTO company_profile_items (tipo, titulo, creado_por_nombre, created_at)"
                         " VALUES ('inventado', 'x', 'Ana', 't')")


def test_0035_conserva_los_elementos_sus_versiones_y_las_referencias(tmp_path):
    from app.database import MIGRATIONS_DIR
    import shutil
    hasta_0034 = tmp_path / "hasta_0034"
    hasta_0034.mkdir()
    for archivo in MIGRATIONS_DIR.glob("*.sql"):
        if archivo.name < "0035":
            shutil.copy(archivo, hasta_0034)
    base = tmp_path / "sicop.db"
    apply_migrations(base, hasta_0034)
    with closing(sqlite3.connect(base)) as conn:
        conn.execute("INSERT INTO company_profile_items (tipo, titulo, creado_por_nombre, created_at)"
                     " VALUES ('experiencia', 'Años de experiencia', 'Ana', 't')")
        conn.execute("INSERT INTO company_profile_versions (item_id, numero, cargado_por_nombre, created_at)"
                     " VALUES (1, '8', 'Ana', 't')")
        conn.commit()
    assert apply_migrations(base) == ["0035_perfil_tipos_nuevos.sql", "0036_reportes_cartel.sql", "0037_ayuda_votos.sql", "0038_cumplimiento_resumen.sql", "0039_reporte_tres_paginas.sql", "0040_enriquecimiento_remoto.sql", "0041_oferta_borrador.sql", "0042_respuesta_tecnica.sql", "0043_oferta_completa.sql", "0044_asistente_chat.sql", "0045_oferta_versiones.sql"]
    with closing(connect(base)) as conn:
        assert conn.execute("SELECT id, tipo, titulo FROM company_profile_items").fetchall() == [
            (1, "experiencia", "Años de experiencia")]
        assert conn.execute("SELECT item_id, numero FROM company_profile_versions").fetchall() == [(1, "8")]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM company_profile_items")


# --- Documentos: solo PDF e imágenes de verdad ----------------------------------------------------------------------

@pytest.mark.parametrize("contenido, nombre, mensaje", [
    (b"MZ\x90\x00 programa", "poliza.pdf", "no es un PDF de verdad"),
    (PDF, "foto.png", "no es un PNG de verdad"),
    (PDF, "carta.docx", "solo PDF e imágenes"),
    (b"", "vacio.pdf", "está vacío"),
])
def test_un_documento_falso_o_no_permitido_se_rechaza(entorno, contenido, nombre, mensaje):
    db, base = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "permiso", "Permiso sanitario", ANA, AHORA)
        with pytest.raises(perfil.ArchivoInvalido, match=mensaje):
            _version(conn, base, item, contenido, nombre)
        assert perfil.versiones(conn, item) == []
    assert not any(p.is_file() for p in base.rglob("*"))           # ni el temporal queda


def test_un_documento_muy_grande_se_corta(entorno):
    db, base = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "permiso", "Patente", ANA, AHORA)
        with pytest.raises(perfil.ArchivoInvalido, match="supera el límite"):
            _version(conn, base, item, PDF + b"x" * (1024 * 1024), "patente.pdf")


# --- Páginas: los dos niveles ven; solo administradores cargan ------------------------------------------------------

def _agregar(cliente, **campos):
    token = token_csrf(cliente.get("/perfil").text)
    archivo = campos.pop("archivo", None)
    files = {"archivo": archivo} if archivo else None
    return cliente.post("/perfil", data={"csrf_token": token, **campos}, files=files, follow_redirects=False)


def test_la_administradora_agrega_con_documento_y_la_encargada_lo_ve_y_descarga(entorno):
    db, _ = entorno
    admin, encargada = _cliente("admin@ejemplo.test"), _cliente("encargada@ejemplo.test")
    vence = (date.today() + timedelta(days=10)).isoformat()
    r = _agregar(admin, tipo="poliza", titulo="Póliza de riesgos del trabajo", valor="Póliza sintética",
                 vence_el=vence, archivo=("poliza.pdf", PDF, "application/pdf"))
    assert r.status_code == 303
    url = r.headers["location"]
    html = encargada.get("/perfil").text
    assert "Póliza de riesgos del trabajo" in html and "Por vencer" in html
    assert "Revisar pronto" not in html                            # sin cuadro de aviso (Ivania, 2026-11-09)
    assert 'action="/perfil"' not in html                          # la encargada no ve los formularios
    item = int(url.rsplit("/", 1)[1])
    with closing(connect(db)) as conn:
        version = perfil.versiones(conn, item)[0].id
    descarga = encargada.get(f"/perfil/{item}/versiones/{version}/archivo")
    assert descarga.status_code == 200 and descarga.content == PDF
    assert descarga.headers["x-content-type-options"] == "nosniff"
    assert descarga.headers["content-disposition"].startswith("attachment")
    ver = encargada.get(f"/perfil/{item}/versiones/{version}/ver")
    assert ver.status_code == 200 and ver.headers["content-disposition"].startswith("inline")
    with closing(sqlite3.connect(db)) as conn:
        accesos = conn.execute("SELECT actor, accion FROM audit_log WHERE accion LIKE '%documento_perfil'"
                               " ORDER BY id").fetchall()
    assert accesos == [("Encargada Sintética", "descargar_documento_perfil"),
                       ("Encargada Sintética", "ver_documento_perfil")]
    assert "Encargada Sintética" in encargada.get(url).text.split("Quién vio o descargó", 1)[1]


def test_una_encargada_no_puede_cargar_ni_cambiar(entorno):
    db, _ = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "legal", "Al día con la CCSS", ANA, AHORA)
    encargada = _cliente("encargada@ejemplo.test")
    token = token_csrf(encargada.get("/oportunidades").text)
    for url, datos in [("/perfil", {"tipo": "legal", "titulo": "Otro"}), (f"/perfil/{item}/version", {"valor": "sí"}),
                       (f"/perfil/{item}/pendiente", {})]:
        r = encargada.post(url, data={"csrf_token": token, **datos}, follow_redirects=False)
        assert r.status_code == 403, url
    with closing(connect(db)) as conn:
        assert perfil.versiones(conn, item) == [] and len(perfil.listar(conn)) == 1


def test_sin_sesion_no_se_ve_ni_se_descarga(entorno):
    db, base = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "permiso", "Patente", ANA, AHORA)
        version = _version(conn, base, item, PDF, "patente.pdf", valor="Patente sintética")
    anonimo = TestClient(app)
    for url in ("/perfil", f"/perfil/{item}", f"/perfil/{item}/versiones/{version}/archivo"):
        r = anonimo.get(url, follow_redirects=False)
        assert r.status_code == 303 and "/login" in r.headers["location"], url


def test_documento_de_otro_elemento_o_inexistente_da_404(entorno):
    db, base = entorno
    with closing(connect(db)) as conn:
        uno = perfil.crear(conn, "permiso", "Patente", ANA, AHORA)
        otro = perfil.crear(conn, "permiso", "Permiso sanitario", ANA, AHORA)
        version = _version(conn, base, uno, PDF, "patente.pdf")
    admin = _cliente("admin@ejemplo.test")
    for url in (f"/perfil/{otro}/versiones/{version}/archivo", f"/perfil/{uno}/versiones/999/archivo",
                f"/perfil/999/versiones/{version}/ver", "/perfil/999"):
        assert admin.get(url).status_code == 404, url
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM audit_log WHERE accion LIKE '%documento_perfil'").fetchone() == (0,)


def test_un_error_en_el_formulario_no_crea_nada(entorno):
    db, _ = entorno
    admin = _cliente("admin@ejemplo.test")
    r = _agregar(admin, tipo="permiso", titulo="Patente", numero="muchos")
    assert r.status_code == 400 and "no es un número" in r.text and 'value="Patente"' in r.text
    r = _agregar(admin, tipo="permiso", titulo="Patente", archivo=("patente.pdf", b"falso", "application/pdf"))
    assert r.status_code == 400 and "se agregó como pendiente" in r.text
    with closing(connect(db)) as conn:
        assert [e.estado for e in perfil.listar(conn)] == ["pendiente"]


# --- Migración, respaldo y Git -------------------------------------------------------------------------------------

def test_migrar_dos_veces_no_falla(tmp_path):
    apply_migrations(tmp_path / "x.db")
    apply_migrations(tmp_path / "x.db")


def test_el_respaldo_incluye_los_documentos_del_perfil(entorno, tmp_path):
    db, base = entorno
    with closing(connect(db)) as conn:
        item = perfil.crear(conn, "poliza", "Póliza", ANA, AHORA)
        _version(conn, base, item, PNG, "poliza.png", valor="Póliza sintética")
    r = respaldo.respaldar(db, tmp_path / "respaldo", datetime(2026, 11, 2, 10, 0), perfil=base)
    with zipfile.ZipFile(tmp_path / "respaldo" / "sicop_20261102-100000_perfil.zip") as zf:
        assert any(n.endswith(".png") for n in zf.namelist())
    assert r.datos["perfil"]


def test_los_documentos_del_perfil_no_van_a_git():
    raiz = Path(__file__).resolve().parents[1]
    r = subprocess.run(["git", "check-ignore", "-q", "data/perfil/1/documento.pdf"], cwd=raiz)
    assert r.returncode == 0
