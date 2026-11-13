"""Gestor de documentos, paso 2: archivos del expediente. Archivos SINTÉTICOS en tmp_path; nunca toca data/.

Reutiliza la base y los usuarios SINTÉTICOS de tests/test_seguimiento.py (Oscar admin; Ivania y Ana encargadas).
"""

import io
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime, timezone

import openpyxl
import pytest

from app import expediente_archivos as ea, historial, respaldo, seguimiento
from app.database import connect
from tests.test_panel import token_csrf
from tests.test_seguimiento import NRO, OTRO, _asignar, _dar_seguimiento, _id, _quien, clientes, db  # noqa: F401

AHORA = datetime(2026, 10, 29, 15, 0, tzinfo=timezone.utc)
MB = 1024 * 1024
PDF = b"%PDF-1.4\n% PLIEGO SINTETICO\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"


def _zip(entradas: dict[str, bytes]) -> bytes:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        for nombre, datos in entradas.items():
            zf.writestr(nombre, datos)
    return salida.getvalue()


def _xlsx() -> bytes:
    libro = openpyxl.Workbook()
    libro.active.title = "Oferta"
    libro.active.append(["Línea", "Precio SINTÉTICO"])
    libro.active.append(["1", "1000"])
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


DOCX = _zip({"[Content_Types].xml": b"<Types/>", "word/document.xml": b"<w:document/>"})
ZIP = _zip({"anexo.pdf": PDF, "nota.txt": b"texto SINTETICO"})
OLE = bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 504


@pytest.fixture
def base(tmp_path):
    return tmp_path / "expedientes"


def _guardar(db, base, nombre, datos, limite=10 * MB, email="ivania@ejemplo.test", nro=NRO):
    with closing(connect(db)) as conn:
        return ea.guardar(conn, base, nro, io.BytesIO(datos), nombre, limite, _quien(db, email), AHORA)


def _abrir(db, nro=NRO):
    with closing(connect(db)) as conn:
        seguimiento.abrir(conn, nro, _quien(db, "ivania@ejemplo.test"), AHORA)


# --- Lógica ---------------------------------------------------------------------------------------------------------

def test_guarda_con_la_huella_como_nombre_y_no_duplica(db, base):
    _abrir(db)
    archivo = _guardar(db, base, "C:\\Users\\ana\\Escritorio\\Pliego final.pdf", PDF)

    assert (archivo.nombre, archivo.tipo, archivo.tamano, archivo.subido_por) == ("Pliego final.pdf", "PDF", len(PDF),
                                                                                 "Ivania")
    assert (base / NRO / f"{archivo.sha256}.pdf").read_bytes() == PDF
    assert [p.name for p in (base / NRO).iterdir()] == [f"{archivo.sha256}.pdf"]   # sin temporales
    with pytest.raises(ea.YaEsta, match="ya está en el expediente"):
        _guardar(db, base, "otra copia.pdf", PDF)
    with closing(connect(db)) as conn:
        assert [a.nombre for a in ea.listar(conn, NRO)] == ["Pliego final.pdf"]
        eventos = [e.detalle for e in historial.ultimos(conn, ("subir_archivo",))]
    assert eventos == [f"{NRO}: Pliego final.pdf ({len(PDF)} bytes)"]


def test_un_nombre_con_carpetas_no_sale_del_expediente(db, base):
    _abrir(db)
    archivo = _guardar(db, base, "../../../../Windows/evil.pdf", PDF)
    assert archivo.nombre == "evil.pdf"
    assert [p for p in base.rglob("*") if p.is_file()] == [base / NRO / f"{archivo.sha256}.pdf"]


@pytest.mark.parametrize("nombre, datos", [("pliego.pdf", PDF), ("oferta.docx", DOCX), ("viejo.doc", OLE),
                                           ("precios.xlsx", _xlsx()), ("viejo.xls", OLE), ("anexos.zip", ZIP)])
def test_acepta_los_cuatro_tipos_por_su_contenido(db, base, nombre, datos):
    _abrir(db)
    assert _guardar(db, base, nombre, datos).nombre == nombre


@pytest.mark.parametrize("nombre, datos", [
    ("pliego.pdf", b"MZ\x90\x00 programa SINTETICO renombrado"),   # un .exe con nombre de PDF
    ("oferta.docx", ZIP),                                          # un ZIP cualquiera no es un Word
    ("precios.xlsx", DOCX),                                        # un Word no es un Excel
    ("viejo.doc", PDF),
    ("anexos.zip", PDF),
])
def test_rechaza_un_tipo_falso(db, base, nombre, datos):
    _abrir(db)
    with pytest.raises(ea.ArchivoInvalido, match="no es un .* de verdad"):
        _guardar(db, base, nombre, datos)
    assert not any(p.is_file() for p in base.rglob("*"))   # no queda nada en disco


def test_rechaza_lo_grande_lo_vacio_y_otras_extensiones(db, base):
    _abrir(db)
    with pytest.raises(ea.ArchivoMuyGrande, match="límite de 1 MB"):
        _guardar(db, base, "grande.pdf", PDF + b"0" * MB, limite=MB)
    with pytest.raises(ea.ArchivoInvalido, match="vacío"):
        _guardar(db, base, "vacio.pdf", b"")
    with pytest.raises(ea.ArchivoInvalido, match="Se aceptan PDF"):
        _guardar(db, base, "programa.exe", b"MZ")
    with pytest.raises(ea.ArchivoInvalido, match="no está en seguimiento"):
        _guardar(db, base, "pliego.pdf", PDF, nro=OTRO)
    assert not any(p.is_file() for p in base.rglob("*"))


def test_los_archivos_no_se_borran_ni_se_cambian(db, base):
    _abrir(db)
    _guardar(db, base, "pliego.pdf", PDF)
    with closing(connect(db)) as conn:
        for sql in ("DELETE FROM seguimiento_archivos", "UPDATE seguimiento_archivos SET nombre = 'x'"):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


def test_el_respaldo_incluye_los_expedientes(db, base, tmp_path):
    _abrir(db)
    _guardar(db, base, "pliego.pdf", PDF)
    r = respaldo.respaldar(db, tmp_path / "respaldos", AHORA, None, base)
    exp = r.datos["expedientes"]
    with closing(connect(db)) as conn:
        huella = ea.listar(conn, NRO)[0].sha256
    with zipfile.ZipFile(tmp_path / "respaldos" / exp["archivo"]) as zf:
        assert zf.namelist() == [f"{NRO}/{huella}.pdf"]
    assert exp["archivos"] == 1 and exp["bytes"] == len(PDF)


# --- Rutas web ------------------------------------------------------------------------------------------------------

@pytest.fixture
def web(clientes, base, monkeypatch):
    monkeypatch.setenv("EXPEDIENTES_DIR", str(base))
    monkeypatch.setenv("EXPEDIENTE_MAX_MB", "1")
    return clientes


def _subir(cliente, nombre, datos, nro=NRO, con_token=True):
    token = token_csrf(cliente.get("/oportunidades").text)
    return cliente.post(f"/seguimiento/{nro}/archivos", data={"csrf_token": token} if con_token else {},
                        files={"archivo": (nombre, datos)}, follow_redirects=False)


def _id_archivo(db, nombre):
    with closing(connect(db)) as conn:
        return next(a.id for a in ea.listar(conn, NRO) if a.nombre == nombre)


def test_la_encargada_sube_ve_y_descarga(web, db):
    _dar_seguimiento(web["ana"])
    _asignar(web["oscar"], _id(db, "ivania@ejemplo.test"))
    ivania = web["ivania"]

    respuesta = _subir(ivania, "Pliego final.pdf", PDF)
    assert respuesta.status_code == 303 and respuesta.headers["location"] == f"/seguimiento/{NRO}#archivos"
    pagina = ivania.get(f"/seguimiento/{NRO}").text
    assert "Archivo subido: Pliego final.pdf." in pagina and "hasta 1 MB" in pagina
    archivo_id = _id_archivo(db, "Pliego final.pdf")
    bajada = ivania.get(f"/seguimiento/{NRO}/archivos/{archivo_id}")
    assert bajada.content == PDF and bajada.headers["content-disposition"].startswith("attachment")
    assert bajada.headers["x-content-type-options"] == "nosniff"
    vista = ivania.get(f"/seguimiento/{NRO}/archivos/{archivo_id}/ver")
    assert vista.headers["content-type"] == "application/pdf" and vista.headers["content-disposition"].startswith("inline")


def test_ver_excel_y_zip_del_expediente(web, db):
    _dar_seguimiento(web["oscar"])
    oscar = web["oscar"]
    _subir(oscar, "precios.xlsx", _xlsx())
    _subir(oscar, "anexos.zip", ZIP)
    _subir(oscar, "oferta.docx", DOCX)

    excel = oscar.get(f"/seguimiento/{NRO}/archivos/{_id_archivo(db, 'precios.xlsx')}/ver").text
    assert "Hoja «Oferta»" in excel and "Precio SINTÉTICO" in excel and f'href="/seguimiento/{NRO}#archivos"' in excel
    zid = _id_archivo(db, "anexos.zip")
    lista = oscar.get(f"/seguimiento/{NRO}/archivos/{zid}/ver").text
    assert "anexo.pdf" in lista and f'href="/seguimiento/{NRO}/archivos/{zid}/ver/0"' in lista
    assert oscar.get(f"/seguimiento/{NRO}/archivos/{zid}/ver/0").content == PDF
    word = oscar.get(f"/seguimiento/{NRO}/archivos/{_id_archivo(db, 'oferta.docx')}/ver")
    assert word.status_code == 422 and "solo se puede descargar" in word.text
    pagina = oscar.get(f"/seguimiento/{NRO}").text
    assert pagina.count(">Ver</a>") == 2 and pagina.count(">Descargar</a>") == 3   # Word: solo «Descargar»


def test_quien_no_es_encargado_no_sube_ni_baja(web, db):
    _dar_seguimiento(web["ana"])
    _asignar(web["oscar"], _id(db, "ivania@ejemplo.test"))
    _subir(web["ivania"], "pliego.pdf", PDF)
    archivo_id = _id_archivo(db, "pliego.pdf")
    ana = web["ana"]   # dio seguimiento, pero no es la encargada

    assert _subir(ana, "otro.pdf", PDF + b"x").status_code == 403
    for ruta in (f"/seguimiento/{NRO}/archivos/{archivo_id}", f"/seguimiento/{NRO}/archivos/{archivo_id}/ver"):
        respuesta = ana.get(ruta)
        assert respuesta.status_code == 403 and PDF not in respuesta.content
    with closing(connect(db)) as conn:
        assert [a.nombre for a in ea.listar(conn, NRO)] == ["pliego.pdf"]


def test_en_un_traspaso_el_nuevo_encargado_baja_todo(web, db):
    _dar_seguimiento(web["ana"])
    _asignar(web["oscar"], _id(db, "ivania@ejemplo.test"))
    _subir(web["ivania"], "borrador.docx", DOCX)
    archivo_id = _id_archivo(db, "borrador.docx")
    _asignar(web["oscar"], _id(db, "ana@ejemplo.test"))

    assert web["ana"].get(f"/seguimiento/{NRO}/archivos/{archivo_id}").content == DOCX
    assert web["ivania"].get(f"/seguimiento/{NRO}/archivos/{archivo_id}").status_code == 403   # ya no es la encargada


def test_errores_de_subida_y_csrf(web, db):
    _dar_seguimiento(web["oscar"])
    oscar = web["oscar"]

    assert _subir(oscar, "pliego.pdf", PDF, con_token=False).status_code == 403
    falso = _subir(oscar, "pliego.pdf", b"MZ programa SINTETICO")
    assert falso.status_code == 400 and "no es un PDF de verdad" in falso.text
    grande = _subir(oscar, "grande.pdf", PDF + b"0" * (2 * MB))   # el panel lo corta antes de recibirlo
    assert grande.status_code == 413 and "1 MB" in grande.text
    _subir(oscar, "pliego.pdf", PDF)
    repetido = _subir(oscar, "copia.pdf", PDF)
    assert repetido.status_code == 409 and "ya está en el expediente" in repetido.text
    assert _subir(oscar, "pliego.pdf", PDF, nro=OTRO).status_code == 404   # no está en seguimiento
    assert oscar.get(f"/seguimiento/{NRO}/archivos/999").status_code == 404
