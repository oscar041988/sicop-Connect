"""Oferta económica de un cartel en PDF (docs/DECISION_PROPUESTA.md, aprobado por Oscar el 2026-11-09).

La app FORMULA el archivo; una persona de Hermatix lo revisa, lo firma con firma digital y lo sube a SICOP. Sigue la
estructura de la oferta que ganó Hermatix en Tarrazú (2025): carta de presentación, tabla de precios con el monto en
letras, condiciones generales, desglose del precio y fórmula de reajuste.

* Todo lo calcula la app, sin IA: los montos en Decimal con su moneda (nunca se suman monedas distintas), el monto en
  letras y el desglose, que cuadra al céntimo con el total.
* El precio lo escribe y lo aprueba una persona: la app no propone precios.
* Nada de esto inventa datos de SICOP: el procedimiento, la institución y el objeto los da quien prepara la oferta (o
  salen del cartel en la base).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import PROJECT_ROOT

PLANTILLAS = PROJECT_ROOT / "app" / "web" / "templates"
LOGO = PROJECT_ROOT / "app" / "web" / "static" / "logo-hermatix.png"
# Membrete de Hermatix: solo el logo con el nombre, arriba a la izquierda, sin franjas de color (pedido de Oscar,
# 2026-11-11). Recortado de membrete-cabecera.png, el de la oferta que ganó en Tarrazú (2025).
MEMBRETE_LOGO = PROJECT_ROOT / "app" / "web" / "static" / "membrete-logo.png"
MARGENES_MM = {"top": 30, "bottom": 20, "left": 25, "right": 26}
ALTO_LOGO_MM = 12
CENTIMO = Decimal("0.01")
CIEN = Decimal("100")
MONEDAS = {"CRC": ("colón", "colones", "₡"), "USD": ("dólar estadounidense", "dólares estadounidenses", "US$")}
RUBROS = ("mano_de_obra", "insumos", "gastos_administrativos", "utilidad")   # los cuatro de la fórmula de reajuste
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")


class OfertaError(ValueError):
    """Un dato de la oferta no sirve; el mensaje es el que ve la persona."""


# --- Monto en letras ------------------------------------------------------------------------------------------------

_UNIDADES = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
             "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno",
             "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
             "veintinueve")
_DECENAS = ("", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
_CENTENAS = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
             "ochocientos", "novecientos")


def _hasta_999(n: int) -> str:
    if n == 100:
        return "cien"
    centenas, resto = divmod(n, 100)
    partes = [_CENTENAS[centenas]] if centenas else []
    if resto:
        if resto < 30:
            partes.append(_UNIDADES[resto])
        else:
            decenas, unidad = divmod(resto, 10)
            partes.append(_DECENAS[decenas] + (f" y {_UNIDADES[unidad]}" if unidad else ""))
    return " ".join(partes)


def _apocope(texto: str) -> str:
    """«uno» → «un» y «veintiuno» → «veintiún» delante de un sustantivo (mil, millones, colones)."""
    if texto.endswith("veintiuno"):
        return texto[:-len("veintiuno")] + "veintiún"
    if texto == "uno" or texto.endswith(" uno"):
        return texto[:-3] + "un"
    return texto


def numero_en_letras(n: int) -> str:
    """El número entero en letras, en minúscula (hasta 999 999 999 999)."""
    if n < 0 or n > 999_999_999_999:
        raise OfertaError(f"El número {n} está fuera del rango que se escribe en letras.")
    if n == 0:
        return "cero"
    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    partes = []
    if millones:
        if millones == 1:
            partes.append("un millón")
        else:
            partes.append(_apocope(_miles(millones)) + " millones")
    if miles:
        partes.append("mil" if miles == 1 else _apocope(_hasta_999(miles)) + " mil")
    if unidades:
        partes.append(_hasta_999(unidades))
    return " ".join(partes)


def _miles(n: int) -> str:
    """Hasta 999 999 (los millones se cuentan con esto: «mil doscientos millones»)."""
    miles, unidades = divmod(n, 1000)
    partes = []
    if miles:
        partes.append("mil" if miles == 1 else _apocope(_hasta_999(miles)) + " mil")
    if unidades:
        partes.append(_hasta_999(unidades))
    return " ".join(partes)


def monto_en_letras(monto: Decimal, moneda: str) -> str:
    """Como en las ofertas: «Tres millones doscientos cuarenta y tres mil seiscientos colones exactos.» y, con
    céntimos, «… colones con 50/100.»"""
    if moneda not in MONEDAS:
        raise OfertaError(f"Moneda no conocida: {moneda!r} (CRC o USD).")
    monto = monto.quantize(CENTIMO, ROUND_HALF_UP)
    if monto < 0:
        raise OfertaError("El monto no puede ser negativo.")
    entero, centimos = int(monto), int((monto - int(monto)) * 100)
    singular, plural, _ = MONEDAS[moneda]
    if entero == 1:
        texto = f"un {singular}"
    else:
        letras = numero_en_letras(entero)
        if entero % 1_000_000 == 0 and entero >= 1_000_000:
            letras += " de"                       # «un millón de colones», «tres millones de colones»
        texto = f"{_apocope(letras)} {plural}"
    texto += f" con {centimos:02d}/100" if centimos else (" exacto" if entero == 1 else " exactos")
    return texto[0].upper() + texto[1:] + "."


# --- Datos de la oferta ----------------------------------------------------------------------------------------------

def decimal(valor, campo: str) -> Decimal:
    """Un monto o una cantidad como Decimal (nunca float); el error dice qué campo está mal."""
    if valor is None or not str(valor).strip():
        raise OfertaError(f"Falta {campo}.")
    try:
        d = Decimal(str(valor).replace(" ", "").replace(",", ""))
    except (InvalidOperation, ValueError):
        raise OfertaError(f"«{campo}» no es un número: {valor!r}.") from None
    if not d.is_finite():
        raise OfertaError(f"«{campo}» no es un número: {valor!r}.")
    return d


def formato(monto: Decimal, moneda: str) -> str:
    """₡3 243 600,00 al estilo costarricense: espacio de miles y coma decimal."""
    simbolo = MONEDAS[moneda][2]
    entero, dec = f"{monto.quantize(CENTIMO, ROUND_HALF_UP):,.2f}".split(".")
    return f"{simbolo}{entero.replace(',', ' ')},{dec}"


def formato_punto(monto: Decimal, moneda: str) -> str:
    """₡27.030,00: punto de miles y coma decimal, como la tabla de precios de la oferta de Tarrazú."""
    return formato(monto, moneda).replace(" ", ".")


def numero_corto(n: Decimal) -> str:
    """10 en vez de 10.00, y 12,5 con coma decimal (cantidades y porcentajes)."""
    texto = format(n.normalize(), "f")
    return texto.replace(".", ",")


@dataclass
class Linea:
    numero: str
    cantidad: Decimal
    descripcion: str
    precio_unitario: Decimal

    @property
    def monto(self) -> Decimal:
        return (self.cantidad * self.precio_unitario).quantize(CENTIMO, ROUND_HALF_UP)


@dataclass
class Rubro:
    clave: str
    nombre: str
    porcentaje: Decimal
    monto: Decimal = Decimal("0")


@dataclass
class Oferta:
    moneda: str
    lineas: list[Linea]
    meses: int | None                  # None: precio único; un número: arrendamiento o servicio mensual
    iva_tasa: Decimal | None           # None: exento
    iva_exento_motivo: str
    rubros: list[Rubro]
    datos: dict = field(default_factory=dict)   # carta, condiciones y firma, tal como vienen

    @property
    def subtotal_periodo(self) -> Decimal:
        """La suma de las líneas: por mes si es mensual, o el total si es precio único."""
        return sum((linea.monto for linea in self.lineas), Decimal("0"))

    @property
    def subtotal(self) -> Decimal:
        return self.subtotal_periodo * self.meses if self.meses else self.subtotal_periodo

    @property
    def iva(self) -> Decimal:
        if self.iva_tasa is None:
            return Decimal("0.00")
        return (self.subtotal * self.iva_tasa / CIEN).quantize(CENTIMO, ROUND_HALF_UP)

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.iva


def desglosar(base: Decimal, rubros: list[Rubro]) -> list[Rubro]:
    """Montos de cada rubro: base × porcentaje, redondeados al céntimo; el último absorbe la diferencia del redondeo
    para que la suma sea exactamente la base (el pliego exige montos y porcentajes concordantes)."""
    suma = sum((r.porcentaje for r in rubros), Decimal("0"))
    if suma != CIEN:
        raise OfertaError(f"Los porcentajes del desglose suman {suma} %; tienen que sumar 100 %.")
    acumulado = Decimal("0")
    for i, r in enumerate(rubros):
        if i == len(rubros) - 1:
            r.monto = base - acumulado
        else:
            r.monto = (base * r.porcentaje / CIEN).quantize(CENTIMO, ROUND_HALF_UP)
            acumulado += r.monto
    return rubros


def leer(datos: dict) -> Oferta:
    """Arma la oferta desde un diccionario (el YAML de la oferta) y revisa cada dato."""
    if not isinstance(datos, dict):
        raise OfertaError("El archivo de la oferta tiene que ser un diccionario (clave: valor).")
    moneda = str(datos.get("moneda", "CRC")).upper()
    if moneda not in MONEDAS:
        raise OfertaError(f"Moneda no conocida: {moneda!r} (CRC o USD). Una oferta usa una sola moneda.")
    crudas = datos.get("lineas") or []
    if not crudas:
        raise OfertaError("La oferta no tiene líneas de precio.")
    lineas = []
    for i, l in enumerate(crudas, 1):
        if not isinstance(l, dict) or not str(l.get("descripcion", "")).strip():
            raise OfertaError(f"La línea {i} necesita «descripcion», «cantidad» y «precio_unitario».")
        cantidad = decimal(l.get("cantidad"), f"la cantidad de la línea {i}")
        precio = decimal(l.get("precio_unitario"), f"el precio unitario de la línea {i}")
        if cantidad <= 0 or precio < 0:
            raise OfertaError(f"La línea {i}: la cantidad tiene que ser mayor que 0 y el precio no puede ser negativo.")
        lineas.append(Linea(str(l.get("numero", i)), cantidad, str(l["descripcion"]).strip(), precio))
    meses = datos.get("meses")
    if meses is not None:
        try:
            meses = int(meses)
        except (TypeError, ValueError):
            raise OfertaError("«meses» tiene que ser un número entero (o no ponerlo, si es precio único).") from None
        if not 1 <= meses <= 120:
            raise OfertaError("«meses» tiene que estar entre 1 y 120.")
    iva = datos.get("iva") or {}
    if not isinstance(iva, dict) or ("tasa" in iva) == ("exento" in iva):
        raise OfertaError("«iva» necesita «tasa» (por ejemplo 13) o «exento» con el motivo, una de las dos.")
    tasa = decimal(iva["tasa"], "tasa del IVA") if "tasa" in iva else None
    motivo = str(iva.get("exento") or "").strip()
    if tasa is None and not motivo:
        raise OfertaError("Si la oferta está exenta de IVA, «exento» tiene que decir por qué (el pliego pide desglosar "
                          "los tributos).")
    desglose = datos.get("desglose") or {}
    if set(desglose) != set(RUBROS):
        raise OfertaError("«desglose» necesita los cuatro rubros de la fórmula de reajuste: "
                          + ", ".join(RUBROS) + ".")
    rubros = []
    for clave in RUBROS:
        r = desglose[clave]
        if not isinstance(r, dict) or not str(r.get("nombre", "")).strip():
            raise OfertaError(f"El rubro «{clave}» necesita «nombre» y «porcentaje».")
        rubros.append(Rubro(clave, str(r["nombre"]).strip(), decimal(r.get("porcentaje"), f"porcentaje de {clave}")))
    oferta = Oferta(moneda, lineas, meses, tasa, motivo, rubros, datos)
    desglosar(oferta.subtotal, oferta.rubros)
    for requerido in ("procedimiento", "institucion", "objeto"):
        if not str(datos.get(requerido, "")).strip():
            raise OfertaError(f"Falta «{requerido}».")
    empresa = datos.get("empresa") or {}
    if not str(empresa.get("nombre", "")).strip() or not str(empresa.get("cedula_juridica", "")).strip():
        raise OfertaError("Falta la empresa: «empresa.nombre» y «empresa.cedula_juridica».")
    return oferta


# --- HTML y PDF ------------------------------------------------------------------------------------------------------

def fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def html(oferta: Oferta, hoy: date) -> str:
    entorno = Environment(loader=FileSystemLoader(PLANTILLAS), autoescape=select_autoescape(["html"]))
    logo = "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode("ascii") if LOGO.is_file() else ""
    d = oferta.datos
    fecha = d.get("fecha")
    fecha = fecha if isinstance(fecha, date) else (date.fromisoformat(str(fecha)) if fecha else hoy)
    return entorno.get_template("oferta_economica.html").render(
        o=oferta, d=d, logo=logo, fecha=fecha_larga(fecha), f=lambda m: formato(m, oferta.moneda),
        fp=lambda m: formato_punto(m, oferta.moneda), q=numero_corto,
        letras=monto_en_letras(oferta.total, oferta.moneda), MONEDA=MONEDAS[oferta.moneda])


def pdf(contenido_html: str, procedimiento: str, titulo: str = "Oferta económica", membrete: bool = True) -> bytes:
    """Imprime a PDF tamaño carta con el Chromium de Playwright, como el Reporte de cartel. Con membrete (la oferta
    económica y la oferta completa, app/propuesta.py), cada hoja lleva arriba a la izquierda el logo de Hermatix con
    su nombre, sin franjas ni pie. Sin membrete, un pie con su título y la página."""
    from playwright.sync_api import sync_playwright

    if membrete:
        cabecera = (f'<div style="width:100%;margin:0;padding:0 0 0 {MARGENES_MM["left"]}mm">'
                    f'<img src="{_imagen(MEMBRETE_LOGO)}" style="display:block;height:{ALTO_LOGO_MM}mm"></div>')
        pie = "<span></span>"
        margen = {lado: f"{mm}mm" for lado, mm in MARGENES_MM.items()}
    else:
        cabecera = "<span></span>"
        pie = ('<div style="width:100%;font-size:7.5pt;color:#5a6b7b;padding:0 14mm;display:flex;'
               'justify-content:space-between;font-family:Arial,sans-serif">'
               f'<span>{_escapar(titulo)} · Procedimiento {_escapar(procedimiento)}</span>'
               '<span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>')
        margen = {"top": "14mm", "bottom": "18mm", "left": "16mm", "right": "16mm"}
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page()
            pagina.set_content(contenido_html, wait_until="load")
            return pagina.pdf(format="Letter", print_background=True, display_header_footer=True,
                              header_template=cabecera, footer_template=pie, margin=margen)
        finally:
            navegador.close()


def _imagen(ruta: Path) -> str:
    """Una imagen como data URI: el encabezado y el pie de Chromium no cargan archivos."""
    return "data:image/png;base64," + base64.b64encode(ruta.read_bytes()).decode("ascii") if ruta.is_file() else ""


def _escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def guardar(contenido: bytes, carpeta: Path, procedimiento: str, momento, prefijo: str = "oferta_economica",
            extension: str = ".pdf") -> Path:
    """EXPORTS_DIR/ofertas/<procedimiento>/<prefijo>_<AAAAMMDD-HHMMSS>.pdf; nunca sobrescribe. La oferta completa del
    botón «Oferta» (app/propuesta.py) usa el prefijo «oferta»; su versión en Word, la extensión «.docx»."""
    seguro = "".join(c if c.isalnum() or c in "-_" else "_" for c in procedimiento)[:80] or "sin_procedimiento"
    destino = carpeta / "ofertas" / seguro
    destino.mkdir(parents=True, exist_ok=True)
    base, n = f"{prefijo}_{momento:%Y%m%d-%H%M%S}", 1
    ruta = destino / f"{base}{extension}"
    while ruta.exists():
        n += 1
        ruta = destino / f"{base}_{n}{extension}"
    ruta.write_bytes(contenido)
    return ruta


# --- Panel: valores iniciales, formulario y borrador -----------------------------------------------------------------

CONFIG = PROJECT_ROOT / "config" / "oferta.yaml"


def configuracion(ruta: Path = CONFIG) -> dict:
    """Los valores iniciales de Hermatix (config/oferta.yaml): empresa, lugar, condiciones y nombres del desglose."""
    import yaml
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    return datos if isinstance(datos, dict) else {}


def valores_iniciales(compra, tipo_procedimiento: str | None, config: dict | None = None) -> dict:
    """Una oferta nueva para el cartel: procedimiento, institución, objeto y líneas salen del cartel; la empresa y los
    textos generales, de config/oferta.yaml. Los precios y los porcentajes quedan vacíos: los escribe una persona."""
    config = configuracion() if config is None else config
    monedas = {linea.estimado.moneda for linea in compra.lineas if linea.estimado is not None}
    return {
        "procedimiento": compra.nro_procedimiento or "", "tipo_procedimiento": tipo_procedimiento or "",
        "institucion": compra.institucion or "", "destinatario": config.get("destinatario", ""),
        # SICOP a veces separa las palabras con espacios duros (\xa0): el título no se partía y se salía de la hoja.
        "objeto": (compra.descripcion or "").replace("\xa0", " "), "lugar": config.get("lugar", "San José"), "fecha": "",
        "partida": "1",
        "empresa": dict(config.get("empresa") or {}),
        "representante": {"nombre": "", "cargo": (config.get("representante") or {}).get("cargo", ""),
                          "calidades": "", "cedula": ""},
        "moneda": monedas.pop() if len(monedas) == 1 else "CRC", "meses": "",
        "lineas": [{"numero": linea.numero_linea, "cantidad": linea.cantidad,
                    "descripcion": linea.nombre_catalogo or "", "precio_unitario": ""} for linea in compra.lineas],
        "iva": {"tasa": "13"},
        "condiciones": dict(config.get("condiciones") or {}),
        "desglose": {clave: {"nombre": (config.get("desglose") or {}).get(clave, clave), "porcentaje": ""}
                     for clave in RUBROS},
    }


def desde_formulario(f) -> dict:
    """Los campos del formulario del panel (un MultiDict de Starlette) en el formato del YAML. Las filas de línea vacías
    se ignoran; lo demás lo revisa leer()."""
    def campo(nombre: str) -> str:
        return str(f.get(nombre) or "").strip()

    filas = zip(f.getlist("lin_numero"), f.getlist("lin_cantidad"), f.getlist("lin_descripcion"),
                f.getlist("lin_precio"))
    lineas = [{"numero": n.strip(), "cantidad": c.strip(), "descripcion": d.strip(), "precio_unitario": p.strip()}
              for n, c, d, p in filas if any(x.strip() for x in (c, d, p))]
    iva = {"tasa": campo("iva_tasa")} if campo("iva_modo") != "exento" else {"exento": campo("iva_exento")}
    return {
        "procedimiento": campo("procedimiento"), "tipo_procedimiento": campo("tipo_procedimiento"),
        "institucion": campo("institucion"), "destinatario": campo("destinatario"), "objeto": campo("objeto"),
        "lugar": campo("lugar"), "fecha": campo("fecha"), "partida": campo("partida"),
        "empresa": {"nombre": campo("empresa_nombre"), "cedula_juridica": campo("empresa_cedula")},
        "representante": {"nombre": campo("rep_nombre"), "cargo": campo("rep_cargo"),
                          "calidades": campo("rep_calidades"), "cedula": campo("rep_cedula")},
        "moneda": campo("moneda") or "CRC", "meses": campo("meses") or None, "lineas": lineas, "iva": iva,
        "condiciones": {"garantia": campo("cond_garantia"), "entrega": campo("cond_entrega"),
                        "forma_pago": campo("cond_forma_pago"), "validez": campo("cond_validez")},
        "desglose": {clave: {"nombre": campo(f"des_{clave}_nombre"), "porcentaje": campo(f"des_{clave}_pct")}
                     for clave in RUBROS},
    }


def borrador(conn, nro_sicop: str) -> tuple[dict, str, str] | None:
    """(datos, quién lo guardó, cuándo) del borrador del cartel, o None si no hay."""
    import json
    fila = conn.execute("SELECT datos_json, actualizado_por_nombre, actualizado_en FROM ofertas_borrador"
                        " WHERE nro_sicop = ?", (nro_sicop,)).fetchone()
    return (json.loads(fila[0]), fila[1], fila[2]) if fila else None


def guardar_borrador(conn, nro_sicop: str, datos: dict, quien, ahora) -> None:
    """Reemplaza el borrador del cartel y lo anota en el historial (sin montos: el detalle solo dice el cartel)."""
    import json

    from app import historial
    from app.database import transaccion
    with transaccion(conn):
        conn.execute(
            "INSERT INTO ofertas_borrador (nro_sicop, datos_json, actualizado_por, actualizado_por_nombre,"
            " actualizado_en) VALUES (?, ?, ?, ?, ?) ON CONFLICT (nro_sicop) DO UPDATE SET datos_json ="
            " excluded.datos_json, actualizado_por = excluded.actualizado_por, actualizado_por_nombre ="
            " excluded.actualizado_por_nombre, actualizado_en = excluded.actualizado_en",
            (nro_sicop, json.dumps(datos, ensure_ascii=False), quien.user_id, quien.nombre,
             ahora.isoformat(timespec="seconds")))
        historial.registrar(conn, quien, "guardar_oferta", nro_sicop)
