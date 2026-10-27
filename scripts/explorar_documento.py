"""Exploración de la descarga de UN documento de la ficha (enriquecimiento, lección 3). SOLO EXPLORA.

Llega a la ficha con los mismos pasos que enrich (app/sources/sicop_tender_detail.py), con la ventana VISIBLE,
lista sus documentos y hace clic en UNO solo: el que se indica con su número (docFileSeqno) o, si no se indica, el
PDF más pequeño. Anota qué pasó al hacer clic:
* si hubo descarga, pestaña nueva o nada;
* las peticiones de red de después del clic: método, servidor, ruta, estado, tipo y tamaño de la respuesta (sin
  ?parámetros, sin cookies);
* del archivo descargado: nombre, tamaño, SHA-256 y si empieza con %PDF. No se abre con ningún programa.
Ante un CAPTCHA, un bloqueo o «No fue posible acceder a la página solicitada» se detiene y lo reporta.

Uso (una sola vez, mirando la ventana):
    .venv\\Scripts\\python.exe scripts\\explorar_documento.py 20261002859
    .venv\\Scripts\\python.exe scripts\\explorar_documento.py 20261002859 4
Todo queda en data/exports/exploracion-documento-AAAAMMDD-HHMMSS/ (fuera de Git): informe.txt, capturas y el
archivo descargado.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROYECTO))

from app.config import load_settings  # noqa: E402
from app.sources import sicop_tender_detail as std  # noqa: E402
from app.sources.sicop_browser import detectar_control  # noqa: E402

SALIDA = PROYECTO / "data" / "exports"
NRO_SICOP = re.compile(r"^\d{11}$")
ESPERA_DESCARGA_MS = 60_000
RECURSOS_RESUMIDOS = {"image", "font", "stylesheet", "media", "script"}
NOMBRE_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")
# El enlace de descarga lleva una clave temporal DENTRO de la ruta (/p/<clave>/, observado el 2026-10-27): no se anota.
CLAVE_EN_RUTA = re.compile(r"/p/[^/]+/")

DESCRIBIR = """e => ({
  etiqueta: e.tagName.toLowerCase(), rol: e.getAttribute('role') || '', href: e.getAttribute('href') || '',
  target: e.getAttribute('target') || '', clases: (e.className && e.className.baseVal === undefined) ? e.className : '',
  padre: e.parentElement ? e.parentElement.tagName.toLowerCase() + ' ' + (e.parentElement.className || '') : '',
  cursor: getComputedStyle(e).cursor
})"""


class Informe:
    def __init__(self) -> None:
        self.lineas: list[str] = []

    def __call__(self, texto: str = "") -> None:
        print(texto)
        self.lineas.append(texto)


def explorar(nro: str, seq: str | None) -> int:
    settings = load_settings()
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    carpeta = SALIDA / f"exploracion-documento-{sello}"
    carpeta.mkdir(parents=True, exist_ok=True)
    informe = Informe()
    escucha = std._Escucha()
    despues: list[str] = []
    paginas_nuevas: list = []
    descargas: list = []
    clic = {"hecho": False}

    def anotar(respuesta) -> None:
        if not clic["hecho"]:
            return
        pedido = respuesta.request
        if pedido.resource_type in RECURSOS_RESUMIDOS:
            return
        partes = urlsplit(pedido.url)  # sin ?parámetros
        tipo = (respuesta.headers.get("content-type") or "").split(";")[0]
        largo = respuesta.headers.get("content-length", "?")
        disp = "con content-disposition" if respuesta.headers.get("content-disposition") else ""
        ruta = CLAVE_EN_RUTA.sub("/p/(clave oculta)/", partes.path)
        despues.append(f"  {pedido.method} {partes.netloc}{ruta} · {pedido.resource_type} · "
                       f"{respuesta.status} · {tipo or '-'} · {largo} bytes {disp}".rstrip())

    informe(f"Exploración de la descarga de un documento · {datetime.now():%Y-%m-%d %H:%M} · Número SICOP {nro}")
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False, slow_mo=300)
        contexto = navegador.new_context(locale="es-CR", accept_downloads=True)
        contexto.on("response", escucha)
        contexto.on("response", anotar)
        contexto.on("page", lambda pg: paginas_nuevas.append(pg))
        page = contexto.new_page()
        page.on("download", lambda d: descargas.append(d))
        page.set_default_timeout(std.ESPERA_MS)
        try:
            textos = std._pasos(page, nro, escucha, lambda n: page.screenshot(path=str(carpeta / f"{n}.png")),
                                std.ESPERA_MS)
            documentos = json.loads(textos["documentos"])
            informe(f"\n1. Ficha abierta. Documentos: {len(documentos)}")
            for d in documentos:
                informe(f"   {d.get('docFileSeqno')} · {d.get('fileTypeNm')} · {d.get('clientFileNm')} · "
                        f"{d.get('fileSizeMb')} MB")
            if seq is None:
                pdfs = [d for d in documentos if str(d.get("clientFileNm", "")).lower().endswith(".pdf")]
                if not pdfs:
                    informe("\nNo hay PDF en esta ficha: indica el número del documento.")
                    return 1
                elegido = min(pdfs, key=lambda d: float(d.get("fileSizeMb") or 999))
            else:
                elegido = next((d for d in documentos if str(d.get("docFileSeqno")) == seq), None)
                if elegido is None:
                    informe(f"\nNo hay documento {seq}.")
                    return 1
            nombre = str(elegido["clientFileNm"])
            informe(f"\n2. Documento elegido: {elegido.get('docFileSeqno')} · {nombre} · {elegido.get('fileSizeMb')} MB")

            celdas = page.get_by_text(nombre, exact=True)
            informe(f"   Elementos con ese texto: {celdas.count()}")
            for i in range(min(celdas.count(), 5)):
                try:
                    informe(f"   · {celdas.nth(i).evaluate(DESCRIBIR)}")
                except PlaywrightError:
                    informe("   · (no se pudo leer)")
            visibles = [celdas.nth(i) for i in range(celdas.count()) if celdas.nth(i).is_visible()]
            if not visibles:
                informe("   No está a la vista: haz clic a mano en el nombre del documento en la ventana.")
                input(">>> Después del clic, presiona Enter aquí... ")
                clic["hecho"] = True
            else:
                visibles[-1].scroll_into_view_if_needed()
                page.screenshot(path=str(carpeta / "5-antes-del-clic.png"))
                clic["hecho"] = True
                visibles[-1].click()

            # 3. ¿Qué pasó? Se espera hasta 60 s una descarga o una pestaña nueva.
            limite = datetime.now().timestamp() + ESPERA_DESCARGA_MS / 1000
            while not descargas and not paginas_nuevas and datetime.now().timestamp() < limite:
                page.wait_for_timeout(500)
            page.wait_for_timeout(2000)
            motivo = detectar_control(page)
            for pg in paginas_nuevas:
                try:
                    pg.wait_for_load_state("domcontentloaded", timeout=15_000)
                except PlaywrightError:
                    pass
                partes = urlsplit(pg.url)
                informe(f"\n3. Se abrió una pestaña nueva: {partes.netloc}{partes.path} (sin parámetros) · "
                        f"título {pg.title()!r}")
                pg.screenshot(path=str(carpeta / "6-pestana-nueva.png"))
                motivo = motivo or detectar_control(pg)
            if motivo:
                informe(f"\nDETENIDO (no se reintenta ni se evita): {motivo}. Avisar a Oscar.")
            for d in descargas:
                destino = carpeta / ("descargado-" + NOMBRE_SEGURO.sub("_", d.suggested_filename)[:120])
                d.save_as(destino)
                datos = destino.read_bytes()
                informe(f"\n3. Hubo descarga: nombre sugerido {d.suggested_filename!r}")
                informe(f"   Tamaño {len(datos)} bytes · SHA-256 {hashlib.sha256(datos).hexdigest()}")
                informe(f"   ¿Empieza con %PDF? {'sí' if datos[:4] == b'%PDF' else 'NO'} · primeros bytes "
                        f"{datos[:8]!r}")
                informe(f"   Guardado en {destino.relative_to(PROYECTO)} (no se abrió)")
            if not descargas and not paginas_nuevas:
                informe("\n3. En 60 s no hubo descarga ni pestaña nueva (ver capturas y peticiones).")
        except std.FalloFicha as fallo:
            informe(f"\nNo se llegó a la ficha: {fallo.motivo}")
        except PlaywrightError as exc:
            informe(f"\nError de Playwright: {type(exc).__name__}: {str(exc).splitlines()[0]}")
        finally:
            try:
                page.screenshot(path=str(carpeta / "final.png"), full_page=True)
            except PlaywrightError:
                pass
            input("\n>>> Revisa la ventana. Presiona Enter para cerrar el navegador... ")
            navegador.close()

    informe("\nPeticiones después del clic (método · servidor · ruta · recurso · estado · tipo · tamaño):")
    for linea in despues:
        informe(linea)
    archivo = carpeta / "informe.txt"
    archivo.write_text("\n".join(informe.lineas) + "\n", encoding="utf-8")
    print(f"\nInforme guardado en {archivo.relative_to(PROYECTO)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or not NRO_SICOP.match(sys.argv[1]):
        sys.exit("Uso: python scripts\\explorar_documento.py NUMERO_SICOP [NUMERO_DE_DOCUMENTO]")
    sys.exit(explorar(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None))
