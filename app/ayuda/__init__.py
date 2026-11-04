"""Ayuda de la app (lección 2 de la ayuda): base de EJEMPLO y capturas automáticas de las misiones.

Todo lo que se muestra en las capturas es inventado y marcado «EJEMPLO»: nunca se usa la base real (data/sicop.db),
sus documentos ni sus usuarios.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MISIONES_DIR = PROJECT_ROOT / "docs" / "ayuda" / "misiones"
CARPETA_EJEMPLO = PROJECT_ROOT / "data" / "ayuda_ejemplo"
CAPTURAS_DIR = PROJECT_ROOT / "app" / "web" / "static" / "ayuda"
