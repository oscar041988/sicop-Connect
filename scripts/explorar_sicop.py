"""Exploración del portal de SICOP (obtención automática, lección 2, encargo 2A). SOLO EXPLORA: no envía nada.

Abre Datos abiertos con la ventana VISIBLE, despliega «Detalle pliego de condiciones», hace clic en CSV y se detiene
en la ventana «Correo electrónico donde se le notificará» SIN escribir el correo ni pulsar Continuar. Anota:
* los elementos usados, con sus datos para elegir selectores estables (texto visible, rol, id, clases);
* las peticiones de red que hizo la página: método, servidor, ruta y tipo de respuesta. Sin los parámetros de la
  dirección (?…), sin cookies y sin cuerpos.

Uso (una sola vez, mirando la ventana):
    .venv\\Scripts\\python.exe scripts\\explorar_sicop.py
Si un clic automático no encuentra el elemento, el script pide hacerlo a mano en la ventana y presionar Enter.
El informe queda en data/exports/exploracion-sicop-AAAAMMDD-HHMMSS.txt, con una captura .png al lado.
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Frame, Page, sync_playwright

URL = "https://www.sicop.go.cr/app/module/pcont/public/ce-open-data"
REPORTE = "Detalle pliego de condiciones"
TEXTO_VENTANA_CORREO = "Correo electrónico"
PROYECTO = Path(__file__).resolve().parent.parent
SALIDA = PROYECTO / "data" / "exports"
ESPERA_MS = 30_000
RECURSOS_RESUMIDOS = {"image", "font", "stylesheet", "media"}

# Datos de un elemento útiles para elegir un selector: el texto y el rol son estables; las clases, casi nunca.
DESCRIBIR = """e => ({
  etiqueta: e.tagName.toLowerCase(), id: e.id || '', clases: (e.className && e.className.baseVal === undefined)
    ? e.className : '', rol: e.getAttribute('role') || '', aria: e.getAttribute('aria-label') || '',
  titulo: e.getAttribute('title') || '', alt: e.getAttribute('alt') || '', tipo: e.getAttribute('type') || '',
  nombre: e.getAttribute('name') || '', placeholder: e.getAttribute('placeholder') || '',
  texto: (e.innerText || e.value || '').trim().replace(/\\s+/g, ' ').slice(0, 80)
})"""


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
    for clave in ("texto", "rol", "aria", "titulo", "alt", "tipo", "nombre", "placeholder", "id", "clases"):
        if d[clave]:
            partes.append(f"{clave}={d[clave]!r}")
    return " ".join(partes)


def _marcos(page: Page) -> list[Frame]:
    """La página principal y sus iframes (algunos portales ponen el contenido dentro de uno)."""
    return list(page.frames)


def _visibles(page: Page, construir) -> list:
    encontrados = []
    for marco in _marcos(page):
        loc = construir(marco)
        for i in range(min(loc.count(), 20)):
            if loc.nth(i).is_visible():
                encontrados.append(loc.nth(i))
    return encontrados


def _a_mano(instruccion: str) -> None:
    input(f"\n>>> {instruccion}\n>>> Hazlo en la ventana del navegador y presiona Enter aquí para seguir... ")


def explorar() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    informe = Informe()
    peticiones: Counter = Counter()
    resumidas: Counter = Counter()

    def anotar(respuesta) -> None:
        pedido = respuesta.request
        partes = urlsplit(pedido.url)  # sin ?parámetros: ahí podría haber datos de la sesión
        tipo = (respuesta.headers.get("content-type") or "").split(";")[0]
        if pedido.resource_type in RECURSOS_RESUMIDOS:
            resumidas[(partes.netloc, pedido.resource_type)] += 1
        else:
            peticiones[(pedido.method, partes.netloc, partes.path, pedido.resource_type, respuesta.status, tipo)] += 1

    informe(f"Exploración de SICOP · {datetime.now():%Y-%m-%d %H:%M} · solo explora: no se envía nada")
    informe(f"URL: {URL}")
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False, slow_mo=400)
        contexto = navegador.new_context(locale="es-CR")  # contexto nuevo: sin cookies guardadas, no se guarda nada
        page = contexto.new_page()
        page.on("response", anotar)
        try:
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            informe(f"\n1. Página abierta. Título: {page.title()!r} · marcos (iframes): {len(page.frames) - 1}")

            # 2. Desplegar el reporte.
            reportes = _visibles(page, lambda m: m.get_by_text(REPORTE, exact=False))
            informe(f"\n2. «{REPORTE}»: {len(reportes)} elemento(s) visible(s) con ese texto")
            for r in reportes:
                informe(f"   {_describir(r)}")
            if len(reportes) >= 1:
                reportes[0].click()
                page.wait_for_timeout(1500)  # solo para ver la animación; el paso siguiente espera de verdad
            else:
                _a_mano(f"Despliega «{REPORTE}».")

            # 3. Elegir CSV.
            csv = _visibles(page, lambda m: m.locator("[title*='CSV' i], [alt*='CSV' i], [aria-label*='CSV' i]"))
            csv += _visibles(page, lambda m: m.get_by_text("CSV", exact=True))
            informe(f"\n3. Elementos visibles que dicen CSV: {len(csv)}")
            for c in csv:
                informe(f"   {_describir(c)}")
            if len(csv) == 1:
                csv[0].click()
            else:
                _a_mano(f"Haz clic en el icono CSV de «{REPORTE}» (hay {len(csv)} candidatos; anota cuál era).")

            # 4. Ventana del correo: se describe y NO se escribe nada.
            try:
                page.get_by_text(TEXTO_VENTANA_CORREO, exact=False).first.wait_for(state="visible", timeout=ESPERA_MS)
                informe(f"\n4. Apareció la ventana «{TEXTO_VENTANA_CORREO}…». No se escribe el correo.")
            except PlaywrightError:
                informe(f"\n4. No apareció «{TEXTO_VENTANA_CORREO}» en {ESPERA_MS // 1000} s (ver la captura).")
            dialogos = _visibles(page, lambda m: m.get_by_role("dialog"))
            informe(f"   Ventanas con rol «dialog»: {len(dialogos)}")
            # Solo lo que está dentro de la ventana (antes se listaba toda la página y no se veían sus campos).
            for dialogo in dialogos:
                campos = dialogo.locator("input, textarea, select, button, a, [role=button]")
                for i in range(campos.count()):
                    informe(f"   {_describir(campos.nth(i))}")
            for texto in ("captcha", "recaptcha", "no soy un robot"):
                if _visibles(page, lambda m, t=texto: m.get_by_text(t, exact=False)):
                    informe(f"   ATENCIÓN: hay un elemento con el texto «{texto}».")
            if _visibles(page, lambda m: m.locator("iframe[src*='captcha' i]")):
                informe("   ATENCIÓN: hay un iframe de CAPTCHA.")
        except PlaywrightError as exc:
            informe(f"\nError de Playwright: {type(exc).__name__}: {str(exc).splitlines()[0]}")
        finally:
            captura = SALIDA / f"exploracion-sicop-{sello}.png"
            try:
                page.screenshot(path=str(captura), full_page=True)
                informe(f"\nCaptura: {captura.relative_to(PROYECTO)}")
            except PlaywrightError:
                informe("\nNo se pudo guardar la captura.")
            input("\n>>> Revisa la ventana (no escribas el correo). Presiona Enter para cerrar el navegador... ")
            navegador.close()

    informe("\nPeticiones de red (método · servidor · ruta · tipo de recurso · estado · tipo de respuesta · veces):")
    for (metodo, servidor, ruta, recurso, estado, tipo), veces in sorted(peticiones.items()):
        informe(f"  {metodo} {servidor}{ruta} · {recurso} · {estado} · {tipo or '-'} · {veces}")
    informe("Resumidas (imágenes, fuentes, estilos):")
    for (servidor, recurso), veces in sorted(resumidas.items()):
        informe(f"  {servidor} · {recurso} · {veces}")

    archivo = SALIDA / f"exploracion-sicop-{sello}.txt"
    archivo.write_text("\n".join(informe.lineas) + "\n", encoding="utf-8")
    print(f"\nInforme guardado en {archivo.relative_to(PROYECTO)}")
    return 0


if __name__ == "__main__":
    sys.exit(explorar())
