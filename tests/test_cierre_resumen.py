"""A4: aviso de cierre próximo, decisiones finales y resumen ejecutivo semanal.

Datos SINTÉTICOS (los carteles de tests/test_panel.py) en una base temporal; envío con un proveedor SIMULADO.
"""

import sqlite3
from contextlib import closing
from datetime import timedelta

import pytest

from app import avisos, ciclo, panel, resumen, usuarios
from app.database import connect
from tests.test_avisos import _ProveedorEspia, _outbox, _settings, base  # noqa: F401
from tests.test_panel import AHORA, CR, _cierre, db  # noqa: F401


def _revisar(conn, nro, decision, cuando=AHORA, motivo=None):
    conn.execute("INSERT INTO reviews (nro_sicop, responsable, decision, motivo, created_at) VALUES (?, 'Ivania', ?, ?, ?)",
                 (nro, decision, motivo, cuando.astimezone(CR).isoformat(timespec="seconds")))
    conn.commit()


def _notify(db, tmp_path, ahora=AHORA, solo_cierre=False, **extra):
    with closing(connect(db)) as conn:
        return avisos.notify(conn, _settings(db, tmp_path, **extra), ahora.astimezone(CR), dry_run=True,
                             solo_cierre=solo_cierre)


def _cierres(db):
    return [(para, nro) for para, nro, _, motivo, _ in _outbox(db) if motivo == "cierre_proximo"]


# --- Decisiones finales --------------------------------------------------------------------------------------

def test_decisiones_finales_se_guardan_y_las_revisiones_siguen_inmutables(db):
    with closing(connect(db)) as conn:
        user_id = usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", "una contraseña sintética larga")
        panel.guardar_revision(conn, "00000000001", "ofertada", "", "", user_id, AHORA)
        panel.guardar_revision(conn, "00000000002", "no_se_oferta", "", "", user_id, AHORA)
        assert [d for (d,) in conn.execute("SELECT decision FROM reviews ORDER BY id")] == ["ofertada", "no_se_oferta"]
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE reviews SET decision = 'interesa'")
        with pytest.raises(panel.RevisionInvalida, match="Ofertada"):
            panel.guardar_revision(conn, "00000000001", "inventada", "", "", user_id, AHORA)


# --- Aviso de cierre próximo ---------------------------------------------------------------------------------

def test_avisa_lo_marcado_que_cierra_pronto_aunque_no_sea_alta_ni_media(base, tmp_path):
    with closing(connect(base)) as conn:
        _revisar(conn, "00000000001", "revisar_requisitos")                 # Alta, cierra en 3 días
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = ? WHERE nro_sicop = '00000000005'", (_cierre(2),))
        _revisar(conn, "00000000005", "interesa")                           # sin familia, cierra en 2 días
        _revisar(conn, "00000000002", "interesa")                           # Media, cierra en 30 días: no

    r = _notify(base, tmp_path)

    assert r.por_cerrar == 4  # 2 carteles × 2 destinatarios
    assert sorted(_cierres(base)) == sorted((p, n) for p in ("oscar@ejemplo.test", "anabelle@ejemplo.test")
                                            for n in ("00000000001", "00000000005"))
    sin_familia = next(o for o in r.preparados["oscar@ejemplo.test"] if o.nro_sicop == "00000000005")
    assert (sin_familia.motivo, sin_familia.encaje, sin_familia.familias) == ("cierre_proximo", "sin_coincidencia", [])
    # El correo lo dice en el asunto y en el texto.
    asunto, html, texto = avisos.componer(r.preparados["oscar@ejemplo.test"], AHORA, "https://x.test")
    assert "por cerrar sin decisión" in asunto and "Cierra pronto y sigue sin decisión final" in texto


def test_n_dias_es_configurable_y_una_decision_final_apaga_el_aviso(base, tmp_path):
    with closing(connect(base)) as conn:
        _revisar(conn, "00000000002", "interesa")          # Media, cierra en 30 días
        _revisar(conn, "00000000001", "interesa")
        _revisar(conn, "00000000001", "ofertada")          # decisión final: ya no se avisa
    assert _notify(base, tmp_path).por_cerrar == 0
    assert _notify(base, tmp_path, NOTIFY_CLOSING_DAYS="31").por_cerrar == 2
    with pytest.raises(ValueError, match="NOTIFY_CLOSING_DAYS"):
        _notify(base, tmp_path, NOTIFY_CLOSING_DAYS="0")


def test_cierre_proximo_no_se_repite_ni_cambia_los_avisos_de_version(base, tmp_path):
    with closing(connect(base)) as conn:
        _revisar(conn, "00000000001", "interesa")
    primero = _notify(base, tmp_path)
    segundo = _notify(base, tmp_path, ahora=AHORA + timedelta(hours=2))
    assert (primero.por_cerrar, segundo.por_cerrar, segundo.nuevos) == (2, 0, 0)
    assert segundo.ya_avisados == 6  # los de versión siguen reconociendo la versión avisada
    claves = [k for (k,) in sqlite3.connect(base).execute(
        "SELECT dedup_key FROM notification_outbox WHERE motivo = 'cierre_proximo'")]
    assert all(k.endswith("|h|cierre_proximo") for k in claves)  # el motivo va en la clave


def test_cartel_vencido_o_sin_fecha_no_recibe_cierre_proximo(base, tmp_path):
    with closing(connect(base)) as conn:
        _revisar(conn, "00000000003", "interesa")   # vencido
        _revisar(conn, "00000000004", "interesa")   # sin fecha de cierre: por verificar
    assert _notify(base, tmp_path, NOTIFY_CLOSING_DAYS="60").por_cerrar == 0


def test_solo_cierre_no_prepara_los_avisos_del_dia(base, tmp_path):
    with closing(connect(base)) as conn:
        _revisar(conn, "00000000001", "interesa")
    r = _notify(base, tmp_path, solo_cierre=True)
    assert {m for *_, m, _ in _outbox(base)} == {"cierre_proximo"}
    assert {o.motivo for lista in r.preparados.values() for o in lista} == {"cierre_proximo"}


# --- Resumen semanal ------------------------------------------------------------------------------------------

def _lunes():
    """El lunes 08:00 (hora CR) más reciente que no sea posterior a AHORA."""
    local = AHORA.astimezone(CR)
    lunes = (local - timedelta(days=local.weekday())).replace(hour=8, minute=0, second=0, microsecond=0)
    return lunes if lunes <= local else lunes - timedelta(days=7)


@pytest.fixture
def semana(base):
    """Fechas fijadas respecto del lunes: así el resultado no depende del día en que corre la prueba."""
    lunes = _lunes()
    iso = lambda d: d.isoformat(timespec="seconds")  # noqa: E731
    with closing(connect(base)) as conn:
        for nro, visto, cierre in [("00000000001", lunes - timedelta(days=3), lunes + timedelta(days=2)),
                                   ("00000000002", lunes - timedelta(days=10), lunes + timedelta(days=30)),
                                   ("00000000004", lunes - timedelta(days=1), None),
                                   ("00000000005", lunes - timedelta(days=20), lunes + timedelta(days=5))]:
            conn.execute("UPDATE tenders SET first_seen = ?, fecha_cierre_recepcion = ? WHERE nro_sicop = ?",
                         (iso(visto), iso(cierre) if cierre else None, nro))
        conn.commit()
        _revisar(conn, "00000000002", "interesa", lunes - timedelta(days=2))
        _revisar(conn, "00000000005", "revisar_requisitos", lunes - timedelta(days=1))
        _revisar(conn, "00000000003", "interesa", lunes - timedelta(days=12))   # de otra semana: no cuenta
    return base, lunes


def test_semana_iso_y_periodo():
    id_semana, inicio, fin = resumen.semana(_lunes())
    assert fin - inicio == timedelta(days=7) and inicio.weekday() == 0 and fin.hour == 0
    assert id_semana.startswith(str(fin.isocalendar()[0])) and "-W" in id_semana


def test_contenido_del_resumen(semana):
    db, lunes = semana
    with closing(connect(db)) as conn:
        c = resumen.contenido(conn, panel.version_vigente(conn), lunes, "https://x.test")
    familias = dict(c.nuevas_por_familia)
    assert c.nuevas_total == 2 and familias["GPS y gestión de flotas"] == 1 and familias["Cámaras corporales"] == 1
    assert (c.revisadas_total, dict(c.revisadas)) == (2, {"Interesa": 1, "Revisar requisitos": 1})
    assert c.pendientes_total == 2 and {p.nro_sicop for p in c.pendientes} == {"00000000001", "00000000004"}
    assert [(p.nro_sicop, p.estado) for p in c.proximos_cierres] == [
        ("00000000001", "Sin revisar"), ("00000000005", "Revisar requisitos")]
    assert not c.hay_adjudicaciones


def test_un_resumen_por_semana_dry_run_y_envio(semana, tmp_path):
    db, lunes = semana
    settings = _settings(db, tmp_path)
    with closing(connect(db)) as conn:
        espia = _ProveedorEspia()
        previa = resumen.notify(conn, settings, lunes, dry_run=True, proveedor=espia)
        assert previa.nuevos == 2 and espia.llamadas == [] and previa.vista_previa
        texto = next(p for p in previa.vista_previa if p.suffix == ".txt").read_text(encoding="utf-8")
        assert "NUEVAS OPORTUNIDADES" in texto and "PRÓXIMOS CIERRES" in texto and "ADJUDICACIONES" not in texto
        assert resumen.notify(conn, settings, lunes + timedelta(hours=3), dry_run=True).nuevos == 0  # no se duplica

        class Proveedor:
            def __init__(self):
                self.para = []

            def enviar(self, para, asunto, html, texto):
                self.para.append(para)
                return "id-simulado"
        proveedor = Proveedor()
        enviado = resumen.notify(conn, settings, lunes + timedelta(hours=4), dry_run=False, proveedor=proveedor)
        assert sorted(proveedor.para) == ["anabelle@ejemplo.test", "oscar@ejemplo.test"]
        assert {e.estado for e in enviado.envios.values()} == {"aceptado"}
        # Otra vez la misma semana: nada que enviar. La siguiente semana: uno nuevo.
        assert resumen.notify(conn, settings, lunes + timedelta(hours=5), dry_run=False, proveedor=proveedor).envios == {}
        assert resumen.notify(conn, settings, lunes + timedelta(days=7), dry_run=True).nuevos == 2
    filas = sqlite3.connect(db).execute(
        "SELECT nro_sicop, motivo, dedup_key FROM notification_outbox WHERE motivo = 'resumen_semanal'").fetchall()
    assert all(nro is None and clave.endswith("|resumen_semanal") for nro, _, clave in filas)


def test_resumen_de_una_semana_vieja_no_se_envia(semana, tmp_path):
    db, lunes = semana
    settings = _settings(db, tmp_path)
    with closing(connect(db)) as conn:
        resumen.notify(conn, settings, lunes, dry_run=True)                 # queda «preparado»
        r = resumen.notify(conn, settings, lunes + timedelta(days=7), dry_run=True)
        assert all(ids for ids in r.preparados.values())
        semanas = {v for (v,) in conn.execute(
            "SELECT version FROM notification_outbox WHERE id IN (%s)" % ",".join(
                str(i) for ids in r.preparados.values() for i in ids))}
    assert semanas == {resumen.semana(lunes + timedelta(days=7))[0]}


def test_el_ciclo_arma_el_resumen_solo_los_lunes(semana, tmp_path):
    db, lunes = semana
    settings = _settings(db, tmp_path)
    with closing(connect(db)) as conn:
        martes = ciclo.Ciclo(id=0, dry_run=True)
        assert ciclo._resumen_del_lunes(conn, settings, martes, lunes + timedelta(days=1), None) is None
        assert martes.resumen is None
        del_lunes = ciclo.Ciclo(id=0, dry_run=True)
        assert ciclo._resumen_del_lunes(conn, settings, del_lunes, lunes, None) is None
        assert del_lunes.resumen.nuevos == 2
