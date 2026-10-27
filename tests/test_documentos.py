"""Documentos de la ficha (enriquecimiento, lección 3) con SICOP y documentos SIMULADOS.

La revisión y el texto se prueban sin navegador con tests/fixtures/documentos_simulados/. La descarga corre un
Chromium real sin ventana contra la página SIMULADA (tests/fixtures/sicop_concursos_simulado.html): el clic en un
documento pide downloadWithPAR y luego el archivo al «almacén», que responde con los bytes que pone cada prueba.
Nunca sale a internet."""

import importlib.util
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app import cli
from app.database import apply_migrations
from app.respaldo import respaldar
from app.sources import sicop_documentos as sd
from tests.test_ficha import ABARROTES, ESPERA_MS, GPS, HORA, SANTA_ANA, _chromium_instalado, _Pausas, _settings, \
    _Sicop
from app.sources import sicop_tender_detail as std

DOCS = Path(__file__).parent / "fixtures" / "documentos_simulados"
_spec = importlib.util.spec_from_file_location("hacer_documentos", DOCS / "hacer_documentos.py")
hacer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hacer)

CON_TEXTO = (DOCS / "con_texto.pdf").read_bytes()
ESCANEADO = (DOCS / "escaneado.pdf").read_bytes()
FALSO = (DOCS / "falso.pdf").read_bytes()
PLIEGO_ZIP = (DOCS / "pliego.zip").read_bytes()
XLSX = (DOCS / "formulario.xlsx").read_bytes()
CLAVE = "CLAVE-SIMULADA-NO-ANOTAR"

navegador = pytest.mark.skipif(not _chromium_instalado(),
                               reason="Chromium de Playwright no instalado: python -m playwright install chromium")


def _lista(nro: str) -> list[dict]:
    return json.loads((Path(__file__).parent / "fixtures" / "ficha_simulada" / nro / "documentos.json")
                      .read_text(encoding="utf-8"))


def _archivos(nro: str, **por_seq) -> dict:
    """Un archivo SIMULADO distinto para cada documento de la ficha, según su extensión; por_seq lo reemplaza."""
    archivos = {}
    for d in _lista(nro):
        seq, ext = str(d["docFileSeqno"]), Path(d["serverFileNm"]).suffix
        if f"d{seq}" in por_seq:
            archivos[d["serverFileNm"]] = por_seq[f"d{seq}"]
        elif ext == ".pdf":
            archivos[d["serverFileNm"]] = hacer.pdf_con_texto([f"SIMULADO documento {seq} de {nro}"])
        elif ext == ".zip":
            archivos[d["serverFileNm"]] = hacer.zip_con({f"interno {seq}.pdf": hacer.pdf_con_texto([f"SIMULADO zip {seq}"])})
        else:
            archivos[d["serverFileNm"]] = hacer.zip_con({"[Content_Types].xml": f"<Types n='{seq}'/>".encode()})
    return archivos


def _enriquecer(settings, nros, sicop, pausas=None):
    return std.enriquecer(settings, list(nros), dormir=pausas or _Pausas(), reloj=lambda: HORA,
                          preparar_contexto=sicop, espera_ms=ESPERA_MS, documentos=True, espera_documento_ms=ESPERA_MS)


def _filas(settings, tabla):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(f) for f in conn.execute(f"SELECT * FROM {tabla} ORDER BY id")]


def _por_seq(settings):
    return {f["doc_seq"]: f for f in _filas(settings, "tender_documents")}


# --- Revisión y texto, sin navegador ---------------------------------------------------------------------------

@pytest.mark.parametrize("datos,extension,rechazo", [
    (CON_TEXTO, ".pdf", None),
    (FALSO, ".pdf", "no es un PDF"),
    (XLSX, ".xlsx", None),
    (CON_TEXTO, ".xlsx", "su contenido no es de ese tipo"),
    (PLIEGO_ZIP, ".zip", None),
    (b"MZ\x90\x00", ".exe", "no permitido"),
    (b"", ".pdf", "vacío"),
    (CON_TEXTO, ".txt", None),
])
def test_validar_revisa_la_firma_no_la_extension(datos, extension, rechazo):
    motivo = sd.validar(datos, extension, 50 * sd.MB)
    assert (motivo is None) if rechazo is None else (rechazo in motivo)


def test_validar_rechaza_lo_que_pasa_del_maximo():
    assert sd.validar(CON_TEXTO, ".pdf", 100).startswith("pesa")


def test_texto_de_un_pdf_pagina_por_pagina():
    texto = sd.extraer_texto(CON_TEXTO, ".pdf")
    assert (texto.estado, texto.paginas) == ("extraido", 2)
    assert texto.filas == [("", 1, "SIMULADO Pliego de condiciones: alquiler de cámaras corporales"),
                           ("", 2, "SIMULADO Garantía de cumplimiento: 5 por ciento")]


def test_pdf_escaneado_es_sin_texto_y_no_vacio():
    texto = sd.extraer_texto(ESCANEADO, ".pdf")
    assert (texto.estado, texto.paginas, texto.filas) == ("sin_texto", 1, [])
    assert "escaneado" in texto.motivo


def test_pdf_danado_es_error_sin_romper_nada():
    texto = sd.extraer_texto(b"%PDF-1.4\nesto no es un PDF de verdad", ".pdf")
    assert texto.estado == "error"


def test_texto_de_los_pdf_dentro_de_un_zip():
    texto = sd.extraer_texto(PLIEGO_ZIP, ".zip")
    assert texto.estado == "extraido"
    assert texto.filas == [("Especificaciones/pliego simulado.pdf", 1, "SIMULADO dentro del ZIP: bodycam con GPS")]


def test_word_y_excel_solo_se_guardan():
    assert sd.extraer_texto(XLSX, ".xlsx").estado == "no_aplica"


def test_zip_con_demasiados_archivos_es_error():
    muchos = hacer.zip_con({f"{i}.pdf": CON_TEXTO for i in range(sd.MAX_ENTRADAS_ZIP + 1)})
    assert sd.extraer_texto(muchos, ".zip").estado == "error"


def test_migrate_dos_veces_sin_error(tmp_path):
    db = tmp_path / "sicop.db"
    assert "0019_documentos.sql" in apply_migrations(db)
    assert apply_migrations(db) == []


@navegador
def test_documentos_y_texto_no_se_modifican_ni_se_borran(tmp_path):
    settings = _settings(tmp_path)
    _enriquecer(settings, [GPS], _Sicop(archivos=_archivos(GPS)))
    with closing(sqlite3.connect(settings.database_path)) as conn:
        for sql, mensaje in [("DELETE FROM tender_documents", "no se borran"),
                             ("UPDATE tender_documents SET estado = 'fallo'", "no se modifican"),
                             ("DELETE FROM tender_document_text", "no se borra"),
                             ("UPDATE tender_document_text SET texto = ''", "no se modifica")]:
            with pytest.raises(sqlite3.IntegrityError, match=mensaje):
                conn.execute(sql)


# --- Descarga con el navegador (SIMULADO) ----------------------------------------------------------------------

@navegador
def test_baja_guarda_y_extrae_los_documentos_de_la_ficha(tmp_path):
    settings = _settings(tmp_path)
    pausas = _Pausas()
    sicop = _Sicop(archivos=_archivos(GPS, d4=ESCANEADO))

    (consulta,) = _enriquecer(settings, [GPS], sicop, pausas)

    assert consulta.resultado == "nueva", consulta.motivo
    docs = _por_seq(settings)
    assert {s: (d["estado"], d["texto_estado"]) for s, d in docs.items()} == {
        "1": ("guardado", "extraido"), "2": ("guardado", "no_aplica"), "3": ("guardado", "no_aplica"),
        "4": ("guardado", "sin_texto"), "5": ("guardado", "extraido")}
    for d in docs.values():
        archivo = settings.documents_dir / d["ruta_local"]
        assert archivo.read_bytes() == sicop.archivos[d["server_file"]]
        assert d["ruta_local"] == f"{GPS}/{d['server_file']}" and len(d["sha256"]) == 64
    assert docs["1"]["nombre_original"] == "Código de conducta del Conglomerado (Código de Ética) V8 02-2025.pdf"
    textos = _filas(settings, "tender_document_text")
    assert [t["texto"] for t in textos] == [f"SIMULADO documento 1 de {GPS}", f"SIMULADO documento 5 de {GPS}"]
    assert pausas.segundos == [8] * 5  # una pausa antes de cada documento


@navegador
def test_la_segunda_vez_no_vuelve_a_bajar_lo_guardado(tmp_path):
    settings = _settings(tmp_path)
    _enriquecer(settings, [GPS], _Sicop(archivos=_archivos(GPS)))
    otra = _Sicop(archivos=_archivos(GPS))

    (consulta,) = _enriquecer(settings, [GPS], otra)

    assert {d.estado for d in consulta.documentos} == {"ya_guardado"}
    assert otra.pedidos_al_almacen == []
    assert len(_filas(settings, "tender_documents")) == 5


@navegador
def test_archivo_falso_se_rechaza_y_no_se_escribe(tmp_path):
    settings = _settings(tmp_path)

    _enriquecer(settings, [GPS], _Sicop(archivos=_archivos(GPS, d1=FALSO)))

    falso = _por_seq(settings)["1"]
    assert falso["estado"] == "rechazado" and "no es un PDF" in falso["motivo"]
    assert falso["ruta_local"] is None
    assert not (settings.documents_dir / GPS / falso["server_file"]).exists()
    assert _por_seq(settings)["5"]["estado"] == "guardado"  # los demás siguen


@navegador
def test_mismo_contenido_dos_veces_es_un_solo_archivo(tmp_path):
    settings = _settings(tmp_path)

    _enriquecer(settings, [GPS], _Sicop(archivos=_archivos(GPS, d1=CON_TEXTO, d5=CON_TEXTO)))

    docs = _por_seq(settings)
    assert (docs["1"]["estado"], docs["5"]["estado"]) == ("guardado", "duplicado")
    assert not (settings.documents_dir / GPS / docs["5"]["server_file"]).exists()


@navegador
def test_demasiado_grande_segun_sicop_no_se_pide(tmp_path):
    settings = _settings(tmp_path, DOCUMENT_MAX_MB="1")
    sicop = _Sicop(archivos=_archivos(SANTA_ANA))

    _enriquecer(settings, [SANTA_ANA], sicop)

    grande = _por_seq(settings)["4"]  # 1.81 MB según la lista de SICOP
    assert grande["estado"] == "omitido_tamano" and "no se pide" in grande["motivo"]
    assert grande["server_file"] not in sicop.pedidos_al_almacen


@navegador
def test_si_llega_mas_grande_de_lo_permitido_no_se_guarda(tmp_path):
    settings = _settings(tmp_path, DOCUMENT_MAX_MB="1")
    enorme = b"%PDF-1.4\n" + b"0" * (sd.MB + 10)

    _enriquecer(settings, [GPS], _Sicop(archivos=_archivos(GPS, d1=enorme)))

    doc = _por_seq(settings)["1"]
    assert doc["estado"] == "omitido_tamano" and doc["motivo"].startswith("pesa")
    assert not (settings.documents_dir / GPS / doc["server_file"]).exists()


@navegador
def test_tope_por_cartel(tmp_path):
    settings = _settings(tmp_path, DOCUMENTS_MAX_MB_PER_TENDER="1")
    sicop = _Sicop(archivos=_archivos(SANTA_ANA))

    _enriquecer(settings, [SANTA_ANA], sicop)

    docs = _por_seq(settings)
    assert docs["4"]["estado"] == "omitido_tope" and "tope de 1 MB" in docs["4"]["motivo"]
    assert docs["4"]["server_file"] not in sicop.pedidos_al_almacen
    assert docs["8"]["estado"] == "guardado"  # 0.35 MB: sí cabe
    # Santa Ana: los documentos son 1, 2, 4… (la columna «No.» es la fila) y el 6 tiene doble espacio en el nombre.
    assert {s: d["estado"] for s, d in docs.items() if s != "4"} == {s: "guardado" for s in "125678"}


@navegador
def test_un_documento_que_no_llega_no_detiene_los_demas(tmp_path):
    settings = _settings(tmp_path)
    archivos = _archivos(GPS)
    archivos[_lista(GPS)[0]["serverFileNm"]] = 404

    (consulta,) = _enriquecer(settings, [GPS], _Sicop(archivos=archivos))

    assert consulta.resultado == "nueva"
    docs = _por_seq(settings)
    assert docs["1"]["estado"] == "fallo" and "HTTP 404" in docs["1"]["motivo"]
    assert [docs[s]["estado"] for s in "2345"] == ["guardado"] * 4


@navegador
def test_tabla_con_paginas_y_zip_con_pdf(tmp_path):
    """El convenio de abarrotes: 49 documentos (5 páginas de la tabla), la mayoría ZIP."""
    settings = _settings(tmp_path)

    (consulta,) = _enriquecer(settings, [ABARROTES], _Sicop(archivos=_archivos(ABARROTES)))

    docs = _por_seq(settings)
    fallos = [(d["doc_seq"], d["motivo"]) for d in docs.values() if d["estado"] != "guardado"]
    assert len(docs) == 49 and not fallos, fallos
    zips = [d for d in docs.values() if d["extension"] == ".zip"]
    assert len(zips) == 30 and {d["texto_estado"] for d in zips} == {"extraido"}
    internos = {t["archivo_interno"] for t in _filas(settings, "tender_document_text")}
    assert "interno 3.pdf" in internos


@navegador
def test_si_la_tabla_tiene_otro_orden_vuelve_a_la_primera_pagina(tmp_path):
    settings = _settings(tmp_path)

    _enriquecer(settings, [ABARROTES], _Sicop("orden_distinto", archivos=_archivos(ABARROTES)))

    docs = _por_seq(settings)
    assert len(docs) == 49 and {d["estado"] for d in docs.values()} == {"guardado"}


@navegador
def test_captcha_al_bajar_detiene_todo_y_la_ficha_queda(tmp_path):
    settings = _settings(tmp_path)

    consultas = _enriquecer(settings, [GPS, SANTA_ANA], _Sicop("captcha_en_descarga", archivos=_archivos(GPS)))

    assert [c.resultado for c in consultas] == ["control", "no_consultado"]
    assert "control no automatizable" in consultas[0].motivo
    assert len(_filas(settings, "tender_details")) == 1  # la ficha sí se guardó
    assert _filas(settings, "tender_documents") == []


@navegador
def test_la_clave_temporal_no_queda_en_ningun_lado(tmp_path, monkeypatch, capsys):
    settings = _settings(tmp_path)
    monkeypatch.setattr(cli, "_opciones_enrich", lambda: {
        "preparar_contexto": _Sicop(archivos=_archivos(GPS)), "espera_ms": ESPERA_MS, "dormir": _Pausas(),
        "espera_documento_ms": ESPERA_MS})

    codigo = cli.main(["enrich", "--nro", GPS, "--documentos"], settings=settings)

    salida = capsys.readouterr()
    assert codigo == 0
    assert "Documentos: 5 · 5 guardados (texto: 3 con texto" in salida.out
    assert CLAVE not in salida.out + salida.err
    with closing(sqlite3.connect(settings.database_path)) as conn:
        assert CLAVE not in "".join(str(fila) for t in ("tender_documents", "tender_document_text", "tender_details")
                                    for fila in conn.execute(f"SELECT * FROM {t}"))
    assert not [p for p in settings.documents_dir.rglob("*") if CLAVE in str(p)]


@navegador
def test_el_respaldo_incluye_los_documentos(tmp_path):
    settings = _settings(tmp_path)
    _enriquecer(settings, [GPS], _Sicop(archivos=_archivos(GPS)))

    r = respaldar(settings.database_path, tmp_path / "respaldos", HORA, settings.documents_dir)

    import zipfile
    assert r.datos["documentos"]["archivos"] == 5
    assert r.datos["filas"]["tender_documents"] == 5
    with zipfile.ZipFile(tmp_path / "respaldos" / r.datos["documentos"]["archivo"]) as zf:
        assert sorted(zf.namelist()) == sorted(f"{GPS}/{d['serverFileNm']}" for d in _lista(GPS))
