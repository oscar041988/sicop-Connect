"""Enriquecimiento automático (lección 4, entrega 4A: enrich run; cambios de §9: prioridad, reintento y borrado al
cierre) con SICOP SIMULADO.

La cola, la retención y los textos se prueban sin navegador sobre una base temporal. Las corridas usan la página
SIMULADA de test_ficha.py (Chromium sin ventana, red cortada). Todas las carpetas van en tmp_path."""

import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta

import pytest

from app import cli
from app.bloqueo import CicloOcupado, bloqueo
from app.importers.comun import HORA_CR
from app.sources import enriquecimiento as en
from tests.test_documentos import _archivos
from tests.test_ficha import ESPERA_MS, GPS, HORA, SANTA_ANA, ABARROTES, _chromium_instalado, _Pausas, _settings, \
    _Sicop

navegador = pytest.mark.skipif(not _chromium_instalado(),
                               reason="Chromium de Playwright no instalado: python -m playwright install chromium")
BAJA, CERRADO = "20260000001", "20260000002"


def _base(tmp_path, encajes=None, **extra):
    """Base temporal con la evaluación vigente «v1» y sus encajes."""
    encajes = encajes or {GPS: "alta", ABARROTES: "media", SANTA_ANA: "alta", BAJA: "baja", CERRADO: "alta"}
    valores = {"ENRICH_ENABLED": "true", "OBTAIN_ALERT_TO": "alertas@ejemplo.test", **extra}
    settings = _settings(tmp_path, nros=tuple(encajes), **valores)
    with closing(sqlite3.connect(settings.database_path)) as conn, conn:
        conn.execute("INSERT INTO evaluation_runs (rules_version, evaluated_at, carteles) VALUES ('v1', ?, 5)",
                     (HORA.isoformat(),))
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = '2026-11-20T10:00:00-06:00' WHERE nro_sicop = ?",
                     (BAJA,))
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = '2026-10-01T10:00:00-06:00' WHERE nro_sicop = ?",
                     (CERRADO,))
        for nro, encaje in encajes.items():
            conn.execute("INSERT INTO opportunity_assessments (nro_sicop, familia, encaje, evidencia, rules_version,"
                         " evaluated_at) VALUES (?, 'camaras', ?, 'x', 'v1', ?)", (nro, encaje, HORA.isoformat()))
    return settings


def _sql(settings, sql, params=()):
    with closing(sqlite3.connect(settings.database_path)) as conn, conn:
        return conn.execute(sql, params).fetchall()


def _ficha(settings, nro, consultado, cierre):
    _sql(settings, "INSERT INTO tender_details (nro_sicop, consultado_en, content_hash, copia_fiel, campos_quitados,"
                   " cierre_recepcion) VALUES (?, ?, ?, '{}', '[]', ?)", (nro, consultado, f"h-{nro}-{consultado}", cierre))


def _cola(settings, ahora=HORA):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        return [(e.nro_sicop, e.motivo) for e in en.cola(conn, settings, ahora)]


# --- Cola ---------------------------------------------------------------------------------------------------

def test_cola_alta_media_y_baja_abiertas_por_prioridad(tmp_path):
    settings = _base(tmp_path)
    # Santa Ana: en los datos abiertos cerró el 23/10 y nunca se consultó su ficha → no entra. Baja entra al final.
    assert _cola(settings) == [(GPS, "nunca enriquecido"), (ABARROTES, "nunca enriquecido"),
                               (BAJA, "nunca enriquecido")]


def test_la_prioridad_va_antes_que_el_cierre_y_cuenta_el_mejor_encaje(tmp_path):
    # ABARROTES (cierra el 09/11) es alta en otra familia: va antes que GPS media (cierra el 28/10).
    settings = _base(tmp_path, encajes={GPS: "media", ABARROTES: "baja", BAJA: "baja"})
    _sql(settings, "INSERT INTO opportunity_assessments (nro_sicop, familia, encaje, evidencia, rules_version,"
                   " evaluated_at) VALUES (?, 'gps', 'alta', 'x', 'v1', ?)", (ABARROTES, HORA.isoformat()))
    with closing(sqlite3.connect(settings.database_path)) as conn:
        lista = en.cola(conn, settings, HORA)
    assert [(e.nro_sicop, e.encaje) for e in lista] == [(ABARROTES, "alta"), (GPS, "media"), (BAJA, "baja")]


def test_sin_coincidencia_no_entra(tmp_path):
    settings = _base(tmp_path, encajes={GPS: "sin_coincidencia", ABARROTES: "alta"})
    assert _cola(settings) == [(ABARROTES, "nunca enriquecido")]


def test_la_ficha_manda_sobre_los_datos_abiertos_y_entra_si_cierra_pronto(tmp_path):
    settings = _base(tmp_path)
    _ficha(settings, SANTA_ANA, "2026-10-27T09:38:00-06:00", "2026-10-30T23:59:00-06:00")
    # El 27/10 faltan más de 3 días; el 28/10 ya no (y la ficha dice que sigue abierto).
    assert SANTA_ANA not in dict(_cola(settings))
    assert dict(_cola(settings, datetime(2026, 10, 28, 10, 0, tzinfo=HORA_CR)))[SANTA_ANA] == \
        "cierra en 3 días o menos"


def test_entra_otra_vez_si_los_datos_abiertos_son_mas_nuevos(tmp_path):
    settings = _base(tmp_path)
    _ficha(settings, ABARROTES, "2026-10-20T10:00:00-06:00", "2026-11-09T08:30:00-06:00")
    assert dict(_cola(settings))[ABARROTES] == "los datos abiertos lo vieron después de la última ficha"
    _ficha(settings, ABARROTES, "2026-10-27T08:30:00-06:00", "2026-11-09T08:30:00-06:00")
    assert ABARROTES not in dict(_cola(settings))  # ya está al día y no cierra pronto


def test_lo_consultado_hoy_no_vuelve_y_cuenta_para_el_maximo(tmp_path):
    settings = _base(tmp_path, ENRICH_MAX_PER_DAY="2")
    _sql(settings, "INSERT INTO enrich_consultas (nro_sicop, iniciada_en, resultado) VALUES (?, ?, 'fallo')",
         (GPS, "2026-10-27T08:00:00-06:00"))
    assert _cola(settings) == [(ABARROTES, "nunca enriquecido"), (BAJA, "nunca enriquecido")]
    with closing(sqlite3.connect(settings.database_path)) as conn:
        assert en.cupo_de_hoy(conn, settings, HORA) == 1
        assert en.cupo_de_hoy(conn, settings, HORA, maximo=5) == 1


def test_sin_evaluacion_no_hay_cola(tmp_path):
    settings = _settings(tmp_path)
    assert _cola(settings) == []


# --- Retención y textos ----------------------------------------------------------------------------------------

def test_retencion_borra_lo_viejo_y_conserva_los_fallos(tmp_path):
    settings = _base(tmp_path)
    raiz = settings.recordings_dir
    for ruta in ("2026-09-01/AAA/100000-video.webm", "2026-09-01/BBB/100000-video.webm",
                 "2026-10-20/CCC/100000-video.webm", "otra-cosa/no-tocar.txt"):
        (raiz / ruta).parent.mkdir(parents=True, exist_ok=True)
        (raiz / ruta).write_text("SIMULADO")
    _sql(settings, "INSERT INTO enrich_consultas (nro_sicop, iniciada_en, resultado, grabacion) VALUES (?, ?, 'fallo',"
                   " '2026-09-01/BBB/100000')", (GPS, "2026-09-01T10:00:00-06:00"))

    with closing(sqlite3.connect(settings.database_path)) as conn:
        borradas = en.limpiar_grabaciones(conn, settings, date(2026, 10, 27))

    assert borradas == 1
    assert not (raiz / "2026-09-01" / "AAA").exists()
    assert (raiz / "2026-09-01" / "BBB").exists() and (raiz / "2026-10-20" / "CCC").exists()
    assert (raiz / "otra-cosa" / "no-tocar.txt").exists()


def test_el_resumen_avisa_los_dias_habiles_sin_corrida(tmp_path):
    settings = _base(tmp_path)
    _sql(settings, "INSERT INTO enrich_runs (iniciada_en, maximo) VALUES ('2026-10-22T10:00:00-06:00', 20)")
    _sql(settings, "INSERT INTO enrich_runs (iniciada_en, maximo) VALUES (?, 20)", (HORA.isoformat(),))
    with closing(sqlite3.connect(settings.database_path)) as conn:
        faltaron = en.dias_habiles_sin_corrida(conn, HORA.date(), 2)
    assert faltaron == [date(2026, 10, 23), date(2026, 10, 26)]  # viernes y lunes; el fin de semana no cuenta
    asunto, cuerpo = en.texto_resumen(settings, en.Corrida("sin_cola"), HORA, faltaron)
    assert "sin consultas" in asunto and "(23/10, 26/10)" in cuerpo and "La cola esperó" in cuerpo


def test_migrate_dos_veces_y_la_bitacora_no_se_cambia(tmp_path):
    settings = _base(tmp_path)
    from app.database import apply_migrations
    assert apply_migrations(settings.database_path) == []
    _sql(settings, "INSERT INTO enrich_consultas (nro_sicop, iniciada_en, resultado) VALUES (?, ?, 'control')",
         (GPS, HORA.isoformat()))
    _sql(settings, "UPDATE enrich_consultas SET aviso_estado = 'vista_previa'")  # solo el aviso se anota
    for sql in ("UPDATE enrich_consultas SET resultado = 'nueva'", "DELETE FROM enrich_consultas",
                "DELETE FROM enrich_runs"):
        _sql(settings, "INSERT INTO enrich_runs (iniciada_en, maximo) VALUES (?, 20)", (HORA.isoformat(),))
        with pytest.raises(sqlite3.IntegrityError):
            _sql(settings, sql)


# --- La corrida (navegador SIMULADO) -------------------------------------------------------------------------

def _correr(settings, sicop, dormir=None, **extra):
    return en.correr(settings, reloj=lambda: HORA, dormir=dormir or _Pausas(), preparar_contexto=sicop,
                     espera_ms=ESPERA_MS, espera_documento_ms=ESPERA_MS, **extra)


def _dos_abiertos(tmp_path, **extra):
    """GPS y Santa Ana en la cola (a Santa Ana se le pone el cierre abierto en los datos abiertos)."""
    settings = _base(tmp_path, encajes={GPS: "alta", SANTA_ANA: "alta"}, **extra)
    _sql(settings, "UPDATE tenders SET fecha_cierre_recepcion = '2026-10-30T23:59:00-06:00' WHERE nro_sicop = ?",
         (SANTA_ANA,))
    archivos = {**_archivos(GPS), **_archivos(SANTA_ANA)}
    return settings, archivos


def test_desactivado_no_abre_el_navegador(tmp_path):
    settings = _base(tmp_path, ENRICH_ENABLED="false")
    sicop = _Sicop()
    assert _correr(settings, sicop).estado == "desactivado"
    assert sicop.peticiones == [] and _sql(settings, "SELECT * FROM enrich_runs") == []


@navegador
def test_corrida_completa_con_bitacora_y_resumen(tmp_path):
    settings, archivos = _dos_abiertos(tmp_path)

    corrida = _correr(settings, _Sicop(archivos=archivos))

    assert corrida.estado == "ok" and [c.nro_sicop for c in corrida.consultas] == [GPS, SANTA_ANA]
    filas = _sql(settings, "SELECT nro_sicop, run_id, resultado, documentos_guardados, grabacion FROM enrich_consultas")
    assert filas == [(GPS, corrida.run_id, "nueva", 5, f"2026-10-27/{GPS}/090000"),
                     (SANTA_ANA, corrida.run_id, "nueva", 7, f"2026-10-27/{SANTA_ANA}/090000")]
    assert (settings.recordings_dir / "2026-10-27" / GPS / "090000-video.webm").exists()
    assert _sql(settings, "SELECT estado, en_cola, consultados, fallos, resumen_estado FROM enrich_runs") == \
        [("ok", 2, 2, 0, "vista_previa")]
    resumen = (settings.exports_dir / f"resumen-enriquecimiento-{corrida.run_id}.txt").read_text(encoding="utf-8")
    assert "Para: alertas@ejemplo.test" in resumen and "2 consultados, 0 FALLO" in resumen
    assert "cierre 30/10/2026 23:59" in resumen
    # Ya consultados hoy: una segunda corrida no tiene cola.
    assert _correr(settings, _Sicop(archivos=archivos)).estado == "sin_cola"


@navegador
def test_un_fallo_no_detiene_la_cola(tmp_path):
    settings, archivos = _dos_abiertos(tmp_path)
    sicop = _Sicop(cambios={GPS: {"busqueda": '{"content": []}'}}, archivos=archivos)

    corrida = _correr(settings, sicop)

    assert corrida.estado == "con_fallos" and [c.resultado for c in corrida.consultas] == ["fallo", "nueva"]
    resumen = (settings.exports_dir / f"resumen-enriquecimiento-{corrida.run_id}.txt").read_text(encoding="utf-8")
    assert "2 consultados, 1 FALLO" in resumen and "no encontró el cartel" in resumen
    assert "Video y capturas:" in resumen and GPS in resumen


@navegador
def test_captcha_detiene_todo_y_manda_la_alerta(tmp_path):
    settings, archivos = _dos_abiertos(tmp_path)
    pausas = _Pausas()

    corrida = _correr(settings, _Sicop("captcha", archivos=archivos), dormir=pausas)

    assert pausas.segundos == [15 * 60]  # la espera antes del único reintento, con el navegador cerrado

    assert corrida.estado == "detenida" and [c.nro_sicop for c in corrida.consultas] == [GPS]
    alerta = (settings.exports_dir / f"alerta-enriquecimiento-{corrida.run_id}.txt").read_text(encoding="utf-8")
    assert "DETENIDO" in alerta and "Ya se reintentó UNA vez, después de 15 min" in alerta
    assert "nunca se resuelve" in alerta
    assert _sql(settings, "SELECT resultado, aviso_estado, es_reintento FROM enrich_consultas") == \
        [("control", None, 0), ("control", "vista_previa", 1)]
    assert _sql(settings, "SELECT estado FROM enrich_runs") == [("detenida",)]


@navegador
def test_max_para_probar_con_pocos(tmp_path):
    settings, archivos = _dos_abiertos(tmp_path)
    corrida = _correr(settings, _Sicop(archivos=archivos), maximo=1)
    assert [c.nro_sicop for c in corrida.consultas] == [GPS] and corrida.en_cola == 2


def test_otro_run_en_curso_sale_con_codigo_2(tmp_path, capsys):
    settings = _base(tmp_path)
    with bloqueo(settings.database_path.parent / "enrich-run.lock", "prueba SIMULADA"):
        with pytest.raises(CicloOcupado):
            _correr(settings, _Sicop())
        assert cli.main(["enrich", "run"], settings=settings) == 2
    assert "ya hay otro enrich run en curso" in capsys.readouterr().err


def test_enrich_cola_y_status_en_la_terminal(tmp_path, capsys, monkeypatch):
    settings = _base(tmp_path, ENRICH_MAX_PER_DAY="1")
    monkeypatch.setattr(en, "_ahora", lambda: HORA)
    assert cli.main(["enrich", "cola"], settings=settings) == 0
    salida = capsys.readouterr().out
    assert "Cola de hoy" in salida and f"hoy Alta  {GPS}" in salida  # solo el primero cabe en el cupo
    assert f"     Baja  {BAJA}" in salida
    assert "Al correr se borrarán" not in salida  # no hay fichas guardadas de carteles ya cerrados
    assert cli.main(["enrich", "status"], settings=settings) == 0
    assert "Todavía no hay consultas" in capsys.readouterr().out


class _CambiaVariante(_Pausas):
    """Pausa SIMULADA que cambia lo que muestra SICOP: {segundos de la pausa: variante para el próximo navegador}."""

    def __init__(self, sicop, cambios):
        super().__init__()
        self.sicop, self.cambios = sicop, dict(cambios)

    def __call__(self, s):
        super().__call__(s)
        if s in self.cambios:
            self.sicop.variante = self.cambios.pop(s)


@navegador
def test_el_reintento_sale_bien_y_sigue_la_cola(tmp_path):
    settings, archivos = _dos_abiertos(tmp_path)
    sicop = _Sicop("captcha", archivos=archivos)

    corrida = _correr(settings, sicop, dormir=_CambiaVariante(sicop, {900: "normal"}))

    assert corrida.estado == "ok" and [c.resultado for c in corrida.consultas] == ["nueva", "nueva"]
    assert corrida.reintentada is not None and corrida.reintentada.nro_sicop == GPS
    assert _sql(settings, "SELECT nro_sicop, resultado, es_reintento FROM enrich_consultas") == \
        [(GPS, "control", 0), (GPS, "nueva", 1), (SANTA_ANA, "nueva", 0)]
    resumen = (settings.exports_dir / f"resumen-enriquecimiento-{corrida.run_id}.txt").read_text(encoding="utf-8")
    assert "2 consultados, 0 FALLO" in resumen and "se reintentó una vez: ficha nueva" in resumen
    assert not (settings.exports_dir / f"alerta-enriquecimiento-{corrida.run_id}.txt").exists()


@navegador
def test_un_segundo_captcha_en_la_corrida_no_se_reintenta(tmp_path):
    settings, archivos = _dos_abiertos(tmp_path)
    sicop = _Sicop("captcha", archivos=archivos)
    # Tras la espera, GPS sale bien; en la primera pausa de 8 s el CAPTCHA vuelve (para el siguiente navegador).
    pausas = _CambiaVariante(sicop, {900: "normal", 8: "captcha"})

    corrida = _correr(settings, sicop, dormir=pausas)

    assert corrida.estado == "detenida" and [c.resultado for c in corrida.consultas] == ["nueva", "control"]
    assert pausas.segundos.count(900) == 1
    alerta = (settings.exports_dir / f"alerta-enriquecimiento-{corrida.run_id}.txt").read_text(encoding="utf-8")
    assert f"El único reintento de la corrida ya se usó con {GPS}" in alerta


# --- Borrado al cierre (migración 0021) ---------------------------------------------------------------------

def _documento(settings, nro, detalle_id, nombre="pliego.pdf", paginas=2):
    """Un documento guardado SIMULADO, con su texto y su archivo en DOCUMENTS_DIR/<nro>/."""
    carpeta = settings.documents_dir / nro
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_bytes(b"%PDF SIMULADO")
    with closing(sqlite3.connect(settings.database_path)) as conn, conn:
        doc = conn.execute(
            "INSERT INTO tender_documents (nro_sicop, detalle_id, server_file, tamano_bytes, sha256, ruta_local,"
            " registrado_en, estado, texto_estado, paginas) VALUES (?, ?, ?, 1000, 'sha', ?, ?, 'guardado',"
            " 'extraido', ?)", (nro, detalle_id, nombre, f"{nro}/{nombre}", HORA.isoformat(), paginas)).lastrowid
        for pagina in range(1, paginas + 1):
            conn.execute("INSERT INTO tender_document_text (documento_id, pagina, texto) VALUES (?, ?, 'SIMULADO')",
                         (doc, pagina))


def _con_ficha_y_documento(settings, nro, cierre):
    _ficha(settings, nro, "2026-09-20T10:00:00-06:00", cierre)
    detalle = _sql(settings, "SELECT max(id) FROM tender_details WHERE nro_sicop = ?", (nro,))[0][0]
    _documento(settings, nro, detalle)
    _sql(settings, "INSERT INTO enrich_consultas (nro_sicop, iniciada_en, resultado, detalle_id) VALUES (?, ?,"
                   " 'nueva', ?)", (nro, "2026-09-20T10:00:00-06:00", detalle))
    return detalle


def _retirar(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        return en.retirar(conn, settings, HORA, None)


def test_al_cierre_se_borran_la_ficha_los_documentos_y_su_texto(tmp_path):
    settings = _base(tmp_path)
    detalle = _con_ficha_y_documento(settings, CERRADO, "2026-10-01T10:00:00-06:00")
    _con_ficha_y_documento(settings, ABARROTES, "2026-11-09T08:30:00-06:00")  # abierto: no se toca

    retiros = _retirar(settings)

    assert [(r.nro_sicop, r.hasta_detalle_id, r.fichas, r.documentos, r.paginas, r.bytes) for r in retiros] == \
        [(CERRADO, detalle, 1, 1, 2, 1000)]
    for tabla in ("tender_details", "tender_documents"):
        assert _sql(settings, f"SELECT DISTINCT nro_sicop FROM {tabla}") == [(ABARROTES,)]
    assert _sql(settings, "SELECT count(*) FROM tender_document_text") == [(2,)]  # solo las de ABARROTES
    assert not (settings.documents_dir / CERRADO).exists() and (settings.documents_dir / ABARROTES).exists()
    # La bitácora se conserva; solo pierde el enlace a la ficha borrada.
    assert _sql(settings, "SELECT nro_sicop, resultado, detalle_id IS NULL FROM enrich_consultas ORDER BY id") == \
        [(CERRADO, "nueva", 1), (ABARROTES, "nueva", 0)]
    assert _sql(settings, "SELECT nro_sicop, cierre, documentos FROM enrich_retiros") == \
        [(CERRADO, "2026-10-01T10:00:00-06:00", 1)]
    assert _sql(settings, "SELECT count(*) FROM tenders WHERE nro_sicop = ?", (CERRADO,)) == [(1,)]
    assert _retirar(settings) == []  # una segunda vez no hay nada que borrar


def test_sin_retiro_anotado_nada_se_puede_borrar(tmp_path):
    settings = _base(tmp_path)
    _con_ficha_y_documento(settings, ABARROTES, "2026-11-09T08:30:00-06:00")
    for sql in ("DELETE FROM tender_document_text", "DELETE FROM tender_documents", "DELETE FROM tender_details",
                "UPDATE enrich_consultas SET detalle_id = NULL", "UPDATE enrich_consultas SET es_reintento = 1"):
        with pytest.raises(sqlite3.IntegrityError):
            _sql(settings, sql)
    _sql(settings, "INSERT INTO enrich_retiros (nro_sicop, retirado_en, cierre, hasta_detalle_id, fichas, documentos,"
                   " paginas, bytes) VALUES (?, ?, 'x', 1, 1, 1, 2, 1000)", (ABARROTES, HORA.isoformat()))
    for sql in ("DELETE FROM enrich_retiros", "UPDATE enrich_retiros SET bytes = 0"):
        with pytest.raises(sqlite3.IntegrityError):
            _sql(settings, sql)


def test_se_conservan_interesa_ofertada_seguimiento_y_prorrogados(tmp_path):
    interesa, ofertada, seguimiento, prorrogado, no_interesa = (f"2026000001{i}" for i in range(5))
    todos = (interesa, ofertada, seguimiento, prorrogado, no_interesa)
    settings = _base(tmp_path, encajes={n: "alta" for n in todos})
    for nro in todos:
        _sql(settings, "UPDATE tenders SET fecha_cierre_recepcion = '2026-10-01T10:00:00-06:00' WHERE nro_sicop = ?",
             (nro,))
        _con_ficha_y_documento(settings, nro, "2026-10-01T10:00:00-06:00")
    # Prorrogado: la ficha dice 01/10, pero los datos abiertos ya traen el cierre nuevo.
    _sql(settings, "UPDATE tenders SET fecha_cierre_recepcion = '2026-11-15T10:00:00-06:00' WHERE nro_sicop = ?",
         (prorrogado,))
    _sql(settings, "INSERT INTO users (email, nombre, role, password_hash, created_at) VALUES ('a@ejemplo.test',"
                   " 'Usuaria SIMULADA', 'encargado', 'x', ?)", (HORA.isoformat(),))
    for nro, decision, motivo in ((interesa, "interesa", None), (ofertada, "ofertada", None),
                                  (no_interesa, "no_interesa", "otro")):
        _sql(settings, "INSERT INTO reviews (nro_sicop, user_id, responsable, decision, motivo, created_at)"
                       " VALUES (?, 1, 'Usuaria SIMULADA', ?, ?, ?)", (nro, decision, motivo, HORA.isoformat()))
    # «Interesa» en algún momento basta, aunque la última revisión diga otra cosa.
    _sql(settings, "INSERT INTO reviews (nro_sicop, user_id, responsable, decision, created_at) VALUES (?, 1,"
                   " 'Usuaria SIMULADA', 'revisar_requisitos', ?)", (interesa, HORA.isoformat()))
    _sql(settings, "INSERT INTO seguimientos (nro_sicop, abierto_por, abierto_por_nombre, abierto_en) VALUES (?, 1,"
                   " 'Usuaria SIMULADA', ?)", (seguimiento, HORA.isoformat()))

    assert [r.nro_sicop for r in _retirar(settings)] == [no_interesa]
    for nro in (interesa, ofertada, seguimiento, prorrogado):
        assert (settings.documents_dir / nro).exists()


def test_la_carpeta_que_no_se_pudo_borrar_se_reintenta_y_lo_demas_no_se_toca(tmp_path):
    settings = _base(tmp_path)
    _con_ficha_y_documento(settings, CERRADO, "2026-10-01T10:00:00-06:00")
    _retirar(settings)
    (settings.documents_dir / CERRADO).mkdir()  # como si el borrado de la carpeta hubiera fallado
    (settings.documents_dir / CERRADO / "resto.pdf").write_bytes(b"SIMULADO")
    (settings.documents_dir / "otra-cosa").mkdir()
    (settings.documents_dir / "20269999999").mkdir()  # sin retiro anotado: no es nuestra para borrar

    retiros = _retirar(settings)

    assert [(r.nro_sicop, r.hasta_detalle_id) for r in retiros] == [(CERRADO, None)]
    assert not (settings.documents_dir / CERRADO).exists()
    assert (settings.documents_dir / "otra-cosa").exists() and (settings.documents_dir / "20269999999").exists()


@navegador
def test_la_corrida_borra_al_cierre_y_lo_dice_en_el_resumen(tmp_path, capsys, monkeypatch):
    settings, archivos = _dos_abiertos(tmp_path, ENRICH_MAX_PER_DAY="1")
    _sql(settings, "INSERT INTO tenders (nro_sicop, fecha_cierre_recepcion, content_hash, first_seen, last_seen)"
                   " VALUES (?, '2026-10-01T10:00:00-06:00', 'h', '2026-09-01', '2026-09-01')", (CERRADO,))
    _con_ficha_y_documento(settings, CERRADO, "2026-10-01T10:00:00-06:00")
    monkeypatch.setattr(en, "_ahora", lambda: HORA)
    assert cli.main(["enrich", "cola"], settings=settings) == 0
    assert "Al correr se borrarán (cerrados, sin «Interesa» ni seguimiento): 1 cartel(es)" in capsys.readouterr().out

    corrida = _correr(settings, _Sicop(archivos=archivos))

    assert [r.nro_sicop for r in corrida.retiros] == [CERRADO]
    assert _sql(settings, "SELECT run_id FROM enrich_retiros") == [(corrida.run_id,)]
    resumen = (settings.exports_dir / f"resumen-enriquecimiento-{corrida.run_id}.txt").read_text(encoding="utf-8")
    assert "Borrado al cierre: 1 cartel(es)" in resumen and f"- {CERRADO} · cerró 01/10/2026 10:00" in resumen
