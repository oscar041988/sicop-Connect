"""Servidor para las capturas: la app real con la base de EJEMPLO. Solo lo lanza app/ayuda/capturas.py.

Uso: python -m app.ayuda.servidor <carpeta_de_ejemplo> <puerto>   (el entorno lo pone capturas.py)

Dos páginas leen archivos reales fuera de la base; aquí se cambian por los de ejemplo:
* «Calidad de reglas» lee el golden set real (tests/golden/, con las etiquetas de Hermatix) → golden de ejemplo.
* «Competencia» lee config/competidores.yaml (nombres reales) → nombres de empresas de ejemplo.
Además agrega /ayuda-ejemplo/correo: el correo diario de ejemplo armado con la plantilla real del aviso.
"""

from __future__ import annotations

import functools
import html
import sys
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi.responses import HTMLResponse

from app import calidad, competencia
from app.ayuda import ejemplo
from app.main import app


def preparar(carpeta: Path) -> None:
    calidad.medir = functools.partial(calidad.medir, golden_dir=carpeta / "golden")
    competencia.cargar_competidores = lambda path=None: dict(ejemplo.COMPETIDORES)

    def correo() -> HTMLResponse:
        asunto, cuerpo = ejemplo.correo_de_ejemplo(carpeta, datetime.now(timezone.utc), "http://127.0.0.1:8000")
        return HTMLResponse(
            "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Correo de ejemplo</title></head>"
            "<body style='margin:0;background:#f1f3f4;font-family:Arial,sans-serif'>"
            "<div style='background:#fff;padding:16px 24px;border-bottom:1px solid #ddd'>"
            "<p style='margin:0;color:#5f6368;font-size:13px'>De: SICOP Connect · Para: equipo@ejemplo.test</p>"
            f"<h2 class='asunto' style='margin:6px 0 0;font-size:20px;font-weight:normal'>{html.escape(asunto)}</h2>"
            f"</div><div style='padding:16px 24px'>{cuerpo}</div></body></html>")

    app.get("/ayuda-ejemplo/correo", response_class=HTMLResponse)(correo)


def main(argv: list[str]) -> None:
    carpeta, puerto = Path(argv[0]), int(argv[1])
    preparar(carpeta)
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_level="warning")


if __name__ == "__main__":
    main(sys.argv[1:])
