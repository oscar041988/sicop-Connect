"""La oferta completa de un cartel con un solo botón (Oscar, por Ivania, 2026-11-10; DECISION_PROPUESTA.md §12).

Sale como la oferta de NAVSAT (IAFA, 2026): un solo PDF con
1. portada (institución, OFERTA, procedimiento, objeto, oferente);
2. el pliego copiado sección por sección, con «Respuesta Sección NN – Título» al final de cada una;
3. el listado de anexos (1 Oferta económica · 2 Documentación legal · 3 Propuesta técnica · 4 Certificaciones);
4. el anexo 1.1, la oferta económica (app/oferta_economica.py, diseño de Tarrazú) con los precios del tarifario;
5. los documentos que se subieron en el asistente de elegibilidad (o del perfil), cada uno con su página de título.

Quién hace qué:
* El texto del pliego lo copia la app del original; la IA solo marca dónde empieza cada sección (app/ai/oferta.py).
* Si Hermatix cumple lo decide la app con el asistente (app/elegibilidad.py): una sección con un requisito que no
  cumple, falta o hay que revisar NO dice «cumplimos»: sale en rojo con lo que falta, y la portada dice «BORRADOR».
  Todo requisito se presenta; nada se esconde.
* Los precios salen de config/tarifario.yaml (los aprueba Oscar); sin tarifa, «PRECIO PENDIENTE». La app no inventa
  precios, y los montos, el desglose y el monto en letras los calcula la app.
* Los documentos de Hermatix nunca van a la IA: se adjuntan aquí, en la PC, y cada uno queda en el historial.
La app FORMULA la oferta; una persona la revisa, la firma con firma digital y la sube a SICOP.

La misma oferta sale también en Word (.docx, app/propuesta_word.py; Oscar, 2026-11-11, DECISION_IA.md §10.6 bis):
preparar() junta los datos una sola vez y de ahí salen los dos formatos, así que dicen lo mismo.
"""

from __future__ import annotations

import base64
import io
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import asistente, elegibilidad, historial, oferta_economica, perfil
from app.ai import oferta as ia_oferta
from app.ai import resumen as ia_resumen
from app.compras import detalle_compra
from app.config import PROJECT_ROOT, Settings
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR
from app.panel import version_vigente

TARIFARIO = PROJECT_ROOT / "config" / "tarifario.yaml"
GRUPOS = {1: "Oferta Económica", 2: "Documentación Legal", 3: "Propuesta Técnica", 4: "Certificaciones Empresariales"}
# Grupo del anexo según el tipo del elemento del perfil o, si el requisito no tiene elemento, según su tipo.
GRUPO_PERFIL = {"legal": 2, "permiso": 2, "poliza": 2, "financiero": 2, "experiencia": 3, "personal": 3,
                "capacidad": 3, "certificacion": 4, "evaluacion": 4}
GRUPO_REQUISITO = {"legal": 2, "financiero": 2, "tecnico": 3, "experiencia": 3}
_PALABRAS_NUMERO = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
                    "doce": 12, "dieciocho": 18, "veinticuatro": 24, "treinta y seis": 36, "cuarenta y ocho": 48}


class PropuestaError(ValueError):
    """No se puede armar la oferta; el mensaje es el que ve la persona."""


@dataclass
class Bloque:
    """Un trozo del pliego copiado y la respuesta de Hermatix (None en el texto antes de la primera sección)."""
    numero: str
    titulo: str
    texto: str
    tipo: str = "cumple"
    respuesta: list[str] | None = None
    pendiente: bool = False
    inicio: int = 0                       # índice de la página donde empieza (para ubicar los requisitos)


@dataclass
class Anexo:
    grupo: int
    numero: str = ""                      # «2.1»
    titulo: str = ""
    ruta: Path | None = None              # el archivo, o None si está pendiente
    extension: str = ""
    pendiente: str | None = None          # por qué falta
    registrar: object = None              # función que anota el acceso en el historial


@dataclass
class Armada:
    contenido: bytes
    procedimiento: str
    pendientes: list[str] = field(default_factory=list)
    motivo_ia: str | None = None


@dataclass
class Preparada:
    """Todo lo que lleva la oferta, antes de pasarla a PDF o a Word."""
    compra: object
    datos: dict                           # los de la oferta económica: empresa, representante, líneas, procedimiento…
    bloques: list[Bloque]
    anexos: list[Anexo]
    pendientes: list[str]
    oferta: object                        # oferta_economica.Oferta, o None si falta algún precio
    precio_pendiente: str | None
    procedimiento: str
    motivo_ia: str | None
    hoy: object                           # la fecha de la oferta (hora de Costa Rica)

    @property
    def presentes(self) -> list[Anexo]:
        return [a for a in self.anexos if a.ruta is not None]


# --- El pliego sección por sección ---------------------------------------------------------------------------------

def _patron(inicio: str) -> re.Pattern:
    return re.compile(r"\s+".join(re.escape(p) for p in inicio.split()))


def cortar(paginas: list[ia_oferta.Pagina], secciones: list[ia_oferta.Seccion]) -> list[Bloque]:
    """El pliego en bloques: lo que hay antes de la primera sección (sin respuesta) y cada sección hasta la siguiente.
    Sin secciones, el pliego entero es un solo bloque."""
    completo, desde, indice = "", {}, {}
    for i, p in enumerate(paginas):
        desde[(p.doc, p.pagina)] = len(completo)
        indice[(p.doc, p.pagina)] = i
        completo += p.texto.strip() + "\n\n"
    cortes = []
    for s in secciones:
        clave = (s.doc, s.pagina)
        pagina = paginas[indice[clave]].texto.strip()
        if m := _patron(s.inicio).search(pagina):
            cortes.append((desde[clave] + m.start(), s, indice[clave]))
    cortes.sort(key=lambda c: c[0])
    if not cortes:
        return [Bloque("", "Pliego de condiciones", completo.strip(), respuesta=[])]
    bloques = []
    if completo[:cortes[0][0]].strip():
        bloques.append(Bloque("", "", completo[:cortes[0][0]].strip()))
    for n, (posicion, s, pagina) in enumerate(cortes):
        fin = cortes[n + 1][0] if n + 1 < len(cortes) else len(completo)
        bloques.append(Bloque(s.numero, s.titulo, _sin_encabezado(completo[posicion:fin].strip(), s.titulo), s.tipo,
                              [], inicio=pagina))
    return bloques


def _sin_encabezado(texto: str, titulo: str) -> str:
    """El texto de la sección sin su primera línea si esa línea es el título (ya va como encabezado)."""
    primera, _, resto = texto.partition("\n")
    if titulo and " ".join(titulo.lower().split()) in " ".join(primera.lower().split()) and len(primera) < 2 * len(titulo) + 12:
        return resto.strip()
    return texto


_MENORES = {"a", "al", "de", "del", "el", "en", "la", "las", "los", "o", "por", "para", "y", "con", "e", "u"}


def titulo_es(texto: str) -> str:
    """«LLAMADO A COTIZAR» → «Llamado a Cotizar», como en la respuesta de NAVSAT."""
    palabras = texto.lower().split()
    return " ".join(p if n and p in _MENORES else p[:1].upper() + p[1:] for n, p in enumerate(palabras))


def responder(bloques: list[Bloque], paginas: list[ia_oferta.Pagina],
              evaluaciones: list[elegibilidad.Evaluacion]) -> list[elegibilidad.Evaluacion]:
    """Pone la respuesta de cada sección. Un requisito del asistente va a la sección donde lo cita el pliego; si en
    una sección algo no cumple, falta o hay que revisar, la respuesta lo dice (en rojo) en lugar de «cumplimos».
    Devuelve los pendientes que no caen en ninguna sección (van en la portada)."""
    indice = {(p.doc, p.pagina): i for i, p in enumerate(paginas)}
    con_respuesta = [b for b in bloques if b.respuesta is not None]
    sueltos = []
    for e in evaluaciones:
        lugar = ia_oferta.lugar_de([*e.item.citas, e.item.requisito])
        destino = None
        if lugar in indice:
            destino = next((b for b in reversed(con_respuesta) if b.inicio <= indice[lugar]), None)
        if destino is None and len(con_respuesta) == 1:
            destino = con_respuesta[0]
        if e.estado == "cumple":
            continue
        linea = f"{e.estado_texto}{' (excluyente)' if e.item.excluyente else ''}: {_sin_citas(e.item.requisito)} — {e.motivo}"
        if destino is None:
            sueltos.append(e)
            continue
        destino.pendiente = True
        destino.respuesta.append(linea)
    for b in con_respuesta:
        if b.pendiente:
            b.respuesta.insert(0, "PENDIENTE antes de firmar: el asistente de elegibilidad dice")
        else:
            b.respuesta = [ia_oferta.TIPOS.get(b.tipo, ia_oferta.TIPOS["cumple"])]
    return sueltos


def _sin_citas(texto: str) -> str:
    return " ".join(re.sub(r"\[DOC[^\]]*\]", "", texto).split())


# --- Oferta económica con el tarifario -------------------------------------------------------------------------------

def tarifario(ruta: Path | None = None) -> dict:
    """Los productos de config/tarifario.yaml ({} si no hay archivo o no tiene productos)."""
    ruta = ruta or TARIFARIO
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    productos = datos.get("productos") if isinstance(datos, dict) else None
    return productos if isinstance(productos, dict) else {}


def producto_del_cartel(conn: sqlite3.Connection, nro_sicop: str) -> str | None:
    """El producto de Hermatix de la familia con mejor encaje en la evaluación vigente (lo dicen las reglas)."""
    version = version_vigente(conn)
    fila = conn.execute(
        "SELECT producto FROM opportunity_assessments WHERE nro_sicop = ? AND rules_version = ?"
        " AND encaje IN ('alta', 'media', 'baja') AND producto IS NOT NULL"
        " ORDER BY CASE encaje WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, id LIMIT 1",
        (nro_sicop, version)).fetchone()
    return fila[0] if fila else None


def meses_de(vigencia: str | None) -> int | None:
    """«1 año» → 12, «24 meses» → 24, «un año» → 12; None si el pliego no lo dice claro."""
    texto = " ".join((vigencia or "").lower().split())
    for palabra, n in sorted(_PALABRAS_NUMERO.items(), key=lambda x: -len(x[0])):
        texto = re.sub(rf"\b{palabra}\b", str(n), texto)
    if m := re.search(r"\b(\d{1,3})\s*(mes|meses|año|años|ano|anos)\b", texto):
        n = int(m.group(1)) * (1 if m.group(2).startswith("mes") else 12)
        return n if 1 <= n <= 120 else None
    return None


def _vigencia(conn: sqlite3.Connection, nro_sicop: str) -> str | None:
    r = ia_resumen.ultimo(conn, nro_sicop)
    try:
        return r.datos["kpi_pliego"]["vigencia_contrato"]["valor"] if r and r.datos else None
    except (KeyError, TypeError):
        return None


def economica(conn: sqlite3.Connection, nro_sicop: str, compra, config: dict, tarifas: dict,
              hoy) -> tuple[oferta_economica.Oferta | None, dict, str | None]:
    """(oferta calculada o None, datos para la carta y la tabla, por qué el precio está pendiente)."""
    tipo = conn.execute("SELECT tipo_procedimiento FROM tenders WHERE nro_sicop = ?", (nro_sicop,)).fetchone()[0]
    datos = oferta_economica.valores_iniciales(compra, tipo, config)
    datos["representante"] = {**datos["representante"], **{k: str(v or "") for k, v in
                                                          (config.get("representante") or {}).items()}}
    datos["fecha"] = hoy.isoformat()
    for linea in datos["lineas"]:
        linea["descripcion"] = linea["descripcion"] or compra.descripcion or "Servicio"
    producto = producto_del_cartel(conn, nro_sicop)
    tarifa = tarifas.get(producto) if producto else None
    if not isinstance(tarifa, dict) or tarifa.get("precio") in (None, ""):
        motivo = (f"no hay tarifa para «{producto}» en config/tarifario.yaml" if producto
                  else "las reglas no asignaron un producto de Hermatix a este cartel")
        return None, datos, motivo
    datos["moneda"] = str(tarifa.get("moneda") or "CRC")
    datos["meses"] = meses_de(_vigencia(conn, nro_sicop)) if tarifa.get("periodo") == "mensual" else None
    for linea in datos["lineas"]:
        linea["precio_unitario"] = str(tarifa["precio"])
    iva = tarifa.get("iva", 13)
    datos["iva"] = ({"exento": str(iva).split(":", 1)[1].strip()} if str(iva).lower().startswith("exento")
                    else {"tasa": str(iva)})
    for clave, pct in (tarifa.get("desglose") or {}).items():
        if clave in datos["desglose"]:
            datos["desglose"][clave]["porcentaje"] = str(pct)
    try:
        return oferta_economica.leer(datos), datos, None
    except oferta_economica.OfertaError as exc:
        return None, datos, f"el tarifario no sirve para este cartel: {str(exc).rstrip('. ')}"


# --- Anexos: lo que se subió en el asistente (o está en el perfil) -------------------------------------------------

def anexos(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien,
           evaluaciones: list[elegibilidad.Evaluacion]) -> list[Anexo]:
    """Un anexo por documento de los requisitos del asistente, numerados por grupo como en NAVSAT. Los que faltan
    quedan en la lista como pendientes (no se esconden). Un mismo archivo para dos requisitos va una sola vez."""
    lista, vistos = [], set()
    for e in evaluaciones:
        item, r = e.item, e.respuesta
        if item.tipo_evidencia != "documento":
            continue
        elemento = perfil.obtener(conn, item.perfil_item_id) if item.perfil_item_id else None
        grupo = GRUPO_PERFIL.get(elemento.tipo, 3) if elemento else GRUPO_REQUISITO.get(item.tipo, 2)
        titulo = item.perfil_titulo or _sin_citas(item.requisito)[:140]
        anexo = Anexo(grupo, titulo=titulo)
        if r is not None and r.tiene_archivo:
            hallado = asistente.documento(conn, settings.assistant_docs_dir, nro_sicop, r.id)
            if hallado:
                ruta, resp = hallado
                anexo.ruta, anexo.extension = ruta, ruta.suffix.lower()
                anexo.registrar = lambda resp=resp: asistente.registrar_acceso(
                    conn, quien, "adjuntar_documento_oferta", nro_sicop, resp)
        elif r is not None and r.fuente == "perfil" and r.perfil_version_id and item.perfil_item_id:
            hallado = perfil.documento(conn, settings.profile_docs_dir, item.perfil_item_id, r.perfil_version_id)
            if hallado:
                ruta, version = hallado
                anexo.ruta, anexo.extension = ruta, ruta.suffix.lower()
                anexo.registrar = lambda v=version, i=item: perfil.registrar_acceso(
                    conn, quien, "adjuntar_documento_oferta", i.perfil_item_id, i.perfil_titulo or "", v)
        if anexo.ruta is None:
            anexo.pendiente = "no se subió el archivo" if e.estado != "no_cumple" else e.motivo
        elif anexo.ruta.resolve() in vistos:
            continue
        else:
            vistos.add(anexo.ruta.resolve())
        lista.append(anexo)
    lista.append(Anexo(3, titulo="Ficha técnica del equipo ofertado",
                       pendiente="falta elegir la ficha técnica del equipo (pendiente de Oscar)"))
    for grupo in (2, 3, 4):
        for n, a in enumerate((a for a in lista if a.grupo == grupo), start=1):
            a.numero = f"{grupo}.{n}"
    return sorted(lista, key=lambda a: (a.grupo, int(a.numero.split(".")[1])))


def _pdf_valido(ruta: Path) -> bool:
    import pypdfium2 as pdfium
    try:
        doc = pdfium.PdfDocument(ruta)
        try:
            return len(doc) > 0
        finally:
            doc.close()
    except Exception:  # noqa: BLE001 — cifrado, dañado o no es PDF: se adjunta a mano
        return False


# --- El documento --------------------------------------------------------------------------------------------------

def _entorno() -> Environment:
    entorno = Environment(loader=FileSystemLoader(oferta_economica.PLANTILLAS), autoescape=select_autoescape(["html"]))
    entorno.filters["titulo_es"] = titulo_es
    return entorno


def _imagen(ruta: Path) -> str:
    tipo = "png" if ruta.suffix.lower() == ".png" else "jpeg"
    return f"data:image/{tipo};base64,{base64.b64encode(ruta.read_bytes()).decode('ascii')}"


def unir(partes: list[tuple[bytes, list[int] | None]]) -> bytes:
    """Une PDFs: cada parte con todas sus páginas (None) o solo las indicadas."""
    import pypdfium2 as pdfium
    destino = pdfium.PdfDocument.new()
    abiertos = []
    for contenido, paginas in partes:
        origen = pdfium.PdfDocument(contenido)
        abiertos.append(origen)
        destino.import_pages(origen, pages=paginas)
    salida = io.BytesIO()
    destino.save(salida)
    for d in abiertos:
        d.close()
    destino.close()
    return salida.getvalue()


def _contar(contenido: bytes) -> int:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(contenido)
    try:
        return len(doc)
    finally:
        doc.close()


def _hojas(imprimir, plantilla, hojas: list[dict], procedimiento: str, **contexto) -> list[tuple[bytes, int]]:
    """Cada hoja propia como (PDF, página). Se imprimen todas juntas (un solo Chromium); si alguna no cupo en una
    página, cada una por separado (más lento, pero ninguna se corre de lugar)."""
    juntas = imprimir(plantilla.render(hojas=hojas, **contexto), procedimiento)
    if _contar(juntas) == len(hojas):
        return [(juntas, i) for i in range(len(hojas))]
    return [(imprimir(plantilla.render(hojas=[h], **contexto), procedimiento), 0) for h in hojas]


def preparar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, ahora: datetime,
             cliente=None, dormir=None, tarifas: dict | None = None) -> Preparada:
    """Junta todo lo de la oferta del cartel. Lanza PropuestaError si no se puede (sin cartel o sin pliego).
    No escribe nada: el historial lo anota quien la entrega (armar o armar_word)."""
    compra = detalle_compra(conn, nro_sicop)
    if compra is None:
        raise PropuestaError(f"No hay un cartel con Número SICOP {nro_sicop}.")
    paginas = ia_oferta.paginas_del_pliego(conn, nro_sicop)
    if not paginas:
        raise PropuestaError("Falta el pliego: el cartel todavía no tiene sus documentos de SICOP con texto "
                             "(los trae el enriquecimiento). Sin el pliego no se puede armar la oferta.")
    hoy = ahora.astimezone(HORA_CR).date()
    config = oferta_economica.configuracion()
    secciones, motivo_ia = ia_oferta.secciones(conn, settings, nro_sicop, paginas, cliente=cliente, dormir=dormir)
    bloques = cortar(paginas, secciones)

    pendientes = []
    if asistente.sesion(conn, nro_sicop) is None:
        evaluaciones = []
        pendientes.append("El asistente de elegibilidad de este cartel no se ha empezado: ningún requisito está "
                          "comprobado.")
    else:
        evaluaciones, _ = elegibilidad.evaluacion_actual(conn, nro_sicop, hoy)
    sueltos = responder(bloques, paginas, evaluaciones)
    pendientes += [f"Sección «{b.titulo or b.numero}»: {len(b.respuesta) - 1} punto(s) sin resolver."
                   for b in bloques if b.pendiente]
    pendientes += [f"{e.estado_texto}: {_sin_citas(e.item.requisito)} — {e.motivo}" for e in sueltos]

    oferta, datos, precio_pendiente = economica(conn, nro_sicop, compra, config,
                                                tarifario() if tarifas is None else tarifas, hoy)
    if precio_pendiente:
        pendientes.append(f"PRECIO PENDIENTE: {precio_pendiente}.")
    if not datos["representante"].get("nombre"):
        pendientes.append("Faltan el nombre y la cédula del representante legal (config/oferta.yaml).")

    lista = anexos(conn, settings, nro_sicop, quien, evaluaciones)
    for a in lista:
        if a.ruta is not None and a.extension == ".pdf" and not _pdf_valido(a.ruta):
            a.ruta, a.pendiente = None, "el PDF no se pudo abrir (¿protegido?): adjuntarlo a mano"
    pendientes += [f"Anexo {a.numero} · {a.titulo}: {a.pendiente}." for a in lista if a.pendiente]

    return Preparada(compra, datos, bloques, lista, pendientes, oferta, precio_pendiente,
                     datos["procedimiento"] or nro_sicop, motivo_ia, hoy)


def _anotar(conn: sqlite3.Connection, quien: Quien, nro_sicop: str, p: Preparada, accion: str) -> None:
    """Cada documento adjuntado queda en el historial (y en los accesos del perfil), y la oferta generada también."""
    for a in p.presentes:
        a.registrar()
    with transaccion(conn):
        historial.registrar(conn, quien, accion,
                            f"{nro_sicop}: {len(p.presentes)} anexo(s), {len(p.pendientes)} pendiente(s)")


def armar(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, ahora: datetime,
          cliente=None, dormir=None, imprimir=oferta_economica.pdf, tarifas: dict | None = None) -> Armada:
    """Arma la oferta completa del cartel en PDF. Lanza PropuestaError si no se puede (sin cartel o sin pliego).
    cliente, dormir, imprimir y tarifas solo se cambian en las pruebas (IA SIMULADA, tarifario SINTÉTICO)."""
    p = preparar(conn, settings, nro_sicop, quien, ahora, cliente=cliente, dormir=dormir, tarifas=tarifas)
    contenido = _pdf(p, imprimir)
    _anotar(conn, quien, nro_sicop, p, "generar_oferta")
    return Armada(contenido, p.procedimiento, p.pendientes, p.motivo_ia)


def armar_word(conn: sqlite3.Connection, settings: Settings, nro_sicop: str, quien: Quien, ahora: datetime,
               cliente=None, dormir=None, tarifas: dict | None = None) -> Armada:
    """La misma oferta en Word (.docx). No necesita Chromium: lo escribe python-docx."""
    from app import propuesta_word
    p = preparar(conn, settings, nro_sicop, quien, ahora, cliente=cliente, dormir=dormir, tarifas=tarifas)
    contenido = propuesta_word.documento(p)
    _anotar(conn, quien, nro_sicop, p, "generar_oferta_word")
    return Armada(contenido, p.procedimiento, p.pendientes, p.motivo_ia)


def _pdf(p: Preparada, imprimir) -> bytes:
    datos, lista, oferta, precio_pendiente = p.datos, p.anexos, p.oferta, p.precio_pendiente
    procedimiento, hoy = p.procedimiento, p.hoy
    entorno = _entorno()
    principal = entorno.get_template("propuesta.html").render(
        d=datos, c=p.compra, bloques=p.bloques, anexos=lista, GRUPOS=GRUPOS, pendientes=p.pendientes,
        oferta=oferta, precio_pendiente=precio_pendiente)
    # Plan del documento después de la parte principal: hojas propias (título de cada anexo, imagen, precio
    # pendiente), la oferta económica y los PDF adjuntos, en el orden del listado de anexos.
    presentes = p.presentes
    hojas, plan = [], []

    def hoja(**h):
        hojas.append(h)
        plan.append(("hoja", len(hojas) - 1))
    hoja(tipo="titulo", texto="Anexo 1.1: Oferta Económica y Desglose del Precio")
    if oferta is not None:
        plan.append(("pdf", imprimir(oferta_economica.html(oferta, hoy), procedimiento)))
    else:
        hoja(tipo="precio_pendiente")
    for a in presentes:
        hoja(tipo="titulo", texto=f"Anexo {a.numero}: {a.titulo}")
        if a.extension == ".pdf":
            plan.append(("pdf", a.ruta.read_bytes()))
        else:
            hoja(tipo="imagen", src=_imagen(a.ruta))
    plantilla = entorno.get_template("propuesta_anexos.html")
    impresas = _hojas(imprimir, plantilla, hojas, procedimiento, d=datos, precio_pendiente=precio_pendiente)
    partes = [(imprimir(principal, procedimiento), None)]
    for tipo, valor in plan:
        if tipo == "hoja":
            contenido_hoja, pagina = impresas[valor]
            partes.append((contenido_hoja, [pagina]))
        else:
            partes.append((valor, None))
    return unir(partes)
