from fastapi.testclient import TestClient

from app.cli import main
from app.config import load_settings
from app.main import app


def test_health_responde_200_sin_secretos():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "ok"
    assert body["database"]["status"] in {"ok", "pendiente", "error"}
    assert "SESSION_SECRET" not in response.text


def test_doctor_oculta_secretos_y_marca_pendientes(tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("SESSION_SECRET=valor-super-secreto\nAPP_ENV=desde-archivo\n", encoding="utf-8")
    # Las variables del proceso tienen prioridad sobre el archivo .env.
    settings = load_settings(env_file=env_file, environ={"APP_ENV": "desde-proceso"})

    assert main(["doctor"], settings=settings) == 0

    salida = capsys.readouterr().out
    assert "valor-super-secreto" not in salida
    assert "configurado (oculto)" in salida
    assert "desde-proceso" in salida
    assert "MAIL_FROM" in salida and "PENDIENTE" in salida


def test_doctor_no_pide_mail_to_e_ignora_uno_viejo(tmp_path, capsys):
    # MAIL_TO se reemplazó por los destinatarios del panel (lección 7). Un .env o app.env viejo que todavía
    # lo tenga no debe fallar ni hacer que doctor lo muestre o lo pida.
    env_file = tmp_path / ".env"
    env_file.write_text("MAIL_TO=alguien@hermatix.com\n", encoding="utf-8")
    settings = load_settings(env_file=env_file, environ={})

    assert main(["doctor"], settings=settings) == 0

    salida = capsys.readouterr().out
    assert "MAIL_TO" not in salida
    assert "alguien@hermatix.com" not in salida
