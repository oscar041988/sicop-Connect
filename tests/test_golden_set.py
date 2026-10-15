"""El golden set es válido: lo editan personas, así que se revisa su forma (no las etiquetas)."""

from pathlib import Path

from app.importers.csv_reader import read_csv

GOLDEN = Path(__file__).parent / "golden" / "golden_set.csv"
GOLDEN_LINEAS = Path(__file__).parent / "golden" / "golden_lineas.csv"
COLUMNAS = ["nro_sicop", "titulo", "etiqueta", "familia_esperada", "confirmada", "nota", "fuente", "actualizado"]
ETIQUETAS = {"interesa", "no_interesa", "falso_positivo_conocido"}
FAMILIAS = {"gps_flotas", "videotelematica", "seguridad_vial", "conteo_pasajeros", "transporte_corporativo",
            "rastreo_activos", "mantenimiento_flotas", "iot_frio", "camaras_corporales"}


def _filas():
    archivo = read_csv(GOLDEN)
    assert archivo.header == COLUMNAS
    return [dict(zip(archivo.header, valores)) for _, valores in archivo.rows]


def test_golden_set_tiene_entre_20_y_40_carteles_unicos():
    nros = [f["nro_sicop"] for f in _filas()]

    assert 20 <= len(nros) <= 40
    assert len(set(nros)) == len(nros)
    assert all(n.isdigit() and len(n) == 11 for n in nros)  # texto intacto (no pasó por Excel)


def test_etiquetas_y_familias_validas():
    for f in _filas():
        assert f["etiqueta"] in ETIQUETAS, f["nro_sicop"]
        assert f["confirmada"] in {"sí", "no"}, f["nro_sicop"]
        familias = {x for x in f["familia_esperada"].split(";") if x}
        assert familias <= FAMILIAS, f["nro_sicop"]
        # «interesa» exige familia; «no interesa» no la lleva; un falso positivo puede llevar la que aparenta.
        if f["etiqueta"] == "interesa":
            assert familias, f["nro_sicop"]
        if f["etiqueta"] == "no_interesa":
            assert not familias, f["nro_sicop"]


def test_hay_casos_de_cada_tipo():
    etiquetas = {f["etiqueta"] for f in _filas() if f["confirmada"] == "sí"}

    assert {"interesa", "no_interesa"} <= etiquetas


def test_lineas_del_golden_set_son_de_sus_carteles():
    archivo = read_csv(GOLDEN_LINEAS)
    assert archivo.header == ["nro_sicop", "numero_linea", "codigo_identificacion", "nombre_catalogo"]
    nros = {f["nro_sicop"] for f in _filas()}
    for _, valores in archivo.rows:
        f = dict(zip(archivo.header, valores))
        assert f["nro_sicop"] in nros, f["nro_sicop"]
        assert len(f["codigo_identificacion"]) == 16 and f["codigo_identificacion"].isdigit()  # texto intacto
        assert f["nombre_catalogo"].strip()
