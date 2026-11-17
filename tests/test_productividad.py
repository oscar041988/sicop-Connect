"""Productividad de la revisión (Ivania, 2026-11-17). Datos SINTÉTICOS en una base temporal; nunca toca data/."""

from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import panel, productividad, usuarios
from app.database import apply_migrations, connect
from app.main import app
from app.matching.evaluar import evaluar_base
from app.matching.reglas import cargar_reglas

CR = timezone(timedelta(hours=-6))
AHORA = datetime(2026, 11, 18, 12, 0, tzinfo=CR)   # miércoles: la última semana completa es la del 9 al 15/11
CONTRASENA = "una contraseña sintética larga"


def _dia(d, hora=0):
    return datetime(2026, 11, d, hora, 0, tzinfo=CR)


CARTELES = [
    # nro, título (SINTÉTICO), primera vez, cierre
    ("00000000001", "Servicio de monitoreo GPS de vehículos institucionales", _dia(10), _dia(12, 10)),  # Alta, revisado
    ("00000000002", "Alquiler de GPS para la flotilla", _dia(10), _dia(13, 10)),                       # Media, se escapó
    ("00000000003", "Cámaras corporales para policía", _dia(11), _dia(14, 15)),                        # Alta, revisado el día del cierre
    ("00000000004", "Servicio de rastreo GPS para la flotilla municipal", _dia(12), _dia(20, 10)),     # Alta, abierto (cierra pronto)
    ("00000000005", "Compra de sillas", _dia(10), _dia(13, 10)),                                       # no es candidato
    ("00000000006", "Monitoreo de temperatura de la cámara de refrigeración del banco de sangre",
     _dia(9), _dia(10, 8)),                                                                            # Alta, revisado tarde
    ("00000000007", "Alquiler de GPS con navegación para la flotilla", datetime(2026, 11, 1, tzinfo=CR),
     _dia(25, 10)),                                                                                    # Media, de otra semana
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "sicop.db"
    apply_migrations(path)
    with closing(connect(path)) as conn:
        conn.execute("INSERT INTO institutions (cedula, nombre, first_seen, last_seen) VALUES"
                     " ('3000000001', 'Municipalidad Sintética', '2026-10-01', '2026-10-01')")
        conn.executemany(
            "INSERT INTO tenders (nro_sicop, descripcion, institution_cedula, fecha_cierre_recepcion, content_hash,"
            " first_seen, last_seen) VALUES (?, ?, '3000000001', ?, 'h', ?, ?)",
            [(nro, titulo, cierre.isoformat(), vista.isoformat(), vista.isoformat())
             for nro, titulo, vista, cierre in CARTELES])
        evaluar_base(conn, cargar_reglas(), AHORA)
        ana = usuarios.crear_usuario(conn, "ana@ejemplo.test", "Ana", CONTRASENA, rol="admin")
        luis = usuarios.crear_usuario(conn, "luis@ejemplo.test", "Luis", CONTRASENA)
        for nro, decision, motivo, quien, cuando in [
            ("00000000001", "interesa", "", ana, _dia(11)),
            ("00000000006", "no_interesa", "no_encaja", ana, _dia(10, 9)),   # una hora después del cierre
            ("00000000003", "interesa", "", luis, _dia(14, 10)),             # el día del cierre, antes de la hora
            ("00000000007", "revisar_requisitos", "", luis, _dia(12)),
            ("00000000001", "no_se_oferta", "", luis, _dia(13)),             # segunda revisión: no cuenta
        ]:
            panel.guardar_revision(conn, nro, decision, motivo, "", quien, cuando)
    return path


def _calcular(db, semana=None):
    with closing(connect(db)) as conn:
        return productividad.calcular(conn, panel.version_vigente(conn), AHORA, semana)


def test_semana_por_defecto_es_la_ultima_completa(db):
    p = _calcular(db)

    assert (p.semana.inicio, p.semana.ultimo_dia) == (_dia(9), date(2026, 11, 15))
    assert (p.anterior, p.siguiente) == (date(2026, 11, 2), date(2026, 11, 16))


def test_cada_candidato_queda_en_un_solo_grupo(db):
    s = _calcular(db).semana

    assert (s.candidatos, s.revisados, s.abiertos, s.abiertos_pronto) == (5, 2, 1, 1)
    # El 6 se revisó una hora después del cierre: se escapó igual. Ordenados por cierre.
    assert [e.nro_sicop for e in s.escapados] == ["00000000006", "00000000002"]
    assert s.escapados[1].dias_en_panel == 3


def test_por_persona_cuenta_la_primera_revision_de_la_semana(db):
    ana, luis = _calcular(db).personas

    assert (ana.nombre, ana.revisados, ana.interesa, ana.revisar, ana.no, ana.al_cierre) == ("Ana", 2, 1, 0, 1, 1)
    assert ana.dias_promedio == Decimal("1.2")            # 1 día y 1,375 días
    # Luis: el 7 es de otra semana pero lo revisó esta; su «No se oferta» del 1 no cuenta (no es la primera).
    assert (luis.nombre, luis.revisados, luis.interesa, luis.revisar, luis.no, luis.al_cierre) == ("Luis", 2, 1, 1, 0, 1)


def test_historial_y_semana_futura(db):
    p = _calcular(db, date(2026, 12, 30))                 # una semana futura se toma como la semana en curso

    assert p.semana.inicio == _dia(16) and p.siguiente is None
    assert [h.inicio.date() for h in p.historial] == [date(2026, 10, 26), date(2026, 11, 2), date(2026, 11, 9),
                                                     date(2026, 11, 16)]
    assert p.historial[2].candidatos == 5


def _cliente(db, monkeypatch, email):
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setattr("app.web.rutas._ahora", lambda: AHORA)
    cliente = TestClient(app)
    html = cliente.get("/login").text
    token = html.split('name="csrf_token" value="')[1].split('"')[0]
    assert cliente.post("/login", data={"csrf_token": token, "email": email, "contrasena": CONTRASENA},
                        follow_redirects=False).status_code == 303
    return cliente


def test_pagina_por_persona_solo_para_administradores(db, monkeypatch):
    admin = _cliente(db, monkeypatch, "ana@ejemplo.test").get("/productividad").text
    assert "Por persona" in admin and "Solo administradores" in admin
    assert 'href="/oportunidades/00000000002"' in admin and "Cerraron sin revisión" in admin

    encargado = _cliente(db, monkeypatch, "luis@ejemplo.test").get("/productividad").text
    assert "Por persona" not in encargado and "Cerraron sin revisión" in encargado


def test_semana_ilegible_muestra_la_de_por_defecto(db, monkeypatch):
    html = _cliente(db, monkeypatch, "ana@ejemplo.test").get("/productividad?semana=no-es-fecha").text

    assert "Semana del lunes 9 de noviembre al domingo 15 de noviembre" in " ".join(html.split())
