"""Genera los documentos SIMULADOS de tests/test_documentos.py (enriquecimiento, lección 3). Se corrió una vez:
    .venv\\Scripts\\python.exe tests\\fixtures\\documentos_simulados\\hacer_documentos.py
No son documentos de SICOP: los textos dicen «SIMULADO»."""

import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).parent
PAGINAS = ["SIMULADO Pliego de condiciones: alquiler de cámaras corporales",
           "SIMULADO Garantía de cumplimiento: 5 por ciento"]


def pdf_con_texto(paginas: list[str]) -> bytes:
    """PDF mínimo válido (con su tabla xref) con una línea de texto por página, en WinAnsi (tildes incluidas)."""
    objetos = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                                                           b"/Encoding /WinAnsiEncoding >>"}
    hijos = []
    for i, texto in enumerate(paginas):
        pagina, contenido = 4 + 2 * i, 5 + 2 * i
        literal = texto.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        flujo = b"BT /F1 14 Tf 72 720 Td (" + literal + b") Tj ET"
        objetos[contenido] = b"<< /Length %d >>\nstream\n" % len(flujo) + flujo + b"\nendstream"
        objetos[pagina] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R "
                           b">> >> /Contents %d 0 R >>" % contenido)
        hijos.append(b"%d 0 R" % pagina)
    objetos[2] = b"<< /Type /Pages /Kids [" + b" ".join(hijos) + b"] /Count %d >>" % len(paginas)
    salida = io.BytesIO()
    salida.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = {}
    for n in sorted(objetos):
        posiciones[n] = salida.tell()
        salida.write(b"%d 0 obj\n" % n + objetos[n] + b"\nendobj\n")
    xref = salida.tell()
    total = max(objetos) + 1
    salida.write(b"xref\n0 %d\n0000000000 65535 f \n" % total)
    for n in range(1, total):
        salida.write(b"%010d 00000 n \n" % posiciones[n])
    salida.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (total, xref))
    return salida.getvalue()


def pdf_escaneado() -> bytes:
    """Solo una imagen (como un pliego escaneado): no tiene texto que extraer."""
    imagen = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(imagen).text((20, 90), "SIMULADO escaneado", fill="black")
    salida = io.BytesIO()
    imagen.save(salida, format="PDF")
    return salida.getvalue()


def zip_con(archivos: dict[str, bytes]) -> bytes:
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in archivos.items():
            zf.writestr(nombre, datos)
    return salida.getvalue()


if __name__ == "__main__":
    texto = pdf_con_texto(PAGINAS)
    archivos = {
        "con_texto.pdf": texto,
        "escaneado.pdf": pdf_escaneado(),
        "falso.pdf": b"<html><body>SIMULADO: pagina de error, no es un PDF</body></html>\n",
        "pliego.zip": zip_con({"Especificaciones/pliego simulado.pdf": pdf_con_texto(["SIMULADO dentro del ZIP: "
                                                                                       "bodycam con GPS"]),
                               "leeme.txt": b"SIMULADO"}),
        "formulario.xlsx": zip_con({"[Content_Types].xml": b"<Types/>", "xl/workbook.xml": b"<workbook/>"}),
    }
    for nombre, datos in archivos.items():
        (AQUI / nombre).write_bytes(datos)
        print(f"{nombre}: {len(datos)} bytes")
