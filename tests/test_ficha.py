"""Ficha del concurso (enriquecimiento, lección 2) con SICOP SIMULADO.

Corre un Chromium real sin ventana, pero context.route responde la consulta de concursos con la página SIMULADA
tests/fixtures/sicop_concursos_simulado.html y sus fetch a prod-api con las respuestas SIMULADAS de
tests/fixtures/ficha_simulada/ (los 3 carteles de la lección 1, sin datos de personas). Cualquier otra petición se
corta: nunca sale a internet. Si Chromium no está instalado, estas pruebas se saltan."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app import cli
from app.config import load_settings
from app.database import apply_migrations
from app.importers.comun import HORA_CR
from app.sources import sicop_tender_detail as std


def _chromium_instalado() -> bool:
    try:
        with std.sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _chromium_instalado(),
                                reason="Chromium de Playwright no instalado: python -m playwright install chromium")

FIXTURES = Path(__file__).parent / "fixtures"
PLANTILLA = (FIXTURES / "sicop_concursos_simulado.html").read_text(encoding="utf-8")
GPS, ABARROTES, SANTA_ANA = "20261002859", "20261001258", "20261001587"
CIERRES_EN_LA_BASE = {GPS: "2026-10-28T09:00:00-06:00", ABARROTES: "2026-11-09T08:30:00-06:00",
                      SANTA_ANA: "2026-10-23T23:59:00-06:00"}  # Santa Ana: el dato viejo de los datos abiertos
HORA = datetime(2026, 10, 27, 9, 0, tzinfo=HORA_CR)
ESPERA_MS = 3000
PERSONAS = ("executorNm", "executorId", "StaffNm", "StaffId", "writerNm", "writerId", "userId", "staffNm",
            "cartelSupNm", "PERSONA SIMULADA")


def _original(nro: str, nombre: str) -> str:
    return (FIXTURES / "ficha_simulada" / nro / f"{nombre}.json").read_text(encoding="utf-8")


def _cambiar(nro: str, nombre: str, **campos) -> str:
    """La respuesta SIMULADA con algunos campos cambiados (en la ficha o en el primer resultado de la búsqueda)."""
    datos = json.loads(_original(nro, nombre))
    destino = datos["content"][0] if nombre == "busqueda" else datos
    destino.update(campos)
    return json.dumps(datos, ensure_ascii=False)


class _Sicop:
    """SIMULADO: sirve la página y responde los fetch con las fichas de tests/fixtures/ficha_simulada/.
    cambios = {nro: {respuesta: texto}} reemplaza una respuesta; estados = {respuesta: código HTTP}."""

    def __init__(self, variante="normal", cambios=None, estados=None, archivos=None):
        """archivos = {serverFileNm: bytes o código HTTP}: lo que responde el almacén de documentos (lección 3)."""
        self.variante, self.cambios, self.estados = variante, cambios or {}, estados or {}
        self.archivos = archivos or {}
        self.nro, self.peticiones, self.busquedas, self.pedidos_al_almacen = None, [], [], []

    def cuerpo(self, nombre):
        if nombre is None:
            return "[]"  # funcionarios u otras: la app no las guarda
        if nombre == "busqueda" and not self.nro:
            return json.dumps({"content": []})  # como SICOP: sin «Número de SICOP» no aparece el cartel
        return self.cambios.get(self.nro, {}).get(nombre) or _original(self.nro, nombre)

    def __call__(self, contexto):
        html = PLANTILLA.replace("__VARIANTE__", self.variante)

        def manejar(route):
            url = route.request.url
            self.peticiones.append(url)
            partes = urlsplit(url)
            if url == std.URL:
                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
            elif partes.netloc == std.API:
                nombre = next((n for n, ruta in std.RUTAS.items() if ruta == partes.path), None)
                if nombre == "busqueda":
                    casillas = json.loads(route.request.post_data)
                    self.busquedas.append(casillas)
                    self.nro = casillas["cartelNo"]
                route.fulfill(status=self.estados.get(nombre, 200), body=self.cuerpo(nombre),
                              headers={"content-type": "application/json", "access-control-allow-origin": "*"})
            elif partes.netloc == "objectstorage.us-ashburn-1.oraclecloud.com":
                archivo = partes.path.rsplit("/", 1)[-1]
                self.pedidos_al_almacen.append(archivo)
                contenido = self.archivos.get(archivo, 404)
                route.fulfill(status=contenido if isinstance(contenido, int) else 200,
                              body=b"" if isinstance(contenido, int) else contenido,
                              headers={"content-type": "application/octet-stream", "access-control-allow-origin": "*",
                                       "content-disposition": f'attachment; filename="{archivo}"'})
            else:
                route.abort()
        contexto.route("**/*", manejar)


def _settings(tmp_path, nros=(GPS, ABARROTES, SANTA_ANA), **extra):
    db = tmp_path / "sicop.db"
    apply_migrations(db)
    with closing(sqlite3.connect(db)) as conn, conn:
        for nro in nros:
            conn.execute("INSERT INTO tenders (nro_sicop, fecha_cierre_recepcion, content_hash, first_seen, last_seen)"
                         " VALUES (?, ?, 'h', '2026-10-27', '2026-10-27')", (nro, CIERRES_EN_LA_BASE.get(nro)))
    valores = {"DATABASE_PATH": str(db), "EXPORTS_DIR": str(tmp_path / "exports"),
               "RECORDINGS_DIR": str(tmp_path / "grabaciones"), "DOCUMENTS_DIR": str(tmp_path / "documentos"),
               "BROWSER_HEADLESS": "true"}  # todas las carpetas en tmp_path: nunca en data/ del proyecto
    valores.update(extra)
    return load_settings(env_file=None, environ=valores)


class _Pausas:
    def __init__(self):
        self.segundos = []

    def __call__(self, s):
        self.segundos.append(s)


def _enriquecer(settings, nros, sicop=None, dormir=None):
    return std.enriquecer(settings, list(nros), dormir=dormir or _Pausas(), reloj=lambda: HORA,
                          preparar_contexto=sicop or _Sicop(), espera_ms=ESPERA_MS)


def _fichas(settings):
    with closing(sqlite3.connect(settings.database_path)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(f) for f in conn.execute("SELECT * FROM tender_details ORDER BY id")]


# --- Los 3 carteles de la lección 1 ----------------------------------------------------------------------------

ESPERADO = {
    GPS: {"estado_concurso": "En recepción de ofertas", "modificado": "N", "secuencia": "00",
          "numero_procedimiento": "2026LD-000031-0018000001", "tipo_modalidad": "Según demanda",
          "inicio_recepcion": "2026-10-21T17:00:00-06:00", "cierre_recepcion": "2026-10-28T09:00:00-06:00",
          "limite_aclaraciones": "2026-10-22T23:59:00-06:00", "monto_estimado": "291782.16", "moneda_monto": "CRC",
          "monto_estimado_usd": None, "lineas_total": 1},
    ABARROTES: {"estado_concurso": "Objetado", "tipo_modalidad": "Convenio marco", "monto_estimado": None,
                "moneda_monto": None, "lineas_total": 432, "cierre_recepcion": "2026-11-09T08:30:00-06:00"},
    SANTA_ANA: {"estado_concurso": "En recepción de ofertas", "modificado": "Y", "version_pliego": "2610202684644",
                "cierre_recepcion": "2026-10-30T23:59:00-06:00", "monto_estimado": "652190", "moneda_monto": "CRC"},
}
DOCUMENTOS = {GPS: 5, ABARROTES: 49, SANTA_ANA: 7}


@pytest.mark.parametrize("nro", [GPS, ABARROTES, SANTA_ANA])
def test_extrae_los_campos_de_las_3_fichas(tmp_path, nro):
    settings = _settings(tmp_path)

    (consulta,) = _enriquecer(settings, [nro])

    assert consulta.resultado == "nueva", consulta.motivo
    (fila,) = _fichas(settings)
    assert fila["nro_sicop"] == nro and len(fila["content_hash"]) == 64
    assert {k: fila[k] for k in ESPERADO[nro]} == ESPERADO[nro]
    assert len(json.loads(fila["documentos"])) == DOCUMENTOS[nro]
    assert json.loads(fila["copia_fiel"])["ficha"]["cartelNo"] == nro
    # Grabación: video y una captura por paso.
    carpeta = settings.recordings_dir / "2026-10-27" / nro
    nombres = sorted(p.name for p in carpeta.iterdir())
    assert "090000-video.webm" in nombres and "090000-4-ficha.png" in nombres


def test_el_numero_va_en_la_casilla_numero_de_sicop(tmp_path):
    """Prueba real del 2026-10-27: con la etiqueta flotante (va DESPUÉS de su casilla), el número quedó en «Código
    de clasificación» y SICOP no encontró nada."""
    settings = _settings(tmp_path)
    sicop = _Sicop()

    (consulta,) = _enriquecer(settings, [GPS], sicop)

    assert sicop.busquedas == [{"instCartelNo": "", "cartelNo": GPS, "identi": ""}]
    assert consulta.resultado == "nueva", consulta.motivo


def test_no_guarda_datos_de_personas(tmp_path):
    settings = _settings(tmp_path)
    sicop = _Sicop(cambios={GPS: {"ficha": _cambiar(GPS, "ficha", executorNm="FUNCIONARIA SIMULADA",
                                                   writerId="X1", poqStaffNm="OTRA PERSONA")}})

    _enriquecer(settings, [GPS], sicop)

    (fila,) = _fichas(settings)
    quitados = set(json.loads(fila.pop("campos_quitados")))  # solo los NOMBRES de los campos quitados
    texto = json.dumps(fila, ensure_ascii=False)
    assert not [p for p in PERSONAS if p in texto]
    assert "FUNCIONARIA SIMULADA" not in texto and "OTRA PERSONA" not in texto
    assert {"executorNm", "writerId", "poqStaffNm"} <= quitados


def test_la_cierre_distinto_de_la_base_se_avisa_en_la_terminal(tmp_path, monkeypatch, capsys):
    """El caso real de Santa Ana: los datos abiertos dicen 23/10, la ficha modificada dice 30/10."""
    settings = _settings(tmp_path)
    monkeypatch.setattr(cli, "_opciones_enrich",
                        lambda: {"preparar_contexto": _Sicop(), "espera_ms": ESPERA_MS, "dormir": _Pausas()})

    codigo = cli.main(["enrich", "--nro", SANTA_ANA], settings=settings)

    salida = capsys.readouterr().out
    assert codigo == 0
    assert "NUEVA versión guardada" in salida and "Cierre de recepción: 30/10/2026 23:59" in salida
    assert "ATENCIÓN: en los datos abiertos el cierre es 23/10/2026 23:59" in salida


# --- Versiones ----------------------------------------------------------------------------------------------

def test_misma_ficha_dos_veces_es_una_sola_fila(tmp_path):
    settings = _settings(tmp_path)

    primera = _enriquecer(settings, [GPS])[0]
    segunda = _enriquecer(settings, [GPS])[0]

    assert (primera.resultado, segunda.resultado) == ("nueva", "sin_cambios")
    assert segunda.guardado.detalle_id == primera.guardado.detalle_id
    assert len(_fichas(settings)) == 1


def test_lo_que_cambia_solo_con_el_reloj_no_crea_otra_version(tmp_path):
    settings = _settings(tmp_path)
    _enriquecer(settings, [GPS])

    despues = _Sicop(cambios={GPS: {"ficha": _cambiar(GPS, "ficha", startPassYn=1, endPassYn=1, openbidPassYn=1,
                                                      biddocEndDtEndYn="N")}})
    (consulta,) = _enriquecer(settings, [GPS], despues)

    assert consulta.resultado == "sin_cambios"
    assert len(_fichas(settings)) == 1


def test_ficha_modificada_es_otra_version_y_la_anterior_no_se_toca(tmp_path):
    settings = _settings(tmp_path)
    _enriquecer(settings, [GPS])
    (antes,) = _fichas(settings)

    modificada = _Sicop(cambios={GPS: {"ficha": _cambiar(GPS, "ficha", cartelModYn="Y", cartelVersion="30102026090000",
                                                         biddocEndDt="2026-11-04T09:00:00")}})
    (consulta,) = _enriquecer(settings, [GPS], modificada)

    assert consulta.resultado == "nueva" and consulta.guardado.versiones == 2
    vieja, nueva = _fichas(settings)
    assert vieja == antes
    assert (nueva["modificado"], nueva["cierre_recepcion"]) == ("Y", "2026-11-04T09:00:00-06:00")


def test_las_fichas_no_se_modifican_ni_se_borran(tmp_path):
    settings = _settings(tmp_path)
    _enriquecer(settings, [GPS])
    with closing(sqlite3.connect(settings.database_path)) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="no se modifican"):
            conn.execute("UPDATE tender_details SET estado_concurso = 'otro'")
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM tender_details")


def test_migrate_dos_veces_no_cambia_nada(tmp_path):
    db = tmp_path / "sicop.db"
    assert "0018_fichas.sql" in apply_migrations(db)
    assert apply_migrations(db) == []


# --- Fallos -------------------------------------------------------------------------------------------------

FALLOS = {
    "no_encontrado": ({"busqueda": json.dumps({"content": []})}, "no encontró el cartel"),
    "dos_resultados": ({"busqueda": json.dumps({"content": [json.loads(_original(GPS, "busqueda"))["content"][0]] * 2})},
                       "trajo 2 resultados"),
    "otro_cartel_en_la_busqueda": ({"busqueda": _cambiar(GPS, "busqueda", cartelNo="20269999999")}, "trajo otro cartel"),
    "ficha_de_otro_cartel": ({"ficha": _cambiar(GPS, "ficha", cartelNo="20269999999")}, "es de otro cartel"),
    "estructura_cambiada": ({"ficha": json.dumps({"cartelNo": GPS})}, "le faltan campos"),
    "no_es_json": ({"ficha": "<html>mantenimiento</html>"}, "no es JSON"),
    "fecha_con_otro_formato": ({"ficha": _cambiar(GPS, "ficha", biddocEndDt="28/10/2026 09:00")}, "otro formato"),
}


@pytest.mark.parametrize("caso", FALLOS)
def test_cada_fallo_da_su_fallo_con_captura_y_no_guarda_nada(tmp_path, caso):
    cambios, mensaje = FALLOS[caso]
    settings = _settings(tmp_path)

    (consulta,) = _enriquecer(settings, [GPS], _Sicop(cambios={GPS: cambios}))

    assert consulta.resultado == "fallo"
    assert mensaje in consulta.motivo
    assert _fichas(settings) == []
    assert list(settings.exports_dir.glob(f"ficha-fallo-*-{GPS}.png"))


def test_si_la_pagina_cambio_es_fallo_del_paso(tmp_path):
    settings = _settings(tmp_path)

    (consulta,) = _enriquecer(settings, [GPS], _Sicop("sin_avanzada"))

    assert consulta.resultado == "fallo"
    assert "Paso «abrir «Búsqueda avanzada»»" in consulta.motivo


@pytest.mark.parametrize("variante,estados,detalle", [
    ("captcha", {}, "CAPTCHA"),
    ("bloqueo", {}, "ID de soporte de SICOP: 0123456789abcdef"),
    ("captcha_en_ficha", {}, "CAPTCHA"),
    ("normal", {"ficha": 403}, "HTTP 403"),
])
def test_captcha_o_bloqueo_detiene_todo_sin_reintentar(tmp_path, variante, estados, detalle):
    settings = _settings(tmp_path)
    pausas = _Pausas()

    consultas = _enriquecer(settings, [GPS, ABARROTES, SANTA_ANA], _Sicop(variante, estados=estados), pausas)

    assert [c.resultado for c in consultas] == ["control", "no_consultado", "no_consultado"]
    assert "control no automatizable" in consultas[0].motivo and detalle in consultas[0].motivo
    assert pausas.segundos == []  # no se intentó el siguiente
    assert _fichas(settings) == []


def test_un_fallo_no_detiene_los_demas_y_hay_pausa_entre_consultas(tmp_path):
    settings = _settings(tmp_path, ENRICH_DELAY_SECONDS="5")
    pausas = _Pausas()
    sicop = _Sicop(cambios={GPS: {"busqueda": json.dumps({"content": []})}})

    consultas = _enriquecer(settings, [GPS, ABARROTES, SANTA_ANA], sicop, pausas)

    assert [c.resultado for c in consultas] == ["fallo", "nueva", "nueva"]
    assert pausas.segundos == [5, 5]
    assert [f["nro_sicop"] for f in _fichas(settings)] == [ABARROTES, SANTA_ANA]


def test_un_numero_que_no_esta_en_la_base_no_abre_el_navegador(tmp_path):
    settings = _settings(tmp_path, nros=(GPS,))
    sicop = _Sicop()

    with pytest.raises(ValueError, match="No están en la base: 20261001587"):
        _enriquecer(settings, [GPS, SANTA_ANA], sicop)

    assert sicop.peticiones == []


def test_maximo_tres_por_corrida(tmp_path):
    settings = _settings(tmp_path)
    with pytest.raises(ValueError, match="de 1 a 3"):
        _enriquecer(settings, [GPS, ABARROTES, SANTA_ANA, "20260000001"])
