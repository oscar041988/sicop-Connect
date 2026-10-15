import pytest

from app.main import app
from app.web.intentos import LimiteIntentos


@pytest.fixture(autouse=True)
def intentos_de_login_en_cero():
    """Cada prueba empieza sin intentos de login fallidos (el contador vive en la app compartida)."""
    app.state.intentos = LimiteIntentos()
