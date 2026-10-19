"""Importador del reporte 2.1 «Detalle líneas de carteles» → tabla tender_lines.

Relaciones (docs/MAPEO_DATOS.md, guía 16.3), solo por claves verificadas:
* línea → cartel por `Número SICOP` (+ secuencia si SICOP la entregara; hoy no viene).
  Si el cartel no está importado, la línea es «huérfana»: se advierte, se conserva en raw_snapshots
  y no entra a tender_lines (no se inventa el cartel).
* línea → catálogo por `Código identificación` (16 dígitos). Un código sin catálogo se advierte
  y queda marcado en la vista v_tender_lines; la línea sí se guarda.
Estimación por línea = cantidad × precio unitario, en Decimal y en la moneda de la línea.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.dinero import parse_decimal, texto_decimal
from app.importers.comun import Fila, FilaRechazada, Resultado, exigir_digitos, importar_reporte, upsert
from app.importers.csv_reader import parse_csv

# Encabezado real del archivo → campo de tender_lines (docs/MAPEO_DATOS.md, reporte 2.1).
COLUMNAS = {
    "Número SICOP": "nro_sicop",
    "Numero de linea": "numero_linea",
    "Numero partida": "numero_partida",
    "Código identificación": "codigo_identificacion",
    "Cantidad": "cantidad_solicitada",
    "Precio Unitario Estimado": "precio_unitario_estimado",
    "Moneda": "moneda",
}
_MONEDA = re.compile(r"^[A-Z]{3}$")

ADV_HUERFANA = "Línea huérfana: su cartel no está importado (queda solo en raw_snapshots)"
ADV_SIN_CATALOGO = "Código sin catálogo: clasificación no descargada"
ADV_NO_EN_CATALOGO = "Código no está en el catálogo de su clasificación"
ADV_EN_CERO = "Cantidad o precio en cero: estimación 0, no informativa"


def _validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
    nro = exigir_digitos("Número SICOP", fila["Número SICOP"])
    numero_linea = exigir_digitos("Numero de linea", fila["Numero de linea"])
    codigo = exigir_digitos("Código identificación", fila["Código identificación"], longitud=16)
    try:
        cantidad = parse_decimal(fila["Cantidad"])
        precio = parse_decimal(fila["Precio Unitario Estimado"])
    except ValueError as exc:
        raise FilaRechazada(f"monto inválido: {exc}")
    moneda = fila["Moneda"]
    if not _MONEDA.match(moneda):
        raise FilaRechazada(f"«Moneda» no válida ({moneda!r}); se esperan 3 letras, p. ej. CRC o USD")
    if cantidad == 0 or precio == 0:
        resultado.advertir(ADV_EN_CERO, linea)

    campos: dict[str, str | None] = {campo: fila[col] for col, campo in COLUMNAS.items()}
    campos["codigo_identificacion"] = codigo
    campos["estimado_linea"] = texto_decimal(cantidad * precio)
    # Clave natural para raw_snapshots: «Número SICOP|línea» (ver migración 0001).
    return Fila(f"{nro}|{numero_linea}", campos, fila)


def import_lineas(conn: sqlite3.Connection, path: Path, origen: str, raw_dir: Path,
                  source_run_id: int | None = None) -> Resultado:
    """Importa un CSV de líneas. Conviene importar antes los carteles (y el catálogo, si lo hay)."""
    raw = path.read_bytes()
    carteles = {nro for (nro,) in conn.execute("SELECT nro_sicop FROM tenders")}
    catalogo = {c for (c,) in conn.execute("SELECT codigo_identificacion FROM catalog_items")}
    clasificaciones = {c for (c,) in conn.execute("SELECT DISTINCT codigo_clasificacion FROM catalog_items")}

    def validar(fila: dict[str, str], linea: int, resultado: Resultado) -> Fila:
        validada = _validar(fila, linea, resultado)
        codigo = validada.campos["codigo_identificacion"]
        if validada.campos["nro_sicop"] not in carteles:
            resultado.advertir(ADV_HUERFANA, linea)
        elif codigo not in catalogo:
            tipo = ADV_NO_EN_CATALOGO if codigo[:8] in clasificaciones else ADV_SIN_CATALOGO
            resultado.advertir(tipo, linea)
        return validada

    def guardar(conn: sqlite3.Connection, fila: Fila, content_hash: str, import_id: int, momento: str) -> str:
        if fila.campos["nro_sicop"] not in carteles:
            return "huerfana"
        clave = {"nro_sicop": fila.campos["nro_sicop"], "numero_linea": fila.campos["numero_linea"]}
        campos = {k: v for k, v in fila.campos.items() if k not in clave}
        return upsert(conn, "tender_lines", clave, campos, content_hash, momento)

    return importar_reporte(
        conn, nombre_archivo=path.name, raw=raw, csv_file=parse_csv(raw), report="lineas", entidad="linea",
        origen=origen, raw_dir=raw_dir, requeridas=COLUMNAS, nombre_clave="Línea (Número SICOP|línea)",
        validar=validar, guardar=guardar, source_run_id=source_run_id,
    )
