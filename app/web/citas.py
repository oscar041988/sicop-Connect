"""Citas del resumen con IA como enlaces (Reporte con IA, lección 5): [DOC 1 · pág. 3] abre ese documento en esa página.

* DOC n se busca con expediente.numeracion, la misma que usó el expediente que leyó el modelo. Solo se enlaza si el
  expediente actual es el mismo del resumen (misma huella): si llegaron documentos nuevos, la numeración pudo cambiar
  y un enlace llevaría al documento equivocado; ahí la cita queda como texto.
* PDF: se abre con «Ver» en la página citada (#page=N, lo entienden los visores de PDF de los navegadores).
  ZIP, Excel o imagen: «Ver» sin página. Word: «Descargar». Un documento no guardado, o un DOC que no existe: texto.
* Todo el texto se escapa; solo el enlace lo arma la app.
"""

from __future__ import annotations

import re

from markupsafe import Markup, escape

from app.fichas_panel import Documento

CITA = re.compile(r"\[DOC (\d+)([^\]]*)\]")
PAGINA = re.compile(r"pág\.\s*(\d+)")


def _enlace(nro_sicop: str, doc: Documento, pagina: str | None) -> str | None:
    base = f"/oportunidades/{nro_sicop}/documentos/{doc.id}"
    if doc.estado != "guardado":
        return None
    if doc.vista == "pdf":
        return f"{base}/ver" + (f"#page={pagina}" if pagina else "")
    return f"{base}/ver" if doc.vista else base


def enlazar(texto: str, nro_sicop: str, docs: dict[int, Documento] | None) -> Markup:
    """El texto de una cita con cada [DOC n · …] convertido en enlace (si se puede). docs None: sin enlaces."""
    if docs is None:
        return escape(texto)
    partes, inicio = [], 0
    for m in CITA.finditer(texto):
        partes.append(escape(texto[inicio:m.start()]))
        doc = docs.get(int(m.group(1)))
        pagina = PAGINA.search(m.group(2))
        destino = _enlace(nro_sicop, doc, pagina.group(1) if pagina else None) if doc else None
        if destino is None:
            partes.append(escape(m.group(0)))
        else:
            titulo = f"{doc.archivo or doc.nombre or 'Documento'}" + (f", página {pagina.group(1)}" if pagina else "")
            partes.append(Markup('<a href="{}" target="_blank" rel="noopener" title="{}">{}</a>').format(
                destino, titulo, m.group(0)))
        inicio = m.end()
    partes.append(escape(texto[inicio:]))
    return Markup("").join(partes)
