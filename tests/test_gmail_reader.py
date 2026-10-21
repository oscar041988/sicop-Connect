"""Lector de Gmail de solo lectura (obtención automática, lección 1) con un Gmail SIMULADO: nunca se conecta a
Google. Los correos son los fixtures SIMULADOS tests/fixtures/correo_*_simulado.eml (ver su README)."""

import base64
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import requests

from app.cli import main
from app.config import load_settings
from app.importers.comun import HORA_CR
from app.sources import gmail_reader as gr
from app.sources.gmail_reader import CorreoNoLlego, FormatoDesconocido, GmailError

FIXTURES = Path(__file__).parent / "fixtures"
CODIGO_EML = (FIXTURES / "correo_codigo_simulado.eml").read_bytes()
ENLACE_EML = (FIXTURES / "correo_envio_simulado.eml").read_bytes()
CODIGO = "Zq9Xw4"
ENLACE = "https://www.sicop.go.cr/app/module/bid/public/ext-report-download?processId=99999"
BUZON = "licitaciones@ejemplo.test"

SOLICITUD = datetime(2026, 10, 21, 13, 33, tzinfo=HORA_CR)  # hora de la solicitud en SICOP


def _ms(minutos_despues: int) -> str:
    """internalDate de Gmail (milisegundos) a tantos minutos de la solicitud."""
    return str(int((SOLICITUD + timedelta(minutes=minutos_despues)).timestamp() * 1000))


class _Respuesta:
    def __init__(self, status, cuerpo=None):
        self.status_code, self._cuerpo = status, cuerpo

    def json(self):
        if self._cuerpo is None:
            raise ValueError("sin JSON")
        return self._cuerpo


class _GmailSimulado:
    """SIMULADO: un buzón con correos {id: (minutos después de la solicitud, bytes del .eml)}.

    La búsqueda devuelve todos los correos (como si Gmail no filtrara): así se prueba que el lector vuelve a
    comprobar remitente, asunto y hora. Solo tiene get(): si el lector intentara cambiar algo, fallaría."""

    def __init__(self, correos=None, error=None):
        self.correos, self.error, self.peticiones = correos or {}, error, []

    def get(self, url, params, timeout):
        self.peticiones.append((url, dict(params)))
        if self.error is not None:
            if isinstance(self.error, Exception):
                raise self.error
            return _Respuesta(self.error, {"error": {"message": "SIMULADO"}})
        if url == gr.URL_MENSAJES:
            return _Respuesta(200, {"messages": [{"id": i} for i in self.correos]} if self.correos else {})
        minutos, eml = self.correos[url.rsplit("/", 1)[1]]
        raw = base64.urlsafe_b64encode(eml).decode("ascii")
        return _Respuesta(200, {"id": "x", "internalDate": _ms(minutos), "raw": raw})


def _lector(correos=None, error=None):
    sesion = _GmailSimulado(correos, error)
    return gr.LectorGmail(credenciales=None, session=sesion), sesion


def _cambiar(eml: bytes, viejo: str, nuevo: str) -> bytes:
    assert viejo.encode() in eml
    return eml.replace(viejo.encode(), nuevo.encode())


# --- Extraer código y enlace ------------------------------------------------------------------------------

def test_extrae_el_codigo_decodificando_el_quoted_printable():
    lector, _ = _lector({"a": (1, CODIGO_EML)})
    correo = lector.buscar_codigo(SOLICITUD)
    assert correo.valor == CODIGO
    assert correo.tipo == "codigo"
    assert correo.recibido == SOLICITUD + timedelta(minutes=1)


def test_extrae_el_enlace_de_descarga():
    lector, _ = _lector({"b": (3, ENLACE_EML)})
    assert lector.buscar_enlace(SOLICITUD).valor == ENLACE


def test_cada_busqueda_solo_toma_su_asunto():
    lector, _ = _lector({"a": (1, CODIGO_EML), "b": (3, ENLACE_EML)})
    assert lector.buscar_codigo(SOLICITUD).valor == CODIGO
    assert lector.buscar_enlace(SOLICITUD).valor == ENLACE


# --- Qué correos sirven -----------------------------------------------------------------------------------

@pytest.mark.parametrize("remitente", [
    "SICOP <info@sicop.go.cr.otro.test>",
    "SICOP <info@otro.test>",
    "info@sicop.go.cr <falso@otro.test>",
])
def test_ignora_correos_de_otros_remitentes(remitente):
    falso = _cambiar(CODIGO_EML, "From: SICOP <info@sicop.go.cr>", f"From: {remitente}")
    lector, _ = _lector({"f": (2, falso)})
    with pytest.raises(CorreoNoLlego):
        lector.buscar_codigo(SOLICITUD)


def test_ignora_un_asunto_parecido():
    otro = _cambiar(CODIGO_EML, "=?UTF-8?Q?C=C3=B3digo_verificaci=C3=B3n_para_reporte?=", "Codigo de prueba")
    lector, _ = _lector({"o": (2, otro)})
    with pytest.raises(CorreoNoLlego):
        lector.buscar_codigo(SOLICITUD)


def test_ignora_correos_anteriores_a_la_solicitud():
    lector, _ = _lector({"viejo": (-5, CODIGO_EML)})
    with pytest.raises(CorreoNoLlego, match="Todavía no llegó"):
        lector.buscar_codigo(SOLICITUD)


def test_con_dos_codigos_usa_el_mas_reciente():
    nuevo = _cambiar(CODIGO_EML, CODIGO, "Nu3voA")
    lector, _ = _lector({"primero": (1, CODIGO_EML), "segundo": (5, nuevo)})
    assert lector.buscar_codigo(SOLICITUD).valor == "Nu3voA"


# --- «No llegó» no es lo mismo que «formato desconocido» --------------------------------------------------

def test_sin_correos_es_correo_no_llego():
    lector, _ = _lector({})
    with pytest.raises(CorreoNoLlego):
        lector.buscar_enlace(SOLICITUD)


def test_codigo_con_otro_texto_es_formato_desconocido():
    raro = _cambiar(CODIGO_EML, "<strong>Zq9Xw4</strong>", "Zq9Xw4")
    lector, _ = _lector({"r": (1, raro)})
    with pytest.raises(FormatoDesconocido, match="formato es desconocido"):
        lector.buscar_codigo(SOLICITUD)


def test_enlace_a_otro_dominio_es_formato_desconocido():
    raro = _cambiar(ENLACE_EML, "https://www.sicop.go.cr/", "https://www.sicop.go.cr.otro.test/")
    lector, _ = _lector({"r": (3, raro)})
    with pytest.raises(FormatoDesconocido):
        lector.buscar_enlace(SOLICITUD)


def test_si_el_mas_reciente_no_se_entiende_no_usa_uno_anterior():
    raro = _cambiar(CODIGO_EML, "<strong>Zq9Xw4</strong>", "sin codigo")
    lector, _ = _lector({"bueno_viejo": (1, CODIGO_EML), "raro_nuevo": (4, raro)})
    with pytest.raises(FormatoDesconocido):
        lector.buscar_codigo(SOLICITUD)


def test_los_errores_no_muestran_el_codigo_ni_el_id():
    raro = _cambiar(CODIGO_EML, "<strong>Zq9Xw4</strong>", "Zq9Xw4")
    lector, _ = _lector({"id-secreto": (1, raro)})
    with pytest.raises(FormatoDesconocido) as exc:
        lector.buscar_codigo(SOLICITUD)
    assert CODIGO not in str(exc.value) and "id-secreto" not in str(exc.value)
    correo = _lector({"id-secreto": (1, CODIGO_EML)})[0].buscar_codigo(SOLICITUD)
    assert CODIGO not in repr(correo) and "id-secreto" not in repr(correo)


# --- Solo lectura y consulta ------------------------------------------------------------------------------

def test_la_consulta_filtra_por_remitente_asunto_y_hora_y_solo_hace_get():
    lector, sesion = _lector({"a": (1, CODIGO_EML)})
    lector.buscar_codigo(SOLICITUD)
    url, params = sesion.peticiones[0]
    assert url == gr.URL_MENSAJES
    assert params["q"] == (f'from:info@sicop.go.cr subject:"Código verificación para reporte" '
                           f'after:{int(SOLICITUD.timestamp())}')
    assert sesion.peticiones[1] == (f"{gr.URL_MENSAJES}/a", {"format": "raw"})
    assert all(u.startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages") for u, _ in sesion.peticiones)
    assert not hasattr(lector, "enviar") and not hasattr(sesion, "post")


@pytest.mark.parametrize("error, texto", [
    (403, "HTTP 403"),
    (500, "HTTP 500"),
    (requests.Timeout(), "no respondió"),
    (requests.ConnectionError(), "No se pudo conectar"),
])
def test_los_fallos_de_gmail_son_gmailerror(error, texto):
    lector, _ = _lector(error=error)
    with pytest.raises(GmailError, match=texto):
        lector.buscar_codigo(SOLICITUD)


def test_hora_sin_zona_horaria_no_se_acepta():
    lector, _ = _lector({})
    with pytest.raises(ValueError, match="zona horaria"):
        lector.buscar_codigo(datetime(2026, 10, 21, 13, 33))


def test_enmascarar():
    assert gr.enmascarar_codigo(CODIGO) == "Zq****"
    assert gr.enmascarar_enlace(ENLACE) == "processId=99***"
    assert gr.enmascarar_enlace("https://otro.test/") == "enlace ****"


# --- Autorización de lectura (flujo SIMULADO) ------------------------------------------------------------

class _Credenciales:
    def __init__(self, email):
        from tests.test_gmail import _id_token
        self.id_token = _id_token(email)

    def to_json(self):
        return '{"token": "SIMULADO-LECTURA"}'


class _FlujoSimulado:
    def __init__(self, email):
        self.email, self.kwargs = email, None

    def run_local_server(self, **kwargs):
        self.kwargs = kwargs
        return _Credenciales(self.email)


def _settings(tmp_path, **extra):
    cliente = tmp_path / "cliente.json"
    cliente.write_text("{}", encoding="utf-8")
    valores = {"DATABASE_PATH": str(tmp_path / "x.db"), "GOOGLE_CLIENT_FILE": str(cliente),
               "GOOGLE_TOKEN_FILE": str(tmp_path / "token_enviar.json"),
               "GOOGLE_READ_TOKEN_FILE": str(tmp_path / "token_leer.json"), "SICOP_REQUEST_EMAIL": BUZON}
    valores.update(extra)
    return load_settings(env_file=None, environ=valores)


def test_el_permiso_de_lectura_es_solo_gmail_readonly():
    assert gr.PERMISO_LEER.scopes == ["https://www.googleapis.com/auth/gmail.readonly", "openid",
                                      "https://www.googleapis.com/auth/userinfo.email"]
    assert not any("send" in s or "modify" in s or s.endswith("mail.google.com/") for s in gr.PERMISO_LEER.scopes)


def test_autorizar_lectura_guarda_su_propio_token(tmp_path):
    settings = _settings(tmp_path)
    flujo = _FlujoSimulado("Licitaciones@Ejemplo.test")
    assert gr.autorizar(settings, flujo=flujo) == BUZON
    assert (tmp_path / "token_leer.json").read_text(encoding="utf-8") == '{"token": "SIMULADO-LECTURA"}'
    assert not (tmp_path / "token_enviar.json").exists()
    assert flujo.kwargs["login_hint"] == BUZON


def test_autorizar_lectura_con_otra_cuenta_no_guarda_nada(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(GmailError, match="pero SICOP_REQUEST_EMAIL es"):
        gr.autorizar(settings, flujo=_FlujoSimulado("oscar@ejemplo.test"))
    assert not (tmp_path / "token_leer.json").exists()


def test_el_token_de_lectura_no_puede_ser_el_de_enviar(tmp_path):
    mismo = str(tmp_path / "token.json")
    settings = _settings(tmp_path, GOOGLE_TOKEN_FILE=mismo, GOOGLE_READ_TOKEN_FILE=mismo)
    with pytest.raises(GmailError, match="otro archivo"):
        gr.autorizar(settings, flujo=_FlujoSimulado(BUZON))
    with pytest.raises(GmailError, match="otro archivo"):
        gr.crear_lector(settings)


def test_sin_token_de_lectura_el_lector_lo_dice(tmp_path):
    with pytest.raises(GmailError, match="obtain gmail-auth"):
        gr.crear_lector(_settings(tmp_path))
    with pytest.raises(GmailError, match="Falta GOOGLE_READ_TOKEN_FILE"):
        gr.crear_lector(_settings(tmp_path, GOOGLE_READ_TOKEN_FILE=""))


# --- Comandos ---------------------------------------------------------------------------------------------

def test_check_mail_muestra_todo_enmascarado(tmp_path, monkeypatch, capsys):
    raro = _cambiar(ENLACE_EML, 'href="https://www.sicop.go.cr/', 'href="https://otro.test/')
    lector, _ = _lector({"a": (1, CODIGO_EML), "b": (3, ENLACE_EML), "c": (6, raro)})
    real = lector.listar_recientes
    monkeypatch.setattr(lector, "listar_recientes", lambda dias: real(dias, ahora=SOLICITUD + timedelta(hours=1)))
    monkeypatch.setattr("app.cli._crear_lector", lambda settings: lector)

    assert main(["obtain", "check-mail"], _settings(tmp_path)) == 0
    salida = capsys.readouterr().out
    assert "de los últimos 3 días (solo lectura): 3" in salida
    assert "2026-10-21 13:34 · Código verificación para reporte · código Zq****" in salida
    assert "2026-10-21 13:36 · Envío de reporte · enlace processId=99***" in salida
    assert "13:39 · Envío de reporte · FORMATO DESCONOCIDO" in salida
    assert CODIGO not in salida and "99999" not in salida and "otro.test" not in salida


def test_check_mail_sin_token_falla_sin_leer(tmp_path, capsys):
    assert main(["obtain", "check-mail"], _settings(tmp_path)) == 1
    assert "No se leyó nada" in capsys.readouterr().err


def test_check_mail_rechaza_dias_fuera_de_rango(tmp_path, capsys):
    assert main(["obtain", "check-mail", "--dias", "0"], _settings(tmp_path)) == 1
    assert "--dias" in capsys.readouterr().err


def test_gmail_auth_por_comando(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(gr, "autorizar", lambda settings: BUZON)
    assert main(["obtain", "gmail-auth"], _settings(tmp_path)) == 0
    assert "LEER (no enviar ni borrar)" in capsys.readouterr().out


def test_doctor_muestra_la_lectura_sin_valores(tmp_path, capsys):
    token = tmp_path / "token_leer.json"
    token.write_text('{"refresh_token": "SECRETO-SIMULADO"}', encoding="utf-8")
    assert main(["doctor"], _settings(tmp_path)) == 0
    salida = capsys.readouterr().out
    assert "Gmail lectura: archivo del cliente existe · token de lectura existe" in salida
    linea = next(l for l in salida.splitlines() if "SICOP_REQUEST_EMAIL" in l)
    assert linea.split() == ["SICOP_REQUEST_EMAIL", "configurado", "(oculto)"]
    assert BUZON not in salida and "SECRETO-SIMULADO" not in salida
