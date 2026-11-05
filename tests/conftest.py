import pytest

from app.main import app
from app.web.intentos import LimiteIntentos


@pytest.fixture(autouse=True)
def intentos_de_login_en_cero():
    """Cada prueba empieza sin intentos de login fallidos (el contador vive en la app compartida)."""
    app.state.intentos = LimiteIntentos()


@pytest.fixture(autouse=True)
def asistente_encendido(monkeypatch):
    """Las pruebas usan el asistente encendido sin depender del .env (ASSISTANT_ENABLED viene en false por
    defecto, lección 5). Las que prueban el apagado lo cambian con monkeypatch."""
    monkeypatch.setenv("ASSISTANT_ENABLED", "true")
