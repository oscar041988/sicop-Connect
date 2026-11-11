"""La oferta completa en Word (.docx): el mismo documento que el PDF del botón «Oferta», en otro formato (pedido de
Oscar, comunicado por Ivania, 2026-11-11; DECISION_IA.md §10.6 bis).

Sale de app/propuesta.preparar(), igual que el PDF, así que dice lo mismo y en el mismo orden:
1. portada (y el recuadro «BORRADOR» con lo pendiente, en rojo);
2. el pliego sección por sección, con «Respuesta Sección NN – Título»;
3. el listado de anexos;
4. el anexo 1.1, la oferta económica (carta, tabla de precios, monto en letras, condiciones, desglose, fórmula y
   firma), o la tabla con «PRECIO PENDIENTE»;
5. los documentos adjuntos: las imágenes tal cual y cada página de los PDF como imagen. El archivo original no se
   toca (solo se lee), y el PDF de la oferta sigue llevando el PDF original.

Membrete de Hermatix arriba y abajo de cada hoja, Times New Roman, tamaño carta: como el PDF. Lo escribe python-docx;
no hace falta Word instalado ni Chromium. Una persona lo revisa, lo firma y lo sube a SICOP.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

from app import oferta_economica as oe
from app.propuesta import GRUPOS, Preparada, titulo_es

AZUL = RGBColor(0x00, 0x30, 0x56)          # el --azul del PDF
ROJO = RGBColor(0xC0, 0x00, 0x00)
AZUL_HEX, ROJO_HEX = "003056", "C00000"
CARTA = (Mm(215.9), Mm(279.4))
MARGENES = {"top": Mm(37), "bottom": Mm(26), "left": Mm(25), "right": Mm(26)}   # los del PDF con membrete
ANCHO_UTIL = Mm(215.9 - 25 - 26)
ALTO_UTIL = Mm(279.4 - 37 - 26 - 12)       # un poco menos: el título del anexo comparte la primera hoja
DPI_ADJUNTOS = 130                         # páginas de los PDF adjuntos: legibles sin hacer el .docx enorme
# Caracteres que no caben en un .docx (XML): el texto de algunos PDF los trae.
_NO_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
SIGLA = {"mano_de_obra": "MO", "insumos": "I", "gastos_administrativos": "GA", "utilidad": "U"}


def _limpio(texto) -> str:
    return _NO_XML.sub("", str(texto or ""))


# --- Ayudas de formato ---------------------------------------------------------------------------------------------

def _parrafo(doc, texto: str = "", *, negrita=False, cursiva=False, color=None, tam=None, alinear=None,
             antes=0, despues=6, subrayado=False):
    p = doc.add_paragraph()
    if texto:
        _run(p, texto, negrita=negrita, cursiva=cursiva, color=color, tam=tam, subrayado=subrayado)
    p.paragraph_format.space_before = Pt(antes)
    p.paragraph_format.space_after = Pt(despues)
    if alinear is not None:
        p.alignment = alinear
    return p


def _run(p, texto: str, *, negrita=False, cursiva=False, color=None, tam=None, subrayado=False):
    r = p.add_run(_limpio(texto))
    r.bold, r.italic, r.underline = negrita or None, cursiva or None, subrayado or None
    if color is not None:
        r.font.color.rgb = color
    if tam is not None:
        r.font.size = Pt(tam)
    return r


def _salto(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def _borde(p, lados: tuple[str, ...], color_hex: str, grosor: int = 12) -> None:
    """Borde de párrafo (grosor en octavos de punto), como el recuadro rojo del PDF."""
    ppr = p._p.get_or_add_pPr()
    bordes = OxmlElement("w:pBdr")
    for lado in lados:
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(grosor))
        b.set(qn("w:space"), "4")
        b.set(qn("w:color"), color_hex)
        bordes.append(b)
    ppr.append(bordes)


def _fondo(celda, color_hex: str) -> None:
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:color"), "auto")
    sombra.set(qn("w:fill"), color_hex)
    celda._tc.get_or_add_tcPr().append(sombra)


def _celda(celda, texto: str, *, negrita=False, color=None, fondo=None, alinear=WD_ALIGN_PARAGRAPH.LEFT,
           extra: str | None = None, extra_color=None) -> None:
    """Escribe en una celda (reemplaza su párrafo vacío). extra va en otra línea (p. ej. «PENDIENTE: …»)."""
    p = celda.paragraphs[0]
    p.alignment = alinear
    p.paragraph_format.space_after = Pt(0)
    _run(p, texto, negrita=negrita, color=color)
    if extra:
        p.add_run().add_break()
        _run(p, extra, negrita=True, color=extra_color)
    if fondo:
        _fondo(celda, fondo)


def _tabla(doc, filas: int, columnas: int, anchos_mm: list[float] | None = None):
    t = doc.add_table(rows=filas, cols=columnas)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if anchos_mm:
        for fila in t.rows:
            for celda, ancho in zip(fila.cells, anchos_mm):
                celda.width = Mm(ancho)
    return t


def _imagen(doc, contenido: bytes, ancho_px: int, alto_px: int) -> None:
    """La imagen tan grande como quepa en la hoja, sin deformarla."""
    ancho, alto = ANCHO_UTIL, int(ANCHO_UTIL * alto_px / max(ancho_px, 1))
    if alto > ALTO_UTIL:
        ancho, alto = int(ALTO_UTIL * ancho_px / max(alto_px, 1)), ALTO_UTIL
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(io.BytesIO(contenido), width=ancho, height=alto)


# --- Documento -----------------------------------------------------------------------------------------------------

def _preparar_documento() -> Document:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(11)
    seccion = doc.sections[0]
    seccion.page_width, seccion.page_height = CARTA
    seccion.top_margin, seccion.bottom_margin = MARGENES["top"], MARGENES["bottom"]
    seccion.left_margin, seccion.right_margin = MARGENES["left"], MARGENES["right"]
    seccion.header_distance, seccion.footer_distance = Mm(8), Mm(6)
    # Membrete de Hermatix en cada hoja, como el PDF (las mismas imágenes).
    for parte, ruta in ((seccion.header, oe.CABECERA), (seccion.footer, oe.PIE)):
        if Path(ruta).is_file():
            p = parte.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(ruta), width=ANCHO_UTIL)
    return doc


def _portada(doc, p: Preparada) -> None:
    d, c = p.datos, p.compra
    centro = WD_ALIGN_PARAGRAPH.CENTER
    _parrafo(doc, (getattr(c, "institucion", None) or d.get("institucion") or "").upper(), negrita=True, color=AZUL,
             tam=13, alinear=centro, antes=24, despues=30)
    _parrafo(doc, "OFERTA", negrita=True, color=AZUL, tam=16, alinear=centro)
    _parrafo(doc, f"{(d.get('tipo_procedimiento') or 'Procedimiento de contratación').upper()},", negrita=True,
             color=AZUL, tam=15, alinear=centro)
    _parrafo(doc, d.get("procedimiento") or "", negrita=True, cursiva=True, color=AZUL, tam=14, alinear=centro,
             despues=34)
    _parrafo(doc, (d.get("objeto") or "").upper(), negrita=True, color=AZUL, tam=12.5, alinear=centro, despues=40)
    empresa = d.get("empresa") or {}
    for texto in ("Oferente", empresa.get("nombre", ""), f"Cédula Jurídica {empresa.get('cedula_juridica', '')}"):
        _parrafo(doc, texto, negrita=True, color=AZUL, tam=14, alinear=centro)
    if p.pendientes:
        caja = _parrafo(doc, f"BORRADOR: hay {len(p.pendientes)} punto(s) sin resolver. No firmar ni subir a SICOP "
                             "todavía.", negrita=True, color=ROJO, tam=12, antes=26, despues=4)
        _borde(caja, ("top", "left", "right"), ROJO_HEX)
        for i, pendiente in enumerate(p.pendientes):
            linea = _parrafo(doc, f"• {pendiente}", color=ROJO, tam=10, despues=0)
            _borde(linea, ("left", "right", "bottom") if i == len(p.pendientes) - 1 else ("left", "right"), ROJO_HEX)


def _pliego(doc, p: Preparada) -> None:
    n = 0
    for b in p.bloques:
        if b.titulo or b.numero:
            _parrafo(doc, f"{b.numero + '. ' if b.numero else ''}{b.titulo}", negrita=True, color=AZUL, tam=11.5,
                     subrayado=True, antes=14, despues=6).paragraph_format.keep_with_next = True
        # El texto del pliego tal cual: un párrafo por cada trozo separado por una línea en blanco, con sus saltos.
        for trozo in re.split(r"\n\s*\n", _limpio(b.texto).strip()):
            if not trozo.strip():
                continue
            par = _parrafo(doc, despues=6)
            for i, linea in enumerate(trozo.split("\n")):
                if i:
                    par.add_run().add_break()
                par.add_run(linea)
        if b.respuesta is not None:
            n += 1
            titulo = f" – {titulo_es(b.titulo)}" if b.titulo else ""
            color = ROJO if b.pendiente else AZUL
            r = _parrafo(doc, f"Respuesta Sección {n:02d}{titulo}", negrita=True, cursiva=not b.pendiente,
                         color=color, antes=6, despues=10)
            for linea in b.respuesta:
                r.add_run().add_break()
                _run(r, linea, cursiva=not b.pendiente, color=color)
            if b.pendiente:
                _borde(r, ("left",), ROJO_HEX, grosor=18)


def _listado(doc, p: Preparada) -> None:
    _parrafo(doc, "Listado de Anexos:", negrita=True, color=AZUL, tam=14, despues=14)
    filas = [(f"1. {GRUPOS[1]}", "Anexo 1.1", "Oferta Económica y Desglose del Precio",
              f"PRECIO PENDIENTE: {p.precio_pendiente}." if p.precio_pendiente else None)]
    for grupo in (2, 3, 4):
        del_grupo = [a for a in p.anexos if a.grupo == grupo]
        for i, a in enumerate(del_grupo):
            filas.append((f"{grupo}. {GRUPOS[grupo]}" if i == 0 else "", f"Anexo {a.numero}", a.titulo,
                          f"PENDIENTE: {a.pendiente}." if a.pendiente else None))
    t = _tabla(doc, len(filas) + 1, 3, [55, 30, 80])
    for celda, texto in zip(t.rows[0].cells, ("Sección", "No. Anexo", "Documento")):
        _celda(celda, texto, negrita=True, color=RGBColor(0xFF, 0xFF, 0xFF), fondo=AZUL_HEX)
    for fila, (seccion, numero, documento, falta) in zip(t.rows[1:], filas):
        _celda(fila.cells[0], seccion)
        _celda(fila.cells[1], numero)
        _celda(fila.cells[2], documento, extra=falta, extra_color=ROJO)


def _titulo_anexo(doc, texto: str) -> None:
    _salto(doc)
    _parrafo(doc, texto, negrita=True, color=AZUL, tam=13, despues=12)


# --- Anexo 1.1: la oferta económica (diseño de Tarrazú, como app/web/templates/oferta_economica.html) -----------

def _economica(doc, p: Preparada) -> None:
    o = p.oferta
    d = o.datos
    r = d.get("representante") or {}
    empresa = d.get("empresa") or {}
    tipo = d.get("tipo_procedimiento") or "Procedimiento de contratación"
    objeto = (d.get("objeto") or "").upper()
    fecha = oe.fecha_larga(p.hoy)
    centro, derecha = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT
    fp = lambda m: oe.formato_punto(m, o.moneda)                       # noqa: E731
    simbolo = oe.MONEDAS[o.moneda][2]
    sin_simbolo = lambda m: oe.formato(m, o.moneda)[len(simbolo):]     # noqa: E731

    # Carta
    _parrafo(doc, f"{d.get('lugar') or 'San José'}, {fecha}.", negrita=True, alinear=derecha, antes=10, despues=30)
    for i, texto in enumerate(("Señores", d.get("institucion") or "",
                               d.get("destinatario") or "Proveeduría Institucional")):
        _parrafo(doc, texto, negrita=True, despues=30 if i == 2 else 0)
    for i, texto in enumerate((tipo, f"“{objeto}”", f"Procedimiento N° {d.get('procedimiento') or ''}")):
        _parrafo(doc, texto, negrita=True, alinear=centro, despues=26 if i == 2 else 0)
    _parrafo(doc, "Estimados Señores:", despues=26)
    nombre = r.get("nombre") or "[nombre del representante legal]"
    cuerpo = _parrafo(doc, alinear=WD_ALIGN_PARAGRAPH.JUSTIFY, despues=12)
    cuerpo.paragraph_format.line_spacing = 1.5
    _run(cuerpo, f"Quien suscribe, {nombre}"
                 f"{', ' + r['calidades'] if r.get('calidades') else ''}"
                 f"{', cédula de identidad ' + r['cedula'] if r.get('cedula') else ''}; en mi condición de "
                 f"{r.get('cargo') or 'representante legal'} de la empresa {empresa.get('nombre', '')}, una sociedad "
                 "inscrita y vigente de acuerdo con las Leyes de la República de Costa Rica, con Cédula Jurídica Número "
                 f"{empresa.get('cedula_juridica', '')}, presento nuestra ")
    _run(cuerpo, "OFERTA ECONÓMICA", negrita=True)
    _run(cuerpo, f" por nuestra participación en la {tipo}, Procedimiento ")
    _run(cuerpo, f"N° {d.get('procedimiento') or ''},", negrita=True)
    _run(cuerpo, " denominada ")
    _run(cuerpo, f"“{objeto}”.", negrita=True)
    if d.get("declaracion_registro", True):
        declaracion = _parrafo(doc, "Manifiesto que la información contenida en las declaraciones incorporadas en el "
                                    "Registro Electrónico Oficial de Proveedores y Subcontratistas se encuentra "
                                    "invariable, de conformidad al artículo 29 de la LGCP.",
                               alinear=WD_ALIGN_PARAGRAPH.JUSTIFY, despues=12)
        declaracion.paragraph_format.line_spacing = 1.5

    # Tabla de precios
    _salto(doc)
    for i, texto in enumerate(("Oferta Económica", objeto, f"Procedimiento N° {d.get('procedimiento') or ''}")):
        _parrafo(doc, texto, negrita=True, tam=14 if i == 0 else None, alinear=centro, despues=30 if i == 2 else 0)
    if d.get("partida"):
        _parrafo(doc, f"Partida {d['partida']}", negrita=True, subrayado=True, despues=20)
    if o.meses == 12:
        periodo = " anual"
    elif o.meses:
        periodo = f" por {o.meses} {'mes' if o.meses == 1 else 'meses'}"
    else:
        periodo = ""
    blanco = RGBColor(0xFF, 0xFF, 0xFF)
    t = _tabla(doc, len(o.lineas) + 6, 5, [15, 20, 66, 30, 34])   # encabezado, líneas, 3 totales, última, letras
    for celda, texto in zip(t.rows[0].cells, ("Línea", "Cantidad", "Descripción", "Precio", "Precio")):
        _celda(celda, texto, negrita=True, color=blanco, fondo=AZUL_HEX, alinear=centro)
    for fila, linea in zip(t.rows[1:], o.lineas):
        _celda(fila.cells[0], linea.numero, alinear=centro)
        _celda(fila.cells[1], oe.numero_corto(linea.cantidad), alinear=centro)
        _celda(fila.cells[2], linea.descripcion.upper(), alinear=centro)
        _celda(fila.cells[3], fp(linea.precio_unitario), alinear=centro, extra="Por unidad")
        _celda(fila.cells[4], fp(linea.monto), alinear=centro, extra="Mensual" if o.meses else "Total")
    iva = (("Total, IVA", "Exento") if o.iva_tasa is None
           else (f"Total, IVA ({oe.numero_corto(o.iva_tasa)} %)", fp(o.iva)))
    totales = [(f"Sub Total{periodo}", fp(o.subtotal)), iva, (f"Total{periodo}", fp(o.total))]
    base = len(o.lineas) + 1
    for i, (etiqueta, valor) in enumerate(totales):
        fila = t.rows[base + i]
        fila.cells[0].merge(fila.cells[2])
        _celda(fila.cells[3], etiqueta, color=blanco, fondo=AZUL_HEX, alinear=centro)
        _celda(fila.cells[4], valor, negrita=valor == "Exento", alinear=centro)
    ultima = t.rows[base + 3]
    ultima.cells[0].merge(ultima.cells[1])
    _celda(ultima.cells[2], "*****Última Línea********", alinear=centro)
    letras = t.rows[base + 4]
    letras.cells[0].merge(letras.cells[4])
    _celda(letras.cells[0], "Monto en Letras", negrita=True,
           extra=oe.monto_en_letras(o.total, o.moneda))
    if o.iva_tasa is None and o.iva_exento_motivo:
        _parrafo(doc, f"IVA exento: {o.iva_exento_motivo}.", antes=8)

    # Condiciones generales y desglose
    _salto(doc)
    _parrafo(doc, "Condiciones Generales de la Oferta", negrita=True, tam=14, alinear=centro, despues=22)
    cond = d.get("condiciones") or {}
    pares = [(nombre_c, cond.get(clave)) for clave, nombre_c in (("garantia", "Garantía"),
                                                                 ("entrega", "Tiempo de Entrega"),
                                                                 ("forma_pago", "Forma de Pago"),
                                                                 ("validez", "Validez de la Oferta"))]
    pares += [(otra.get("nombre", ""), otra.get("texto", "")) for otra in cond.get("otras") or []]
    for nombre_c, texto in pares:
        if texto:
            par = _parrafo(doc, despues=2)
            _run(par, nombre_c, negrita=True)
            _run(par, f": {texto}")
    _parrafo(doc, "**Aceptamos el pliego de condiciones y por lo tanto cumplimos con lo establecido**", negrita=True,
             antes=18, despues=30)
    nota = _parrafo(doc, despues=30)
    _run(nota, "Nota:", negrita=True, color=RGBColor(0xE0, 0x00, 0x00), subrayado=True)
    _run(nota, " El precio de nuestra oferta es en firme, definitivo y en plaza.", subrayado=True)
    _parrafo(doc, "DESGLOSE DE PRECIO", negrita=True, tam=14, alinear=centro, despues=18)
    _parrafo(doc, f"Estructura de Costos – Monto Total {fp(o.subtotal)}", negrita=True, despues=12)
    t = _tabla(doc, len(o.rubros) + 2, 3, [90, 30, 40])
    for celda, texto in zip(t.rows[0].cells, ("Rubro", "Porcentaje", f"Monto ({simbolo})")):
        _celda(celda, texto, negrita=True)
    filas = [(rb.nombre, f"{oe.numero_corto(rb.porcentaje)} %", sin_simbolo(rb.monto)) for rb in o.rubros]
    filas.append(("Total", "100 %", sin_simbolo(o.subtotal)))
    for fila, valores in zip(t.rows[1:], filas):
        for celda, texto in zip(fila.cells, valores):
            _celda(celda, texto, negrita=True)

    # Fórmula de reajuste y firma
    _salto(doc)
    _parrafo(doc, "Fórmula Matemática", negrita=True, tam=14, despues=14)
    _parrafo(doc, "PV = PC { MO ( iMOtm / IMOtc ) + I ( iIti / iItc ) + GA ( iGAtg / iGAtc ) + U }", tam=13,
             despues=18)
    _parrafo(doc, "DONDE:", negrita=True, despues=10)
    definiciones = [("PV", "Precio Variado"), ("PC", "Precio cotización")]
    definiciones += [(SIGLA[rb.clave], f"Porcentaje de {rb.nombre.lower()} del precio de cotización "
                                       f"({oe.numero_corto(rb.porcentaje)} %).") for rb in o.rubros]
    definiciones += [
        ("iMOtm", "Índice del costo de la mano de obra en el momento considerado para la variación."),
        ("iMOtc", "Índice del costo de la mano de obra en el momento de la cotización."),
        ("iITi", "Índice del costo de los insumos en el momento considerado para la variación."),
        ("iItc", "Índice del costo de insumos en el momento de la cotización."),
        ("iGAtg", "Índice de costo de gastos administrativos en el momento de la variación."),
        ("iGAtc", "Índice de costo de gastos administrativos en el momento de la cotización."),
    ]
    for sigla, texto in definiciones:
        par = _parrafo(doc, despues=0)
        _run(par, f"{sigla}\t", negrita=True)
        _run(par, f"= {texto}")
    firma = [r.get("nombre") or "[nombre del representante legal]", r.get("cargo_firma") or "Representante Legal",
             empresa.get("nombre", "")]
    if r.get("cedula"):
        firma.append(f"Cédula de identidad: {r['cedula']}")
    firma.append(f"Cédula jurídica: {empresa.get('cedula_juridica', '')}")
    _parrafo(doc, "______________________________", alinear=centro, antes=70, despues=0)
    for texto in firma:
        _parrafo(doc, texto, alinear=centro, despues=0)


def _precio_pendiente(doc, p: Preparada) -> None:
    _parrafo(doc, f"PRECIO PENDIENTE: {p.precio_pendiente}. La app no inventa precios: Oscar los aprueba en "
                  "config/tarifario.yaml.", negrita=True, color=ROJO, despues=12)
    lineas = p.datos.get("lineas") or []
    t = _tabla(doc, len(lineas) + 1, 4, [20, 25, 85, 35])
    blanco = RGBColor(0xFF, 0xFF, 0xFF)
    for celda, texto in zip(t.rows[0].cells, ("Línea", "Cantidad", "Descripción", "Precio unitario")):
        _celda(celda, texto, negrita=True, color=blanco, fondo=AZUL_HEX, alinear=WD_ALIGN_PARAGRAPH.CENTER)
    for fila, linea in zip(t.rows[1:], lineas):
        _celda(fila.cells[0], str(linea.get("numero", "")), alinear=WD_ALIGN_PARAGRAPH.CENTER)
        _celda(fila.cells[1], str(linea.get("cantidad", "")), alinear=WD_ALIGN_PARAGRAPH.CENTER)
        _celda(fila.cells[2], str(linea.get("descripcion", "")).upper(), alinear=WD_ALIGN_PARAGRAPH.CENTER)
        _celda(fila.cells[3], "PENDIENTE", negrita=True, color=ROJO, alinear=WD_ALIGN_PARAGRAPH.CENTER)


# --- Documentos adjuntos -------------------------------------------------------------------------------------------

def _paginas_pdf(ruta: Path) -> list[tuple[bytes, int, int]]:
    """Cada página del PDF como JPEG (bytes, ancho, alto). Solo lee el archivo: el original no cambia."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(ruta)
    try:
        imagenes = []
        for i in range(len(doc)):
            imagen = doc[i].render(scale=DPI_ADJUNTOS / 72).to_pil().convert("RGB")
            salida = io.BytesIO()
            imagen.save(salida, format="JPEG", quality=82)
            imagenes.append((salida.getvalue(), imagen.width, imagen.height))
        return imagenes
    finally:
        doc.close()


def _adjunto(doc, ruta: Path, extension: str) -> None:
    if extension == ".pdf":
        for i, (contenido, ancho, alto) in enumerate(_paginas_pdf(ruta)):
            if i:
                _salto(doc)
            _imagen(doc, contenido, ancho, alto)
        return
    from PIL import Image
    with Image.open(ruta) as imagen:
        ancho, alto = imagen.size
    _imagen(doc, ruta.read_bytes(), ancho, alto)


def documento(p: Preparada) -> bytes:
    """La oferta completa en .docx, en el orden del PDF."""
    doc = _preparar_documento()
    _portada(doc, p)
    _salto(doc)
    _pliego(doc, p)
    _salto(doc)
    _listado(doc, p)
    _titulo_anexo(doc, "Anexo 1.1: Oferta Económica y Desglose del Precio")
    if p.oferta is not None:
        _economica(doc, p)
    else:
        _precio_pendiente(doc, p)
    for a in p.presentes:
        _titulo_anexo(doc, f"Anexo {a.numero}: {a.titulo}")
        _adjunto(doc, a.ruta, a.extension)
    salida = io.BytesIO()
    doc.save(salida)
    return salida.getvalue()
