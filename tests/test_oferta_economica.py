"""Oferta económica en PDF (app/oferta_economica.py; DECISION_PROPUESTA.md). Datos SINTÉTICOS
(tests/fixtures/oferta_sintetica.yaml): ningún precio real va en las pruebas."""

from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from app import cli
from app import oferta_economica as oe
from tests.test_enriquecimiento import navegador

DATOS = Path(__file__).parent / "fixtures" / "oferta_sintetica.yaml"


def _datos(**cambios) -> dict:
    datos = yaml.safe_load(DATOS.read_text(encoding="utf-8"))
    datos.update(cambios)
    return datos


@pytest.mark.parametrize("monto, texto", [
    ("1", "Un colón exacto."),
    ("21", "Veintiún colones exactos."),
    ("100", "Cien colones exactos."),
    ("101", "Ciento un colones exactos."),
    ("1100", "Mil cien colones exactos."),
    ("21000", "Veintiún mil colones exactos."),
    ("121500", "Ciento veintiún mil quinientos colones exactos."),
    ("1000000", "Un millón de colones exactos."),
    ("21000000", "Veintiún millones de colones exactos."),
    ("1500000", "Un millón quinientos mil colones exactos."),
    ("2400000", "Dos millones cuatrocientos mil colones exactos."),
    ("1000000000", "Mil millones de colones exactos."),
    ("1234567.50", "Un millón doscientos treinta y cuatro mil quinientos sesenta y siete colones con 50/100."),
    ("0.5", "Cero colones con 50/100."),
])
def test_monto_en_letras(monto, texto):
    assert oe.monto_en_letras(Decimal(monto), "CRC") == texto


def test_monto_en_letras_en_dolares_y_errores():
    assert oe.monto_en_letras(Decimal("2000.25"), "USD") == "Dos mil dólares estadounidenses con 25/100."
    with pytest.raises(oe.OfertaError, match="Moneda"):
        oe.monto_en_letras(Decimal("1"), "EUR")
    with pytest.raises(oe.OfertaError, match="negativo"):
        oe.monto_en_letras(Decimal("-1"), "CRC")


def test_tabla_mensual_exenta_y_desglose_que_cuadra():
    o = oe.leer(_datos())
    assert o.subtotal_periodo == Decimal("200000.00")                  # 8 × ₡25 000 al mes
    assert o.subtotal == Decimal("2400000.00") and o.iva == 0 and o.total == Decimal("2400000.00")
    montos = [r.monto for r in o.rubros]
    assert montos == [Decimal("799920.00"), Decimal("799920.00"), Decimal("400080.00"), Decimal("400080.00")]
    assert sum(montos) == o.subtotal                                     # cuadra al céntimo
    assert oe.formato(o.total, "CRC") == "₡2 400 000,00"


def test_iva_con_tasa_y_precio_unico():
    o = oe.leer(_datos(meses=None, iva={"tasa": 13}))
    assert o.subtotal == Decimal("200000.00") and o.iva == Decimal("26000.00") and o.total == Decimal("226000.00")


def test_el_ultimo_rubro_absorbe_el_redondeo():
    rubros = [oe.Rubro(c, c, Decimal(p)) for c, p in zip(oe.RUBROS, ("33.33", "33.33", "33.33", "0.01"))]
    oe.desglosar(Decimal("1000.01"), rubros)
    assert sum(r.monto for r in rubros) == Decimal("1000.01")


@pytest.mark.parametrize("cambios, mensaje", [
    ({"desglose": {**_datos()["desglose"], "utilidad": {"nombre": "Utilidad", "porcentaje": "20"}}}, "suman"),
    ({"moneda": "EUR"}, "Moneda"),
    ({"iva": {}}, "tasa"),
    ({"iva": {"tasa": 13, "exento": "x"}}, "una de las dos"),
    ({"iva": {"exento": ""}}, "por qué"),
    ({"lineas": [{"cantidad": 1, "precio_unitario": 5}]}, "descripcion"),
    ({"lineas": [{"descripcion": "x", "cantidad": 0, "precio_unitario": 5}]}, "mayor que 0"),
    ({"lineas": [{"descripcion": "x", "cantidad": 1, "precio_unitario": "cinco"}]}, "no es un número"),
    ({"procedimiento": ""}, "procedimiento"),
    ({"meses": 0}, "entre 1 y 120"),
    ({"empresa": {"nombre": "X"}}, "cedula_juridica"),
])
def test_datos_que_no_sirven_dicen_cual(cambios, mensaje):
    with pytest.raises(oe.OfertaError, match=mensaje):
        oe.leer(_datos(**cambios))


def test_html_escapado_con_ultima_linea_letras_y_formula():
    from datetime import date
    o = oe.leer(_datos(objeto="Objeto <script>alert(1)</script> SINTÉTICO"))
    html = " ".join(oe.html(o, date(2026, 11, 9)).split())
    assert "&lt;script&gt;" in html and "<script>alert(1)" not in html
    assert "Última línea" in html and "Dos millones cuatrocientos mil colones exactos." in html
    assert "PV = PC" in html and "9 de noviembre de 2026" in html
    assert "Registro Electrónico Oficial de Proveedores" in html


@navegador
def test_comando_genera_el_pdf(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path / "exports"))
    from app.config import load_settings
    settings = load_settings(env_file=None, environ={"EXPORTS_DIR": str(tmp_path / "exports")})
    assert cli.oferta_economica_cmd(settings, DATOS, None) == 0
    salida = capsys.readouterr().out
    assert "Dos millones cuatrocientos mil colones exactos." in salida
    [pdf] = list((tmp_path / "exports" / "ofertas").rglob("*.pdf"))
    assert pdf.read_bytes().startswith(b"%PDF")
    import pdfplumber
    with pdfplumber.open(pdf) as doc:
        texto = " ".join(p.extract_text() or "" for p in doc.pages)
    assert "₡2 400 000,00" in texto and "Desglose del precio" in texto


def test_comando_con_datos_malos_no_hace_pdf(tmp_path, capsys):
    malo = tmp_path / "malo.yaml"
    malo.write_text("moneda: EUR\n", encoding="utf-8")
    from app.config import load_settings
    settings = load_settings(env_file=None, environ={"EXPORTS_DIR": str(tmp_path / "exports")})
    assert cli.oferta_economica_cmd(settings, malo, None) == 1
    assert "Error" in capsys.readouterr().err and not (tmp_path / "exports").exists()
