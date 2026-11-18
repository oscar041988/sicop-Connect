"""Gestor de documentos, paso 4: descargar todo el expediente en un ZIP. Datos y archivos SINTÉTICOS en tmp_path;
nunca toca data/.

Reutiliza la base y los usuarios SINTÉTICOS de tests/test_seguimiento.py (Oscar admin; Ivania y Ana encargadas) y
los archivos de tests/test_expediente_archivos.py.
"""

import io
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone

import pytest

from app import expediente_descarga as ed, historial, seguimiento
from app.database import connect
from tests.test_expediente_archivos import DOCX, PDF, _abrir, _guardar, base  # noqa: F401
from tests.test_seguimiento import NRO, OTRO, _asignar, _dar_seguimiento, _id, _quien, clientes, db  # noqa: F401

AHORA = datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc)   # 09:00 en Costa Rica


def _armar(db, base, email="oscar@ejemplo.test"):
    salida = io.BytesIO()
    with closing(connect(db)) as conn:
        resumen = ed.armar(conn, base, NRO, salida, _quien(db, email), AHORA)
    return resumen, zipfile.ZipFile(io.BytesIO(salida.getvalue()))


def _expediente_completo(db, base):
    """Ivania encargada, en «enviada», con 2 notas y 3 archivos (dos se llaman igual)."""
    _abrir(db)
    oscar, ivania = _quien(db, "oscar@ejemplo.test"), _quien(db, "ivania@ejemplo.test")
    with closing(connect(db)) as conn:
        seguimiento.asignar(conn, NRO, ivania.user_id, oscar, AHORA)
        seguimiento.cambiar_etapa(conn, NRO, "enviada", ivania, AHORA)
        seguimiento.escribir_nota(conn, NRO, "Pedir el pliego.\nLlamar el lunes.", ivania, AHORA)
        seguimiento.escribir_nota(conn, NRO, "Visto.", oscar, AHORA)
    return [_guardar(db, base, "Pliego.pdf", PDF), _guardar(db, base, "oferta.docx", DOCX),
            _guardar(db, base, "pliego.PDF", PDF + b"% version 2\n")]


# --- Lógica ---------------------------------------------------------------------------------------------------------

def test_nombres_repetidos_llevan_su_numero():
    assert ed._nombres_unicos(["a.pdf", "b.pdf", "A.pdf", "a.pdf", "a (2).pdf"]) == [
        "a.pdf", "b.pdf", "A (2).pdf", "a (3).pdf", "a (2) (2).pdf"]


def test_el_zip_trae_archivos_notas_e_historial(db, base):
    archivos = _expediente_completo(db, base)
    resumen, zf = _armar(db, base)

    assert resumen == ed.Resumen(archivos=3, notas=2, faltantes=0)
    assert sorted(zf.namelist()) == ["archivos/Pliego.pdf", "archivos/oferta.docx", "archivos/pliego (2).PDF",
                                     "expediente.txt"]
    assert zf.read("archivos/Pliego.pdf") == PDF and zf.read("archivos/pliego (2).PDF") == PDF + b"% version 2\n"
    assert zf.read("archivos/oferta.docx") == DOCX
    texto = zf.read("expediente.txt").decode("utf-8")
    for esperado in (f"EXPEDIENTE DEL CARTEL {NRO}",
                     "Descargado el 30/10/2026 09:00 por Oscar",
                     "Cartel: Servicio de monitoreo GPS de vehículos",
                     "Institución: Municipalidad Sintética A",
                     "Encargado vigente: Ivania", "Etapa: Enviada",
                     "- Ivania · asignado por Oscar · 30/10/2026 09:00",
                     "- Enviada · la puso Ivania · 30/10/2026 09:00",
                     "== NOTAS (2,", "--- Ivania · 30/10/2026 09:00\nPedir el pliego.\nLlamar el lunes.",
                     "--- Oscar · 30/10/2026 09:00\nVisto.",
                     f"- archivos/Pliego.pdf · PDF · 0.0 MB · subido por Ivania · 29/10/2026 09:00"
                     f" · SHA-256 {archivos[0].sha256}"):
        assert esperado in texto
    assert texto.index("--- Oscar") < texto.index("--- Ivania")   # notas: la más reciente primero
    with closing(connect(db)) as conn:
        eventos = [e.detalle for e in historial.ultimos(conn, ("descargar_expediente",))]
    assert eventos == [f"{NRO}: 3 archivos, 2 notas"]


def test_un_archivo_que_falta_en_disco_no_detiene_la_descarga(db, base):
    archivos = _expediente_completo(db, base)
    (base / NRO / f"{archivos[1].sha256}.docx").unlink()
    resumen, zf = _armar(db, base)

    assert resumen == ed.Resumen(archivos=2, notas=2, faltantes=1)
    assert "archivos/oferta.docx" not in zf.namelist()
    assert "- FALTA EN DISCO (no va en el ZIP): oferta.docx" in zf.read("expediente.txt").decode("utf-8")
    with closing(connect(db)) as conn:
        assert historial.ultimos(conn, ("descargar_expediente",))[0].detalle == \
            f"{NRO}: 2 archivos, 2 notas, 1 faltan en disco"


def test_expediente_vacio_y_cartel_sin_seguimiento(db, base):
    _abrir(db)
    resumen, zf = _armar(db, base)
    texto = zf.read("expediente.txt").decode("utf-8")
    assert resumen == ed.Resumen(0, 0, 0) and zf.namelist() == ["expediente.txt"]
    assert "Encargado vigente: sin encargado" in texto and "Sin notas." in texto and "Sin archivos." in texto
    with closing(connect(db)) as conn, pytest.raises(seguimiento.SeguimientoInvalido, match="no está en seguimiento"):
        ed.armar(conn, base, OTRO, io.BytesIO(), _quien(db, "oscar@ejemplo.test"), AHORA)


# --- Panel ----------------------------------------------------------------------------------------------------------

@pytest.fixture
def web(clientes, base, monkeypatch, tmp_path):
    monkeypatch.setenv("EXPEDIENTES_DIR", str(base))
    temporales = tmp_path / "temporales"
    temporales.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporales))   # para comprobar que el ZIP temporal se borra
    return clientes, temporales


def test_descargan_el_encargado_y_los_administradores_y_cambia_con_el_traspaso(web, db, base):
    clientes, temporales = web
    _dar_seguimiento(clientes["ana"])
    _asignar(clientes["oscar"], _id(db, "ivania@ejemplo.test"))
    _guardar(db, base, "Pliego.pdf", PDF)

    assert clientes["ana"].get(f"/seguimiento/{NRO}/descargar").status_code == 403   # dio seguimiento, no es la encargada
    respuesta = clientes["ivania"].get(f"/seguimiento/{NRO}/descargar")
    assert respuesta.status_code == 200 and respuesta.headers["content-type"] == "application/zip"
    assert respuesta.headers["content-disposition"].startswith(f'attachment; filename="expediente_{NRO}_')
    assert "archivos/Pliego.pdf" in zipfile.ZipFile(io.BytesIO(respuesta.content)).namelist()
    assert clientes["oscar"].get(f"/seguimiento/{NRO}/descargar").status_code == 200
    assert list(temporales.iterdir()) == []   # el ZIP temporal se borró después de enviarlo
    # Traspaso: la nueva encargada baja todo; la anterior ya no.
    _asignar(clientes["oscar"], _id(db, "ana@ejemplo.test"))
    assert clientes["ana"].get(f"/seguimiento/{NRO}/descargar").status_code == 200
    assert clientes["ivania"].get(f"/seguimiento/{NRO}/descargar").status_code == 403
    with closing(connect(db)) as conn:
        quienes = [e.actor for e in historial.ultimos(conn, ("descargar_expediente",))]
    assert quienes == ["Ana", "Oscar", "Ivania"]   # las negadas no se anotan


def test_boton_y_cartel_sin_seguimiento(web, db):
    clientes, _ = web
    _dar_seguimiento(clientes["ana"])
    assert f'href="/seguimiento/{NRO}/descargar"' in clientes["oscar"].get(f"/seguimiento/{NRO}").text
    assert clientes["oscar"].get(f"/seguimiento/{OTRO}/descargar").status_code == 404
    assert clientes["oscar"].get("/seguimiento/..%2F..%2Fx/descargar").status_code == 404
