"""Capturas automáticas de las misiones: la app real con la base de EJEMPLO, el elemento resaltado en rojo.

1. Rehace la base de ejemplo (app/ayuda/ejemplo.py).
2. Arranca la app con esa base en un puerto libre de 127.0.0.1 (app/ayuda/servidor.py), con TODAS las claves de la
   configuración en el entorno: el .env real no influye.
3. Con Chromium sin ventana (1280 × 800), por cada marcador: abre la página, hace las acciones previas, busca el
   elemento, le pone un borde rojo y guarda la ventana en app/web/static/ayuda/<misión>/<paso>.png.
4. Escribe indice.json (misión, paso, imagen y texto alternativo) para la página de ayuda (lección 3).

Si un elemento ya no está (cambió un botón), sigue con los demás y al final devuelve la lista de errores, cada uno
con la misión, el paso y lo que no encontró.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from app.ayuda import CAPTURAS_DIR, CARPETA_EJEMPLO, PROJECT_ROOT, ejemplo, pantallas
from app.ayuda.misiones import Marcador

ANCHO, ALTO = 1280, 800
ESPERA_MS = 5000
ESTILO_MARCA = ("[data-ayuda]{outline:4px solid #E11D48 !important;outline-offset:3px !important;"
                "box-shadow:0 0 0 10px rgba(225,29,72,.22) !important;border-radius:6px}")

# Busca el elemento y lo marca con data-ayuda. Por texto: primero el texto exacto, luego «empieza con».
# Abre los <details> que lo contienen (sin abrir el desplegable cuyo título es el propio elemento).
_BUSCAR = """([texto, selector, contiene, enMenu, menu]) => {
  document.querySelectorAll('[data-ayuda]').forEach(e => e.removeAttribute('data-ayuda'));
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const raiz = enMenu ? document.querySelector(menu) : document.body;
  if (!raiz) return false;
  let el = null;
  if (selector) {
    let c = [...raiz.querySelectorAll(selector)];
    if (contiene) {
      c = c.filter(e => norm(e.textContent).includes(contiene));
      c.sort((a, b) => norm(a.textContent).length - norm(b.textContent).length);
    }
    el = c[0] || null;
  } else {
    const c = [...raiz.querySelectorAll('h1,h2,h3,summary,button,a,label,legend,dt,th,span,strong,small,p,td')];
    const t = norm(texto);
    el = c.find(e => norm(e.textContent) === t) || c.find(e => norm(e.textContent).startsWith(t)) || null;
  }
  if (!el) return false;
  let d = (el.tagName === 'SUMMARY' ? el.parentElement : el).parentElement;
  for (d = d && d.closest('details'); d; d = d.parentElement && d.parentElement.closest('details')) d.open = true;
  el.setAttribute('data-ayuda', '1');
  el.scrollIntoView({block: 'center', inline: 'nearest'});
  return true;
}"""


@dataclass
class Resultado:
    hechas: list[Marcador] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _arrancar(carpeta: Path, puerto: int) -> subprocess.Popen:
    """La app con la base de ejemplo. Del entorno del proceso solo se heredan las variables del sistema."""
    entorno = {k: v for k, v in os.environ.items() if k.upper() in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME",
                                                                    "USERPROFILE", "LOCALAPPDATA", "APPDATA")}
    entorno.update(ejemplo.entorno(carpeta))
    entorno["PYTHONIOENCODING"] = "utf-8"
    proceso = subprocess.Popen([sys.executable, "-m", "app.ayuda.servidor", str(carpeta), str(puerto)],
                               cwd=PROJECT_ROOT, env=entorno)
    limite = time.monotonic() + 30
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            raise RuntimeError("La app de ejemplo no arrancó (mira el error de arriba).")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/health", timeout=2):
                return proceso
        except OSError:
            time.sleep(0.3)
    proceso.terminate()
    raise RuntimeError("La app de ejemplo no respondió en 30 s.")


def _iniciar_sesion(contexto, base: str, claves: ejemplo.Claves) -> None:
    page = contexto.new_page()
    page.goto(f"{base}/login")
    page.fill("input[name=email]", claves.email)
    page.fill("input[name=contrasena]", claves.contrasena)
    page.click("button[type=submit]")
    page.wait_for_url(f"{base}/oportunidades**")
    page.close()


def _grabar_video(navegador, base: str, claves: ejemplo.Claves, carpeta: Path) -> None:
    """La grabación de la consulta con FALLO: un video corto y una captura del cartel de ejemplo."""
    dia, nro, hora = claves.grabacion.split("/")
    destino = carpeta / "grabaciones" / dia / nro
    destino.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / "video_temporal"
    contexto = navegador.new_context(viewport={"width": ANCHO, "height": ALTO}, locale="es-CR",
                                     record_video_dir=str(temporal), record_video_size={"width": 960, "height": 600})
    _iniciar_sesion(contexto, base, claves)
    page = contexto.new_page()
    page.goto(f"{base}/oportunidades/{nro}")
    page.wait_for_timeout(1500)
    page.screenshot(path=str(destino / f"{hora}-1-inicio.png"))
    page.mouse.wheel(0, 600)
    page.wait_for_timeout(1000)
    video = page.video
    contexto.close()
    shutil.move(video.path(), destino / f"{hora}-video.webm")
    shutil.rmtree(temporal, ignore_errors=True)


def _hacer_antes(page, acciones, base: str, subida) -> None:
    for accion, *datos in acciones:
        if accion == "click":
            page.click(datos[0])
            page.wait_for_load_state()
        elif accion == "elegir":
            page.select_option(datos[0], datos[1])
        elif accion == "subir":
            page.set_input_files(datos[0], str(subida()))
        elif accion == "ir":
            page.goto(base + datos[0])


def _capturar(contexto, m: Marcador, url: str, objetivo: pantallas.Objetivo, base: str, subida,
              salida: Path) -> str | None:
    """Toma la captura del marcador. Devuelve el error (texto) o None si salió bien."""
    page = contexto.new_page()
    try:
        page.goto(base + url)
        _hacer_antes(page, objetivo.antes, base, subida)
        try:
            page.wait_for_function(_BUSCAR, arg=[objetivo.texto, objetivo.selector, objetivo.contiene,
                                                 objetivo.en_menu, pantallas.MENU], timeout=ESPERA_MS)
        except Exception:  # noqa: BLE001 — TimeoutError de Playwright: el elemento no está
            return f"{m.donde}: no encontré {objetivo.describir()} en «{m.pantalla}» ({url})."
        # Un video sale en blanco hasta que carga: se espera su primer cuadro y se adelanta un segundo.
        page.wait_for_function("() => { const v = document.querySelector('[data-ayuda]');"
                               " return v.tagName !== 'VIDEO' || v.readyState >= 2; }", timeout=ESPERA_MS)
        page.evaluate("() => { const v = document.querySelector('[data-ayuda]');"
                      " if (v.tagName === 'VIDEO') v.currentTime = 1; }")
        page.wait_for_function("() => { const v = document.querySelector('[data-ayuda]');"
                               " return v.tagName !== 'VIDEO' || (!v.seeking && v.readyState >= 2); }",
                               timeout=ESPERA_MS)
        page.wait_for_timeout(300)
        page.add_style_tag(content=ESTILO_MARCA)
        page.wait_for_timeout(150)
        ruta = salida / m.imagen
        ruta.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(ruta))
        return None
    finally:
        page.close()


def _indice(salida: Path, hechas: list[Marcador], misiones: set[str]) -> None:
    archivo = salida / "indice.json"
    anteriores = []
    if archivo.is_file():
        anteriores = [x for x in json.loads(archivo.read_text(encoding="utf-8")) if x["mision"] not in misiones]
    nuevas = [{"mision": m.mision, "paso": m.paso, "orden": m.orden, "pantalla": m.pantalla,
               "imagen": m.imagen, "alt": m.alt} for m in hechas]
    todas = sorted(anteriores + nuevas, key=lambda x: (x["mision"], x["paso"], x["orden"]))
    archivo.write_text(json.dumps(todas, ensure_ascii=False, indent=1), encoding="utf-8")


def tomar(marcadores: list[Marcador], carpeta: Path = CARPETA_EJEMPLO, salida: Path = CAPTURAS_DIR,
          avisar=print) -> Resultado:
    """Rehace la base de ejemplo y toma las capturas de estos marcadores."""
    from playwright.sync_api import sync_playwright

    resultado = Resultado()
    trabajos = []
    for m in marcadores:
        try:
            trabajos.append((m, *pantallas.resolver(m)))
        except pantallas.SinObjetivo as exc:
            resultado.errores.append(str(exc))
    misiones = {m.mision for m in marcadores}
    for mision in misiones:
        shutil.rmtree(salida / mision, ignore_errors=True)
    salida.mkdir(parents=True, exist_ok=True)

    avisar("Creando la base de ejemplo…")
    claves = ejemplo.crear(carpeta)
    subidas = iter(range(1, 100))
    subida = lambda: ejemplo.subida_de_ejemplo(carpeta, next(subidas))  # noqa: E731 — un archivo nuevo cada vez
    datos = {"principal": claves.principal, "seguido": claves.seguido, "sin_encargado": claves.sin_encargado,
             "consulta": claves.consulta_grabacion}
    puerto = _puerto_libre()
    base = f"http://127.0.0.1:{puerto}"
    proceso = _arrancar(carpeta, puerto)
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            try:
                if any(m.pantalla == "Grabación" for m, *_ in trabajos):
                    _grabar_video(navegador, base, claves, carpeta)
                con_sesion = navegador.new_context(viewport={"width": ANCHO, "height": ALTO}, locale="es-CR")
                sin_sesion = navegador.new_context(viewport={"width": ANCHO, "height": ALTO}, locale="es-CR")
                _iniciar_sesion(con_sesion, base, claves)
                for n, (m, url, objetivo) in enumerate(trabajos, start=1):
                    contexto = sin_sesion if m.pantalla in pantallas.SIN_SESION else con_sesion
                    error = _capturar(contexto, m, url.format(**datos), objetivo, base, subida, salida)
                    if error:
                        resultado.errores.append(error)
                    else:
                        resultado.hechas.append(m)
                    if n % 20 == 0:
                        avisar(f"  {n} de {len(trabajos)}…")
            finally:
                navegador.close()
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)
    _indice(salida, resultado.hechas, misiones)
    return resultado
