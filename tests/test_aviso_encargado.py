"""Gestor de documentos, paso 1B: correo al nuevo encargado (app/aviso_encargado.py, docs/GESTOR_DOCUMENTOS.md).

Datos SINTÉTICOS (la base de tests/test_seguimiento.py) y envío SIMULADO: nunca sale un correo de verdad.
"""

import shutil
import sqlite3
from contextlib import closing
from datetime import timedelta

import pytest

from app import aviso_encargado, avisos, ciclo, destinatarios, reintentos, seguimiento, usuarios
from app.config import load_settings
from app.database import MIGRATIONS_DIR, apply_migrations, connect
from tests.test_avisos import ProveedorSimulado
from tests.test_seguimiento import AHORA, CR, NRO, OTRO, _id, _quien, db  # noqa: F401 (db es una fixture)


def _settings(db, tmp_path):  # noqa: F811
    return load_settings(env_file=None, environ={
        "DATABASE_PATH": str(db), "EXPORTS_DIR": str(tmp_path / "exports"), "INCOMING_DIR": str(tmp_path / "incoming"),
        "RAW_DATA_DIR": str(tmp_path / "raw"), "APP_BASE_URL": "https://sicop.ejemplo.test"})


def _asignar(db, email, nro=NRO, por="oscar@ejemplo.test", ahora=AHORA):  # noqa: F811
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, nro, _quien(db, por), ahora)
        return seguimiento.asignar(conn, nro, _id(db, email), _quien(db, por), ahora)


def _outbox(db):  # noqa: F811
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT recipient, nro_sicop, version, motivo, status FROM notification_outbox"
                            " ORDER BY id").fetchall()


def _notify(db, tmp_path, dry_run=True, proveedor=None, ahora=AHORA):  # noqa: F811
    with closing(connect(db)) as conn:
        return aviso_encargado.notify(conn, _settings(db, tmp_path), ahora.astimezone(CR), dry_run=dry_run,
                                      proveedor=proveedor)


class _Espia:
    def enviar(self, *args):
        raise AssertionError("el dry-run no debe llamar al proveedor")


def test_asignar_prepara_el_correo_al_nuevo_encargado(db):  # noqa: F811
    assert _asignar(db, "ivania@ejemplo.test")
    [(para, nro, version, motivo, estado)] = _outbox(db)
    assert (para, nro, motivo, estado) == ("ivania@ejemplo.test", NRO, "asignacion", "preparado")
    with closing(sqlite3.connect(db)) as conn:
        assert version == str(conn.execute("SELECT max(id) FROM seguimiento_asignaciones").fetchone()[0])


def test_quien_se_asigna_a_si_mismo_no_recibe_correo(db):  # noqa: F811
    assert _asignar(db, "oscar@ejemplo.test", por="oscar@ejemplo.test")
    assert _outbox(db) == []


def test_el_dry_run_escribe_la_vista_previa_y_no_se_repite(db, tmp_path):  # noqa: F811
    _asignar(db, "ivania@ejemplo.test")

    r = _notify(db, tmp_path, proveedor=_Espia())
    [(para, [a])] = r.preparados.items()
    assert para == "ivania@ejemplo.test" and a.nro_sicop == NRO and a.antes is None
    texto = next(p for p in r.vista_previa if p.suffix == ".txt").read_text(encoding="utf-8")
    assert f"Asunto: SICOP · Te asignaron el cartel {NRO} en seguimiento" in texto
    assert "Asignado por Oscar" in texto and "estaba sin encargado" in texto
    assert f"https://sicop.ejemplo.test/seguimiento/{NRO}" in texto and "VISTA PREVIA" in texto
    html = next(p for p in r.vista_previa if p.suffix == ".html").read_text(encoding="utf-8")
    assert "Municipalidad Sintética A" in html and "<script" not in html

    _notify(db, tmp_path)   # el ciclo de mañana, otra vez en dry-run
    assert [f[4] for f in _outbox(db)] == ["preparado"]   # sigue una sola fila, sin enviar


def test_si_cambia_de_encargado_antes_del_envio_solo_le_llega_al_nuevo(db, tmp_path):  # noqa: F811
    _asignar(db, "ivania@ejemplo.test")
    _asignar(db, "ana@ejemplo.test")

    r = _notify(db, tmp_path)
    assert list(r.preparados) == ["ana@ejemplo.test"]
    assert r.preparados["ana@ejemplo.test"][0].antes == "Ivania"
    assert [f[0] for f in _outbox(db)] == ["ivania@ejemplo.test", "ana@ejemplo.test"]   # nada se borra


def test_varios_carteles_van_en_un_solo_correo(db, tmp_path):  # noqa: F811
    _asignar(db, "ivania@ejemplo.test", NRO)
    _asignar(db, "ivania@ejemplo.test", OTRO)
    proveedor = ProveedorSimulado()

    r = _notify(db, tmp_path, dry_run=False, proveedor=proveedor)

    [(para, asunto, html, texto)] = proveedor.llamadas
    assert para == "ivania@ejemplo.test" and asunto == "SICOP · Te asignaron 2 carteles en seguimiento"
    assert NRO in texto and OTRO in texto
    assert r.envios["ivania@ejemplo.test"].estado == "aceptado"
    assert {f[4] for f in _outbox(db)} == {"aceptado"}
    _notify(db, tmp_path, dry_run=False, proveedor=proveedor)
    assert len(proveedor.llamadas) == 1   # no se reenvía


def test_un_usuario_desactivado_no_recibe_el_correo(db, tmp_path):  # noqa: F811
    _asignar(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        usuarios.cambiar_estado(conn, _id(db, "ivania@ejemplo.test"), False)
    assert _notify(db, tmp_path).preparados == {}


def test_un_cartel_ya_cerrado_igual_avisa_al_encargado(db, tmp_path):  # noqa: F811
    _asignar(db, "ivania@ejemplo.test")
    assert list(_notify(db, tmp_path, ahora=AHORA + timedelta(days=30)).preparados) == ["ivania@ejemplo.test"]


def test_el_correo_diario_no_incluye_las_asignaciones(db, tmp_path):  # noqa: F811
    with closing(connect(db)) as conn:
        destinatarios.agregar(conn, "ivania@ejemplo.test", "Ivania")   # también recibe los avisos del día
    _asignar(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        r = avisos.notify(conn, _settings(db, tmp_path), AHORA, dry_run=True)
    assert all(o.motivo != "asignacion" for lista in r.preparados.values() for o in lista)
    assert sum(f[3] == "asignacion" for f in _outbox(db)) == 1


def test_un_correo_rechazado_se_reintenta_desde_avisos_mientras_siga_vigente(db, tmp_path):  # noqa: F811
    _asignar(db, "ivania@ejemplo.test")
    _notify(db, tmp_path, dry_run=False, proveedor=ProveedorSimulado(ivania="rechazar"))

    with closing(connect(db)) as conn:
        [a] = reintentos.por_revisar(conn, AHORA)
        assert a.es_asignacion and a.estado == "fallido" and a.destinatario_activo   # sin estar en «Destinatarios»
        assert a.que == f"asignación del cartel {NRO}"
        reintentos.reintentar(conn, a.id, AHORA)
    assert _outbox(db)[0][4] == "preparado"

    _notify(db, tmp_path, dry_run=False, proveedor=ProveedorSimulado(ivania="rechazar"))
    _asignar(db, "ana@ejemplo.test")   # el cartel cambió de encargado: ya no hace falta
    with closing(connect(db)) as conn:
        a = next(x for x in reintentos.por_revisar(conn, AHORA) if x.para == "ivania@ejemplo.test")
        assert not a.destinatario_activo
        with pytest.raises(reintentos.AvisoInvalido, match="ya no es el encargado"):
            reintentos.reintentar(conn, a.id, AHORA)


def test_el_ciclo_lo_envia_aunque_la_fuente_falle(db, tmp_path, monkeypatch, capsys):  # noqa: F811
    monkeypatch.setattr(ciclo, "_resumen_del_lunes", lambda *args: None)
    settings = _settings(db, tmp_path)
    settings.incoming_dir.mkdir(parents=True)
    _asignar(db, "ivania@ejemplo.test")

    from app.cli import main
    assert main(["run-cycle", "--origen", "sintetico"], settings) == 1   # no llegó ningún archivo

    salida = capsys.readouterr().out
    assert "NO se avisó" in salida
    assert "Correo a encargados (seguimiento): 1 encargado(s) · 1 cartel(es) asignado(s)" in salida
    assert f"ivania@ejemplo.test: {NRO}" in salida and "Vista previa:" in salida
    assert _outbox(db)[0][4] == "preparado"   # dry-run: no se envió


def test_0024_conserva_la_outbox_de_antes(tmp_path):
    hasta_0023 = tmp_path / "hasta_0023"
    hasta_0023.mkdir()
    for archivo in sorted(MIGRATIONS_DIR.glob("00*.sql")):
        if archivo.name < "0024":
            shutil.copy(archivo, hasta_0023)
    db = tmp_path / "sicop.db"
    apply_migrations(db, hasta_0023)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("INSERT INTO notification_outbox (id, dedup_key, recipient, nro_sicop, version, motivo, cierre,"
                     " rules_version, status, created_at) VALUES (7, 'k', 'a@ejemplo.test', NULL, '2026-W44',"
                     " 'resumen_semanal', NULL, 'r', 'aceptado', '2026-10-26T08:00:00-06:00')")
        conn.commit()

    assert apply_migrations(db) == ["0024_aviso_encargado.sql"]
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT id, motivo, status FROM notification_outbox").fetchall() == [
            (7, "resumen_semanal", "aceptado")]
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM notification_outbox")
