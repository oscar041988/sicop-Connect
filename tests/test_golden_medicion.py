"""Medición de las reglas contra el golden set (guía, sección 16.5; criterio O3: ≥ 80 % de acierto).

Datos REALES: carteles etiquetados por Oscar (golden_set.csv) y el nombre de catálogo de sus líneas
(golden_lineas.csv, copiado de la base). Se evalúan título y líneas, igual que el comando evaluate.
Las filas provisionales (confirmada = no) se muestran pero no cuentan.

Un cartel es «candidato» de una familia si su encaje es Alta o Media. Acierto:
* interesa → alguna de sus familias esperadas es candidata.
* no_interesa y falso_positivo_conocido → ninguna familia es candidata.

Ver el informe: python -m pytest tests/test_golden_medicion.py -s
"""

from pathlib import Path

from app.importers.csv_reader import read_csv
from app.matching.evaluar import Texto, evaluar_textos
from app.matching.reglas import cargar_reglas

GOLDEN = Path(__file__).parent / "golden" / "golden_set.csv"
GOLDEN_LINEAS = Path(__file__).parent / "golden" / "golden_lineas.csv"
CANDIDATO = {"alta", "media"}
META_O3 = 80.0


def lineas_por_cartel() -> dict[str, list[Texto]]:
    archivo = read_csv(GOLDEN_LINEAS)
    lineas: dict[str, list[Texto]] = {}
    for _, valores in archivo.rows:
        f = dict(zip(archivo.header, valores))
        lineas.setdefault(f["nro_sicop"], []).append(Texto(f"línea {f['numero_linea']}", f["nombre_catalogo"]))
    return lineas


def medir():
    reglas = cargar_reglas()
    lineas = lineas_por_cartel()
    archivo = read_csv(GOLDEN)
    filas = [dict(zip(archivo.header, valores)) for _, valores in archivo.rows]
    contadas, aciertos, fallos, provisionales = 0, 0, [], []
    for f in filas:
        evaluaciones = evaluar_textos(reglas, f["titulo"], lineas.get(f["nro_sicop"]))
        candidatas = {e.familia for e in evaluaciones if e.encaje in CANDIDATO}
        esperadas = {x for x in f["familia_esperada"].split(";") if x}
        acierto = bool(candidatas & esperadas) if f["etiqueta"] == "interesa" else not candidatas
        caso = (f, evaluaciones, acierto)
        if f["confirmada"] != "sí":
            provisionales.append(caso)
            continue
        contadas += 1
        aciertos += acierto
        if not acierto:
            fallos.append(caso)
    return reglas.version, contadas, aciertos, fallos, provisionales


def _describir(f, evaluaciones) -> list[str]:
    lineas = [f"  {f['nro_sicop']} · {f['etiqueta']} · esperada: {f['familia_esperada'] or '—'}",
              f"      {f['titulo']}"]
    if not evaluaciones:
        lineas.append("      obtenido: ninguna señal")
    for e in evaluaciones:
        lineas.append(f"      obtenido: {e.familia} -> {e.encaje} · {e.regla} · {e.evidencia}")
    return lineas


def test_porcentaje_de_acierto_del_golden_set(capsys):
    version, contadas, aciertos, fallos, provisionales = medir()
    porcentaje = 100 * aciertos / contadas
    informe = [f"Golden set · reglas {version} · acierto {aciertos}/{contadas} = {porcentaje:.1f} %"
               f" (meta O3: al menos {META_O3:.0f} %)", f"Fallidos ({len(fallos)}):"]
    for f, evaluaciones, _ in fallos:
        informe += _describir(f, evaluaciones)
    informe.append(f"Provisionales, no cuentan ({len(provisionales)}):")
    for f, evaluaciones, acierto in provisionales:
        informe += [(l + ("  [acertaría]" if acierto else "  [fallaría]")) if i == 0 else l
                    for i, l in enumerate(_describir(f, evaluaciones))]
    with capsys.disabled():
        print("\n" + "\n".join(informe))

    assert contadas >= 20
    assert porcentaje >= META_O3, f"Acierto {porcentaje:.1f} % por debajo de la meta O3"
