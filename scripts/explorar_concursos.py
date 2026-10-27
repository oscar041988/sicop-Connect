"""Exploración de la consulta pública de concursos (enriquecimiento, lección 1, encargo 1). SOLO EXPLORA.

Abre la consulta de concursos con la ventana VISIBLE, entra a «Búsqueda avanzada», escribe UN Número SICOP en
«Número de SICOP», pulsa «Consultar» y abre el resultado. NO descarga documentos, no recorre listados y no repite.
Anota:
* los elementos usados, con sus datos para elegir selectores estables (texto visible, rol, id, clases);
* la URL de la ficha, sus bloques de información (títulos y etiquetas) y la lista de documentos SIN descargarlos;
* las peticiones de red de la página: método, servidor, ruta, estado y tipo de respuesta (sin ?parámetros, sin
  cookies). De las respuestas JSON muestra sus CAMPOS (nombres y tipos, no los valores).
Ante un CAPTCHA, un bloqueo o «No fue posible acceder a la página solicitada» se detiene y lo reporta: no lo evita.

Uso (una sola vez, mirando la ventana):
    .venv\\Scripts\\python.exe scripts\\explorar_concursos.py 20261002859
Si un clic automático no encuentra el elemento, el script pide hacerlo a mano en la ventana y presionar Enter.
Todo queda en data/exports/exploracion-concursos-AAAAMMDD-HHMMSS/ (fuera de Git): informe.txt, una captura por
paso, el texto de la ficha (ficha.txt) y las respuestas JSON completas (para las fichas SIMULADAS de la lección 2;
pueden traer contactos: no se suben a Git ni se pegan en chats).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

URL = "https://www.sicop.go.cr/app/module/bid/public/tenders"
PROYECTO = Path(__file__).resolve().parent.parent
SALIDA = PROYECTO / "data" / "exports"
ESPERA_MS = 30_000
RECURSOS_RESUMIDOS = {"image", "font", "stylesheet", "media"}
NRO_SICOP = re.compile(r"^\d{11}$")
CONTROL = re.compile(r"captcha|no soy un robot|acceso denegado|demasiadas solicitudes"
                     r"|no fue posible acceder a la página solicitada", re.IGNORECASE)
DOCUMENTO = re.compile(r"\.(pdf|docx?|xlsx?|zip|rar)\b|descargar|documento|adjunto|archivo", re.IGNORECASE)

DESCRIBIR = """e => ({
  etiqueta: e.tagName.toLowerCase(), id: e.id || '', clases: (e.className && e.className.baseVal === undefined)
    ? e.className : '', rol: e.getAttribute('role') || '', aria: e.getAttribute('aria-label') || '',
  titulo: e.getAttribute('title') || '', tipo: e.getAttribute('type') || '', nombre: e.getAttribute('name') || '',
  placeholder: e.getAttribute('placeholder') || '', href: e.getAttribute('href') || '',
  texto: (e.innerText || e.value || '').trim().replace(/\\s+/g, ' ').slice(0, 100)
})"""

# Títulos y etiquetas de la ficha: lo que sirve para nombrar sus bloques en DETALLE_CARTEL.md.
BLOQUES = """() => [...document.querySelectorAll('h1,h2,h3,h4,h5,legend,caption,th,label,[role=tab],[role=heading]')]
  .filter(e => e.offsetParent !== null)
  .map(e => e.tagName.toLowerCase() + ' · ' + (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80))
  .filter(t => !t.endsWith(' · '))"""


class Detenido(Exception):
    """CAPTCHA, bloqueo o aviso contra programas: se detiene sin reintentar."""


class Informe:
    def __init__(self) -> None:
        self.lineas: list[str] = []

    def __call__(self, texto: str = "") -> None:
        print(texto)
        self.lineas.append(texto)


def _describir(locator) -> str:
    try:
        d = locator.evaluate(DESCRIBIR)
    except PlaywrightError:
        return "(no se pudo leer el elemento)"
    partes = [f"<{d['etiqueta']}>"]
    for clave in ("texto", "rol", "aria", "titulo", "tipo", "nombre", "placeholder", "href", "id", "clases"):
        if d[clave]:
            partes.append(f"{clave}={d[clave]!r}")
    return " ".join(partes)


def _visibles(page: Page, construir, tope: int = 20) -> list:
    encontrados = []
    for marco in page.frames:  # la página y sus iframes
        loc = construir(marco)
        for i in range(min(loc.count(), tope)):
            if loc.nth(i).is_visible():
                encontrados.append(loc.nth(i))
    return encontrados


def _campos(valor, prefijo: str = "", nivel: int = 0) -> list[str]:
    """Nombres y tipos de los campos de un JSON, sin sus valores. De una lista, solo su primer elemento."""
    if nivel > 4:
        return []
    if isinstance(valor, dict):
        salida = []
        for clave, sub in valor.items():
            ruta = f"{prefijo}.{clave}" if prefijo else clave
            salida.append(f"{ruta}: {type(sub).__name__}")
            salida += _campos(sub, ruta, nivel + 1)
        return salida
    if isinstance(valor, list) and valor:
        return [f"{prefijo}[] ({len(valor)} elementos)"] + _campos(valor[0], f"{prefijo}[]", nivel + 1)
    return []


def _a_mano(instruccion: str) -> None:
    input(f"\n>>> {instruccion}\n>>> Hazlo en la ventana del navegador y presiona Enter aquí para seguir... ")


def explorar(nro: str) -> int:
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    carpeta = SALIDA / f"exploracion-concursos-{sello}"
    carpeta.mkdir(parents=True, exist_ok=True)
    informe = Informe()
    peticiones: Counter = Counter()
    resumidas: Counter = Counter()
    jsons: list[tuple[str, object]] = []
    bloqueos: list[str] = []

    def anotar(respuesta) -> None:
        pedido = respuesta.request
        partes = urlsplit(pedido.url)  # sin ?parámetros
        tipo = (respuesta.headers.get("content-type") or "").split(";")[0]
        if pedido.resource_type in RECURSOS_RESUMIDOS:
            resumidas[(partes.netloc, pedido.resource_type)] += 1
            return
        peticiones[(pedido.method, partes.netloc, partes.path, pedido.resource_type, respuesta.status, tipo)] += 1
        if respuesta.status in (403, 429) and pedido.resource_type in ("document", "xhr", "fetch"):
            bloqueos.append(f"HTTP {respuesta.status} en {partes.netloc}{partes.path}")
        if "json" in tipo and pedido.resource_type in ("xhr", "fetch"):
            try:
                jsons.append((f"{pedido.method} {partes.netloc}{partes.path}", respuesta.json()))
            except Exception:  # cuerpo vacío o no legible: queda en la lista de peticiones
                pass

    def foto(page: Page, nombre: str) -> None:
        try:
            page.screenshot(path=str(carpeta / f"{nombre}.png"), full_page=True)
        except PlaywrightError:
            informe(f"   (no se pudo tomar la captura {nombre})")

    def revisar_control(page: Page, paso: str) -> None:
        if bloqueos or page.locator("iframe[src*='captcha' i]").count() or page.get_by_text(CONTROL).count():
            foto(page, f"{paso}-DETENIDO")
            raise Detenido(f"{paso}: CAPTCHA, bloqueo o aviso de SICOP ({'; '.join(bloqueos) or 'texto en pantalla'})")

    informe(f"Exploración de la consulta de concursos · {datetime.now():%Y-%m-%d %H:%M} · Número SICOP {nro}")
    informe(f"URL: {URL} · solo explora: no descarga documentos")
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False, slow_mo=400)
        contexto = navegador.new_context(locale="es-CR")  # sin cookies guardadas; no se guarda nada al cerrar
        contexto.on("response", anotar)  # en el contexto: también cubre una pestaña nueva con la ficha
        page = contexto.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            informe(f"\n1. Página abierta. Título: {page.title()!r} · iframes: {len(page.frames) - 1}")
            revisar_control(page, "1-inicio")
            foto(page, "1-inicio")

            # 2. Búsqueda avanzada.
            avanzada = _visibles(page, lambda m: m.get_by_text("Búsqueda avanzada", exact=False))
            informe(f"\n2. «Búsqueda avanzada»: {len(avanzada)} elemento(s) visible(s)")
            for a in avanzada:
                informe(f"   {_describir(a)}")
            if avanzada:
                avanzada[0].click()
                page.wait_for_timeout(1500)  # solo para ver la animación
            else:
                _a_mano("Abre «Búsqueda avanzada».")
            revisar_control(page, "2-avanzada")
            foto(page, "2-avanzada")

            # 3. Casilla «Número de SICOP» (no confundir con «Número de procedimiento»).
            casilla = _visibles(page, lambda m: m.get_by_label("Número de SICOP", exact=False))
            if not casilla:
                casilla = _visibles(page, lambda m: m.get_by_placeholder("SICOP", exact=False))
            informe(f"\n3. Casilla «Número de SICOP»: {len(casilla)} candidata(s)")
            for c in casilla:
                informe(f"   {_describir(c)}")
            etiquetas = _visibles(page, lambda m: m.get_by_text("Número de SICOP", exact=False))
            for e in etiquetas:
                informe(f"   etiqueta: {_describir(e)}")
            campos = _visibles(page, lambda m: m.locator("input, select, textarea"), tope=40)
            informe(f"   Campos del formulario visibles: {len(campos)}")
            for c in campos:
                informe(f"   · {_describir(c)}")
            if len(casilla) == 1:
                casilla[0].fill(nro)
            else:
                _a_mano(f"Escribe {nro} en «Número de SICOP» (hay {len(casilla)} candidatos; anota cuál era).")

            # 4. Consultar.
            consultar = _visibles(page, lambda m: m.get_by_role("button", name="Consultar"))
            if not consultar:
                consultar = _visibles(page, lambda m: m.get_by_text("Consultar", exact=True))
            informe(f"\n4. «Consultar»: {len(consultar)} elemento(s)")
            for c in consultar:
                informe(f"   {_describir(c)}")
            if len(consultar) == 1:
                consultar[0].click()
            else:
                _a_mano("Pulsa «Consultar».")
            page.wait_for_load_state("networkidle", timeout=ESPERA_MS)
            revisar_control(page, "4-resultado")
            foto(page, "4-resultado")

            # 5. Resultado: solo el que muestra el número buscado (nunca otro cartel).
            resultados = _visibles(page, lambda m: m.get_by_text(nro, exact=False))
            informe(f"\n5. Elementos con el número {nro} en el resultado: {len(resultados)}")
            for r in resultados:
                informe(f"   {_describir(r)}")
            enlaces = _visibles(page, lambda m: m.locator("a, [role=link], [role=button], button"), tope=60)
            cerca = [e for e in enlaces if nro in (e.inner_text() or "")]
            informe(f"   Enlaces o botones que dicen {nro}: {len(cerca)}")
            paginas_antes = len(contexto.pages)
            if len(cerca) == 1:
                cerca[0].click()
            else:
                _a_mano(f"Abre el resultado de {nro} (anota en qué hiciste clic).")
            page.wait_for_timeout(3000)
            if len(contexto.pages) > paginas_antes:
                page = contexto.pages[-1]
                informe("   La ficha se abrió en una pestaña nueva.")
            page.wait_for_load_state("networkidle", timeout=ESPERA_MS)
            revisar_control(page, "5-ficha")
            foto(page, "5-ficha")

            # 6. Ficha.
            informe(f"\n6. Ficha · URL: {page.url}")
            informe(f"   ¿Muestra el número buscado? {'sí' if page.get_by_text(nro).count() else 'NO (revisar)'}")
            informe("   Bloques (títulos, pestañas y etiquetas visibles):")
            for b in dict.fromkeys(page.evaluate(BLOQUES)):  # sin repetidos, en orden
                informe(f"   · {b}")
            (carpeta / "ficha.txt").write_text(page.inner_text("body"), encoding="utf-8")
            informe("   Texto completo en ficha.txt (puede traer contactos: no va a Git).")

            # 7. Documentos: se listan, NO se descargan ni se abren.
            docs = [e for e in _visibles(page, lambda m: m.locator("a, button, [role=button], [role=link]"), tope=200)
                    if DOCUMENTO.search(_describir(e))]
            informe(f"\n7. Posibles documentos (sin descargar): {len(docs)}")
            for d in docs:
                informe(f"   {_describir(d)}")
            if not docs:
                informe("   Ninguno a la vista: quizá están en una pestaña o sección de la ficha (ver captura).")
        except Detenido as exc:
            informe(f"\nDETENIDO (no se reintenta ni se evita): {exc}. Avisar a Oscar.")
        except PlaywrightError as exc:
            informe(f"\nError de Playwright: {type(exc).__name__}: {str(exc).splitlines()[0]}")
        finally:
            foto(page, "final")
            input("\n>>> Revisa la ventana (no descargues nada). Presiona Enter para cerrar el navegador... ")
            navegador.close()

    informe("\nPeticiones de red (método · servidor · ruta · tipo de recurso · estado · tipo de respuesta · veces):")
    for (metodo, servidor, ruta, recurso, estado, tipo), veces in sorted(peticiones.items()):
        informe(f"  {metodo} {servidor}{ruta} · {recurso} · {estado} · {tipo or '-'} · {veces}")
    informe("Resumidas (imágenes, fuentes, estilos):")
    for (servidor, recurso), veces in sorted(resumidas.items()):
        informe(f"  {servidor} · {recurso} · {veces}")

    informe(f"\nRespuestas JSON: {len(jsons)} (campos sin valores; completas en json-N.json)")
    for i, (origen, cuerpo) in enumerate(jsons, 1):
        (carpeta / f"json-{i}.json").write_text(json.dumps(cuerpo, ensure_ascii=False, indent=2), encoding="utf-8")
        contiene = "sí" if nro in json.dumps(cuerpo, ensure_ascii=False) else "no"
        informe(f"\n  json-{i} · {origen} · ¿trae {nro}? {contiene}")
        for campo in _campos(cuerpo)[:80]:
            informe(f"    {campo}")

    archivo = carpeta / "informe.txt"
    archivo.write_text("\n".join(informe.lineas) + "\n", encoding="utf-8")
    print(f"\nInforme guardado en {archivo.relative_to(PROYECTO)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or not NRO_SICOP.match(sys.argv[1]):
        sys.exit("Uso: python scripts\\explorar_concursos.py NUMERO_SICOP  (11 dígitos, p. ej. 20261002859)")
    sys.exit(explorar(sys.argv[1]))
