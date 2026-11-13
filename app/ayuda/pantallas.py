"""De un marcador de captura a «qué página abrir» y «qué elemento resaltar».

Regla automática: «resaltar «X»» busca en la página el elemento visible cuyo texto es X (primero exacto, luego
«empieza con X»); «resaltar «X» en el menú» busca solo en el menú de arriba. Si el elemento está dentro de un
desplegable cerrado («Más filtros», «Cambiar», «Administración»…), se abre antes.

ESPECIALES es solo para lo que esa regla no resuelve: objetivos sin «» («la prioridad», «una tarjeta»),
textos repetidos («Ver» del resumen y «Ver» de un documento) o pasos que necesitan otro cartel u otra acción antes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ayuda.misiones import Marcador

# Pantalla → dirección. {principal}, {seguido}, {sin_encargado}, {consulta}, {perfil} y {constancia} salen de
# claves.json.
PANTALLAS: dict[str, str] = {
    "Iniciar sesión": "/login",
    "Panel de carteles": "/oportunidades",
    "Cartel": "/oportunidades/{principal}",
    "Resumen": "/oportunidades/{principal}/resumen",
    "Seguimiento": "/seguimiento",
    "Expediente": "/seguimiento/{seguido}",
    "Competencia": "/competencia",
    "Cargar archivo": "/cargar",
    "Usuarios": "/usuarios",
    "Destinatarios": "/destinatarios",
    "Avisos": "/avisos",
    "Calidad de reglas": "/calidad",
    "Bitácora": "/bitacora",
    "Grabación": "/bitacora/consultas/{consulta}",
    "Correo": "/ayuda-ejemplo/correo",
    "Perfil": "/perfil",
    "Elemento del perfil": "/perfil/{perfil}",
    "Asistente": "/oportunidades/{seguido}/asistente",   # su propia página (12/11), con el asistente empezado
    "Revisión rápida": "/oportunidades/{sin_encargado}/asistente",   # sin ampliar, excluyentes respondidos
    "Resultado": "/oportunidades/{seguido}/asistente",   # el mismo cartel, con un resultado ya calculado
    "Constancia": "/oportunidades/{seguido}/asistente/resultados/{constancia}",
}
SIN_SESION = {"Iniciar sesión"}
MENU = "header nav"


@dataclass(frozen=True)
class Objetivo:
    """Cómo encontrar el elemento: por texto (texto) o por selector CSS (selector, con un filtro opcional por
    contenido: entre varios, el de texto más corto, o sea el más interno). antes: acciones previas, en orden:
    ("click", css) · ("elegir", css, valor) · ("subir", css, "subida") · ("ir", url)."""
    texto: str | None = None
    selector: str | None = None
    contiene: str | None = None
    en_menu: bool = False
    url: str | None = None
    antes: tuple[tuple[str, ...], ...] = ()

    def describir(self) -> str:
        if self.texto:
            return f"«{self.texto}»" + (" en el menú" if self.en_menu else "")
        return f"el elemento «{self.selector}»" + (f" con «{self.contiene}»" if self.contiene else "")


_SUBIR = (("elegir", "select[name=reporte]", "carteles"), ("elegir", "select[name=origen]", "sintetico"),
          ("subir", "input[name=archivo]", "subida"), ("click", "form[action='/cargar'] button[type=submit]"))

ESPECIALES: dict[tuple[str, str], Objetivo] = {
    # Panel de carteles
    ("Panel de carteles", "el buscador"): Objetivo(selector="input[type=search]"),
    ("Panel de carteles", "el menú"): Objetivo(selector=MENU),
    ("Panel de carteles", "el número de resultados"): Objetivo(selector=".resultados .sub"),
    ("Panel de carteles", "el título de un cartel"): Objetivo(selector=".card h3 a"),
    ("Panel de carteles", "la etiqueta «Nuevo»"): Objetivo(selector=".tag.new"),
    ("Panel de carteles", "la familia"): Objetivo(selector=".card .tags .tag:not(.new):not(.w):not(.g):not(.r)"),
    ("Panel de carteles", "la fila de botones"): Objetivo(selector=".tools"),
    ("Panel de carteles", "la prioridad"): Objetivo(selector=".card .score"),
    ("Panel de carteles", "los cuadros de «Más filtros»"): Objetivo(selector="form.filtros"),
    ("Panel de carteles", "«Exportar a Excel»"): Objetivo(selector="a.exportar"),
    # Cartel (el principal: Alta, sin revisar, sin seguimiento, con ficha, documentos y resumen)
    # Franja de arriba (rediseño del 2026-11-06, misiones 04 y 09)
    ("Cartel", "la institución"): Objetivo(selector=".cf-institucion"),
    ("Cartel", "las etiquetas"): Objetivo(selector=".cf-arriba .ct-chips"),
    ("Cartel", "el título"): Objetivo(selector="h1.cf-titulo"),
    ("Cartel", "«¿Podemos participar?»"): Objetivo(selector=".cf-participar"),
    ("Cartel", "las cuatro cifras"): Objetivo(selector="dl.cf-cifras"),
    ("Cartel", "las etiquetas de seguimiento"): Objetivo(selector=".cf-arriba .ct-chips", url="/oportunidades/{seguido}"),
    # Pestañas «Condiciones» y «Documentos» (misión 06): la dirección abre la pestaña con ?paso=
    ("Cartel", "la pestaña «Condiciones»"): Objetivo(selector='a.paso-pill[data-paso="condiciones"]'),
    ("Cartel", "el estado del concurso"): Objetivo(selector="#paso-condiciones > p.sub",
                                                   url="/oportunidades/{principal}?paso=condiciones"),
    ("Cartel", "el aviso del cierre"): Objetivo(selector="#paso-condiciones p.aviso",
                                                url="/oportunidades/{principal}?paso=condiciones"),
    ("Cartel", "la fila «Garantías»"): Objetivo(selector=".tarjetas-cartel.condiciones article", contiene="Garantías",
                                                   url="/oportunidades/{principal}?paso=condiciones"),
    ("Cartel", "las fechas de SICOP"): Objetivo(selector="#paso-condiciones dl.datos",
                                                url="/oportunidades/{principal}?paso=condiciones"),
    ("Cartel", "la pestaña «Documentos»"): Objetivo(selector='a.paso-pill[data-paso="evidencia"]'),
    ("Cartel", "un documento"): Objetivo(selector=".documentos-cartel li",
                                         url="/oportunidades/{principal}?paso=evidencia"),
    ("Cartel", "«Abrir» de un documento"): Objetivo(selector=".documentos-cartel a.btn.p",
                                                    url="/oportunidades/{principal}?paso=evidencia"),
    ("Cartel", "«Descargar» de un documento"): Objetivo(selector=".documentos-cartel a.btn.o",
                                                        url="/oportunidades/{principal}?paso=evidencia"),
    ("Cartel", "«Historial»"): Objetivo(texto="Historial", url="/oportunidades/{seguido}"),
    ("Cartel", "«Ver» del resumen"): Objetivo(selector="#resumen-ia a.btn.p"),
    ("Cartel", "«Resumen ejecutivo»"): Objetivo(selector="#resumen-ia h2"),
    # Resumen
    ("Resumen", "la columna «Excluyente»"): Objetivo(texto="Excluyente"),
    ("Resumen", "una cita"): Objetivo(selector=".cita"),
    # Seguimiento y expediente
    ("Seguimiento", "una tarjeta"): Objetivo(selector=".rejilla-seguimiento .tarjeta"),
    ("Seguimiento", "«Sin encargado»"): Objetivo(selector=".rejilla-seguimiento .tag.w"),
    ("Seguimiento", "«Solo los míos»"): Objetivo(selector="a.chip[href='/seguimiento?mios=1']"),
    ("Expediente", "la etiqueta «En seguimiento»"): Objetivo(selector=".op-etiquetas .en-seguimiento"),
    ("Expediente", "«Asignar el encargado»"): Objetivo(texto="Asignar el encargado",
                                                      url="/seguimiento/{sin_encargado}"),
    ("Expediente", "«Guardar»"): Objetivo(selector="form[action$='/encargado'] button",
                                         url="/seguimiento/{sin_encargado}"),
    ("Expediente", "«Encargado»"): Objetivo(selector="h2", contiene="Encargado"),
    # Competencia
    ("Competencia", "una tarjeta"): Objetivo(selector="article.familia-comp"),
    ("Competencia", "un número de «Veces»"): Objetivo(selector="a.veces"),
    ("Competencia", "«Ver los … ganadores»"): Objetivo(selector="article.familia-comp summary", contiene="ganadores"),
    # Cargar archivo
    ("Cargar archivo", "el botón para elegir el archivo"): Objetivo(selector="input[type=file]"),
    ("Cargar archivo", "«Resumen de la importación»"): Objetivo(texto="Resumen de la importación", antes=_SUBIR),
    ("Cargar archivo", "«Evaluación»"): Objetivo(texto="Evaluación", antes=_SUBIR),
    # Usuarios, destinatarios, avisos
    ("Usuarios", "una tarjeta"): Objetivo(selector=".tarjeta.usuario"),
    ("Usuarios", "«Crear usuario»"): Objetivo(selector="h2", contiene="Crear usuario"),
    ("Usuarios", "«Crear usuario» (botón)"): Objetivo(selector="form[action='/usuarios'] button[type=submit]"),
    ("Destinatarios", "una tarjeta"): Objetivo(selector=".tarjeta.usuario"),
    ("Avisos", "una tarjeta"): Objetivo(selector=".tarjeta.usuario"),
    # Bitácora y grabación
    ("Bitácora", "el aviso de grabaciones por revisar"): Objetivo(selector="p.aviso"),
    ("Grabación", "el video"): Objetivo(selector="video"),
    # Iniciar sesión
    ("Iniciar sesión", "el título «Iniciar sesión»"): Objetivo(selector="h1"),
    ("Iniciar sesión", "el ojito de «Contraseña»"): Objetivo(selector=".btn-mostrar"),
    # Asistente de elegibilidad: perfil, lista de verificación y asistente
    ("Perfil", "una fila"): Objetivo(selector="table.lista tbody tr"),
    ("Perfil", "el estado"): Objetivo(selector="table.lista .estado-perfil"),
    ("Elemento del perfil", "el estado"): Objetivo(selector=".ficha .estado-perfil"),
    ("Asistente", "la sección «Asistente de elegibilidad»"): Objetivo(selector="#asistente"),
    ("Asistente", "el avance"): Objetivo(selector=".asistente .avance", url="/oportunidades/{sin_encargado}/asistente"),
    ("Asistente", "la pregunta"): Objetivo(selector=".pregunta-asistente"),
    ("Asistente", "el dato del perfil"): Objetivo(selector=".perfil-dato"),
    ("Asistente", "la lista «Antes de pedirla»"): Objetivo(selector=".oferta-falta"),
    ("Revisión rápida", "el resultado rápido"): Objetivo(selector="#revision-rapida"),
    ("Resultado", "la sección «Resultado»"): Objetivo(selector="#resultado"),
    ("Resultado", "el resultado"): Objetivo(selector=".resultado-eleg .resultado-titular"),
    ("Resultado", "la tabla de requisitos"): Objetivo(selector=".resultado-eleg .tabla-resultado"),
    ("Resultado", "«Cumple» y «No cumple»"): Objetivo(selector=".revisar-requisito"),
    ("Constancia", "el detalle por requisito"): Objetivo(selector=".doc-resumen .tabla-resultado"),
    # Correo
    ("Correo", "el asunto"): Objetivo(selector=".asunto"),
    ("Correo", "el cuadro «Resumen con IA»"): Objetivo(selector="div", contiene="Resumen con IA · preliminar"),
}

_TEXTO = re.compile(r"«([^»]+)»( en el menú)?")


class SinObjetivo(ValueError):
    """El marcador no se puede convertir en una pantalla y un elemento: dice la misión y el paso."""


def resolver(m: Marcador) -> tuple[str, Objetivo]:
    """(dirección con {claves} por llenar, objetivo) del marcador."""
    if m.pantalla not in PANTALLAS:
        raise SinObjetivo(f"{m.donde}: la pantalla «{m.pantalla}» no está en app/ayuda/pantallas.py (PANTALLAS).")
    objetivo = ESPECIALES.get((m.pantalla, m.objetivo))
    if objetivo is None:
        texto = _TEXTO.fullmatch(m.objetivo)
        if texto is None:
            raise SinObjetivo(f"{m.donde}: no sé qué resaltar para «{m.objetivo}» en «{m.pantalla}». Escríbelo "
                              "entre «» como en la pantalla o agrégalo a ESPECIALES en app/ayuda/pantallas.py.")
        objetivo = Objetivo(texto=texto.group(1), en_menu=bool(texto.group(2)))
    return objetivo.url or PANTALLAS[m.pantalla], objetivo
