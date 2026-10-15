"""Avisos por correo (lección 7): notify --dry-run y --send, outbox con deduplicación y destinatarios.

Datos SINTÉTICOS en una base temporal (los carteles de tests/test_panel.py); nunca toca data/ ni envía correos:
el envío usa un proveedor SIMULADO.
"""

import sqlite3
from contextlib import closing
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import avisos, cli, destinatarios, usuarios
from app.cli import main
from app.notifications import EnvioIncierto, EnvioRechazado
from app.config import load_settings
from app.database import connect
from app.main import app
from tests.test_panel import AHORA, CR, CONTRASENA, _cierre, db, iniciar_sesion, token_csrf  # noqa: F401

BASE_URL = "https://sicop.ejemplo.test"
CANDIDATOS = {"00000000001", "00000000002", "00000000004"}  # Alta 3 días · Media 30 días · Alta por verificar
# 00000000003 es Baja y está vencido; 00000000005 no coincide con ninguna familia.


def _hace(dias):
    return (AHORA - timedelta(days=dias)).astimezone(CR).isoformat(timespec="seconds")


def _registrar_version(conn, nro, version, cuando, cierre="sin cambio"):
    """Simula que una importación trajo esta versión del cartel (como lo deja el importador)."""
    import_id = conn.execute("INSERT INTO imports (report, file_name, file_hash, data_origin, imported_at)"
                             " VALUES ('carteles', 'sintetico.csv', ?, 'sintetico', ?)", (f"{nro}{version}", cuando)).lastrowid
    conn.execute("INSERT INTO raw_snapshots (import_id, entity, natural_key, content_hash, payload, captured_at)"
                 " VALUES (?, 'cartel', ?, ?, '{}', ?)", (import_id, nro, version, cuando))
    conn.execute("UPDATE tenders SET content_hash = ? WHERE nro_sicop = ?", (version, nro))
    if cierre != "sin cambio":
        conn.execute("UPDATE tenders SET fecha_cierre_recepcion = ? WHERE nro_sicop = ?", (cierre, nro))


@pytest.fixture
def base(db):
    """Los 5 carteles sintéticos, vistos ayer, y 2 destinatarios activos."""
    with closing(connect(db)) as conn:
        for nro in [f"0000000000{n}" for n in range(1, 6)]:
            _registrar_version(conn, nro, "h", _hace(1))
        destinatarios.agregar(conn, "Oscar@Ejemplo.test", "Oscar")
        destinatarios.agregar(conn, "anabelle@ejemplo.test", "Anabelle")
    return db


def _settings(db, tmp_path, **extra):
    return load_settings(env_file=None, environ={"DATABASE_PATH": str(db), "EXPORTS_DIR": str(tmp_path / "exports"),
                                                 "APP_BASE_URL": BASE_URL + "/", **extra})


def _notify(db, tmp_path, ahora=AHORA, **extra):
    with closing(connect(db)) as conn:
        return avisos.notify(conn, _settings(db, tmp_path, **extra), ahora.astimezone(CR), dry_run=True)


def _outbox(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT recipient, nro_sicop, version, motivo, status FROM notification_outbox"
                            " ORDER BY id").fetchall()


# --- Criterio de la guía ------------------------------------------------------------------------------

def test_un_segundo_dry_run_no_duplica(base, tmp_path):
    primero = _notify(base, tmp_path)
    segundo = _notify(base, tmp_path, ahora=AHORA + timedelta(minutes=5))

    assert (primero.nuevos, primero.ya_avisados) == (6, 0)   # 3 oportunidades × 2 destinatarios
    assert (segundo.nuevos, segundo.ya_avisados) == (0, 6)
    assert len(_outbox(base)) == 6
    # La vista previa sigue mostrando lo preparado: es lo que enviaría --send.
    assert {p: {o.nro_sicop for o in lista} for p, lista in segundo.preparados.items()} == {
        "oscar@ejemplo.test": CANDIDATOS, "anabelle@ejemplo.test": CANDIDATOS}


class _ProveedorEspia:
    def __init__(self):
        self.llamadas = []

    def enviar(self, para, asunto, html, texto):
        self.llamadas.append(para)
        raise AssertionError("el dry-run no debe llamar al proveedor")


def test_el_dry_run_no_llama_al_proveedor_ni_marca_enviado(base, tmp_path):
    espia = _ProveedorEspia()
    with closing(connect(base)) as conn:
        avisos.notify(conn, _settings(base, tmp_path), AHORA, dry_run=True, proveedor=espia)

    assert espia.llamadas == []
    assert {fila[4] for fila in _outbox(base)} == {"preparado"}


def test_notify_exige_elegir_dry_run_o_send(base, tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["notify"], _settings(base, tmp_path))
    assert _outbox(base) == []


# --- Envío real (encargo B) con proveedor SIMULADO: nunca sale un correo de verdad -------------------------

class ProveedorSimulado:
    """SIMULADO. Responde lo que se le pida por destinatario: 'aceptar' (por defecto), 'rechazar', 'incierto'
    o 'explotar' (un error cualquiera). Anota cada llamada."""

    def __init__(self, **respuestas):
        self.respuestas = respuestas
        self.llamadas = []

    def enviar(self, para, asunto, html, texto):
        self.llamadas.append((para, asunto, html, texto))
        respuesta = self.respuestas.get(para.split("@")[0], "aceptar")
        if respuesta == "rechazar":
            raise EnvioRechazado("HTTP 400: Invalid To header (SIMULADO)")
        if respuesta == "incierto":
            raise EnvioIncierto("Gmail no respondió en 30 s (SIMULADO)")
        if respuesta == "explotar":
            raise RuntimeError("se cortó la luz (SIMULADO)")
        return f"sim-{len(self.llamadas)}"


def _enviar(db, tmp_path, proveedor, ahora=AHORA, solo=None):
    with closing(connect(db)) as conn:
        return avisos.notify(conn, _settings(db, tmp_path), ahora.astimezone(CR), dry_run=False,
                             proveedor=proveedor, solo=solo)


def _estados(db):
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute("SELECT recipient, status, count(*) FROM notification_outbox GROUP BY 1, 2"
                            " ORDER BY 1, 2").fetchall()


def test_un_envio_marca_aceptado_y_un_segundo_no_reenvia(base, tmp_path):
    sim = ProveedorSimulado()
    resultado = _enviar(base, tmp_path, sim)

    assert sorted(p for p, *_ in sim.llamadas) == ["anabelle@ejemplo.test", "oscar@ejemplo.test"]  # 1 por persona
    assert {p: (e.estado, e.avisos) for p, e in resultado.envios.items()} == {
        "anabelle@ejemplo.test": ("aceptado", 3), "oscar@ejemplo.test": ("aceptado", 3)}
    assert _estados(base) == [("anabelle@ejemplo.test", "aceptado", 3), ("oscar@ejemplo.test", "aceptado", 3)]
    with closing(sqlite3.connect(base)) as conn:
        assert {d for (d,) in conn.execute("SELECT detalle FROM notification_outbox")} == {"gmail id sim-1",
                                                                                          "gmail id sim-2"}
    otra = ProveedorSimulado()
    segundo = _enviar(base, tmp_path, otra, ahora=AHORA + timedelta(minutes=5))
    assert otra.llamadas == [] and segundo.envios == {}  # nada nuevo: no se reenvía


def test_el_correo_es_un_resumen_con_saludo_al_equipo(base, tmp_path):
    sim = ProveedorSimulado()
    _enviar(base, tmp_path, sim)

    para, asunto, html, texto = sim.llamadas[0]
    assert asunto == "SICOP · 3 oportunidades para revisar (3 nuevas)"
    assert "Hola, equipo." in html and "Hola, equipo." in texto
    assert all(f"{BASE_URL}/oportunidades/{nro}" in texto for nro in CANDIDATOS)


@pytest.mark.parametrize("respuesta, estado", [("rechazar", "fallido"), ("incierto", "incierto"),
                                               ("explotar", "incierto")])
def test_rechazo_y_duda_no_se_reintentan(base, tmp_path, respuesta, estado):
    resultado = _enviar(base, tmp_path, ProveedorSimulado(oscar=respuesta))

    assert resultado.envios["oscar@ejemplo.test"].estado == estado
    assert resultado.envios["anabelle@ejemplo.test"].estado == "aceptado"  # uno no arrastra al otro
    assert ("oscar@ejemplo.test", estado, 3) in _estados(base)
    otra = ProveedorSimulado()
    _enviar(base, tmp_path, otra, ahora=AHORA + timedelta(minutes=5))
    assert otra.llamadas == []  # ni fallido ni incierto se reintentan solos


def test_se_marca_incierto_antes_de_llamar_al_proveedor(base, tmp_path):
    vistos = []

    class Mirón(ProveedorSimulado):
        def enviar(self, para, asunto, html, texto):
            vistos.append(_estados(base))  # lo que hay en la base justo cuando sale el correo
            return super().enviar(para, asunto, html, texto)

    _enviar(base, tmp_path, Mirón(), solo="oscar@ejemplo.test")

    assert ("oscar@ejemplo.test", "incierto", 3) in vistos[0]  # si se cae aquí, no se reenvía


def test_un_aviso_vencido_no_se_envia_ni_sale_en_la_vista_previa(base, tmp_path):
    _notify(base, tmp_path)  # prepara los 3 candidatos; 00000000001 cierra en 3 días
    despues = AHORA + timedelta(days=4)

    vista = _notify(base, tmp_path, ahora=despues)
    sim = ProveedorSimulado()
    _enviar(base, tmp_path, sim, ahora=despues)

    assert "00000000001" not in {o.nro_sicop for o in vista.preparados["oscar@ejemplo.test"]}
    assert all("00000000001" not in texto for *_, texto in sim.llamadas)
    with closing(sqlite3.connect(base)) as conn:  # se queda «preparado», sin enviarse
        assert {s for (s,) in conn.execute(
            "SELECT status FROM notification_outbox WHERE nro_sicop = '00000000001'")} == {"preparado"}


def test_un_cartel_que_cambia_antes_de_enviarse_va_una_sola_vez(base, tmp_path):
    _notify(base, tmp_path)
    with closing(connect(base)) as conn:
        _registrar_version(conn, "00000000002", "h2", _hace(0))  # enmienda antes del envío
    _notify(base, tmp_path)
    sim = ProveedorSimulado()
    resultado = _enviar(base, tmp_path, sim, solo="oscar@ejemplo.test")

    assert resultado.envios["oscar@ejemplo.test"].avisos == 3
    assert ("oscar@ejemplo.test", "aceptado", 4) in _estados(base)  # las 2 filas del cartel quedan aceptadas


def test_solo_envia_a_un_destinatario_y_el_resto_espera(base, tmp_path):
    sim = ProveedorSimulado()
    _enviar(base, tmp_path, sim, solo="  OSCAR@ejemplo.test ")

    assert [p for p, *_ in sim.llamadas] == ["oscar@ejemplo.test"]
    assert _estados(base) == [("anabelle@ejemplo.test", "preparado", 3), ("oscar@ejemplo.test", "aceptado", 3)]
    with pytest.raises(avisos.AvisoError, match="no es un destinatario activo"):
        _enviar(base, tmp_path, sim, solo="nadie@ejemplo.test")


ENVIO_ACTIVADO = {"NOTIFICATIONS_ENABLED": "true", "NOTIFICATIONS_DRY_RUN": "false", "MAIL_PROVIDER": "gmail_api",
                  "MAIL_FROM": "licitaciones@ejemplo.test"}


@pytest.mark.parametrize("quitar", ["NOTIFICATIONS_ENABLED", "NOTIFICATIONS_DRY_RUN", "MAIL_PROVIDER", "MAIL_FROM"])
def test_send_se_niega_sin_la_configuracion_de_envio(base, tmp_path, capsys, monkeypatch, quitar):
    monkeypatch.setattr(cli, "_crear_proveedor", lambda s: pytest.fail("no debe crear el proveedor"))
    config = {k: v for k, v in ENVIO_ACTIVADO.items() if k != quitar}

    assert main(["notify", "--send"], _settings(base, tmp_path, **config)) == 1
    assert "el envío real está desactivado" in capsys.readouterr().err
    assert _outbox(base) == []


def test_send_sin_token_no_envia_ni_toca_la_outbox(base, tmp_path, capsys):
    config = {**ENVIO_ACTIVADO, "GOOGLE_TOKEN_FILE": str(tmp_path / "no_existe.json")}

    assert main(["notify", "--send"], _settings(base, tmp_path, **config)) == 1
    assert "google-auth" in capsys.readouterr().err
    assert _outbox(base) == []


def test_comando_notify_send(base, tmp_path, capsys, monkeypatch):
    sim = ProveedorSimulado(anabelle="incierto")
    monkeypatch.setattr(cli, "_crear_proveedor", lambda s: sim)
    settings = _settings(base, tmp_path, **ENVIO_ACTIVADO)

    assert main(["notify", "--send"], settings) == 1  # 1: hubo un incierto
    salida = capsys.readouterr().out
    assert "ENVÍO REAL" in salida
    assert "oscar@ejemplo.test: ACEPTADO · 3 oportunidad(es) · gmail id sim-2" in salida
    assert "anabelle@ejemplo.test: INCIERTO" in salida and "no se reenvían solos" in salida

    assert main(["notify", "--send"], settings) == 0
    assert "no se envió ningún correo" in capsys.readouterr().out


# --- Qué se selecciona --------------------------------------------------------------------------------

def test_solo_alta_y_media_con_plazo_no_vencido(base, tmp_path):
    _notify(base, tmp_path)

    assert {nro for _, nro, *_ in _outbox(base)} == CANDIDATOS


def test_el_primer_lote_se_limita_a_los_ultimos_n_dias(base, tmp_path):
    with closing(connect(base)) as conn:
        _registrar_version(conn, "00000000002", "v-vieja", _hace(10))  # visto hace 10 días

    _notify(base, tmp_path)  # NOTIFY_LOOKBACK_DAYS = 7 por defecto
    assert "00000000002" not in {nro for _, nro, *_ in _outbox(base)}

    _notify(base, tmp_path, NOTIFY_LOOKBACK_DAYS="14")
    assert "00000000002" in {nro for _, nro, *_ in _outbox(base)}


@pytest.mark.parametrize("valor", ["0", "-3", "siete"])
def test_dias_no_validos(base, tmp_path, valor):
    with pytest.raises(ValueError, match="NOTIFY_LOOKBACK_DAYS"):
        _notify(base, tmp_path, NOTIFY_LOOKBACK_DAYS=valor)


def test_cambios_relevantes_nueva_version_y_cambio_de_plazo(base, tmp_path):
    _notify(base, tmp_path)
    with closing(connect(base)) as conn:
        _registrar_version(conn, "00000000001", "v2", _hace(0))                          # enmienda, mismo cierre
        _registrar_version(conn, "00000000002", "v2", _hace(0), cierre=_cierre(45))      # se amplió el plazo

    resultado = _notify(base, tmp_path)

    assert resultado.nuevos == 4
    nuevos = {(r, nro, motivo) for r, nro, v, motivo, _ in _outbox(base) if v == "v2"}
    assert nuevos == {(r, nro, motivo) for r in ("oscar@ejemplo.test", "anabelle@ejemplo.test")
                      for nro, motivo in (("00000000001", "nueva_version"), ("00000000002", "cambio_plazo"))}
    assert _notify(base, tmp_path).nuevos == 0  # la misma versión no se vuelve a avisar


def test_un_destinatario_nuevo_recibe_lo_vigente_y_uno_quitado_nada(base, tmp_path):
    _notify(base, tmp_path)
    with closing(connect(base)) as conn:
        destinatarios.agregar(conn, "ivania@ejemplo.test", "Ivania")
        anabelle = next(d.id for d in destinatarios.listar(conn) if d.email.startswith("anabelle"))
        destinatarios.cambiar_estado(conn, anabelle, False)

    resultado = _notify(base, tmp_path)

    assert resultado.nuevos == 3  # solo para Ivania
    assert set(resultado.preparados) == {"oscar@ejemplo.test", "ivania@ejemplo.test"}
    assert not any("anabelle" in p.name for p in resultado.vista_previa)


def test_sin_destinatarios_no_prepara_nada(db, tmp_path):
    with closing(connect(db)) as conn:
        _registrar_version(conn, "00000000001", "h", _hace(1))

    resultado = _notify(db, tmp_path)

    assert (resultado.destinatarios, resultado.nuevos, resultado.vista_previa) == (0, 0, [])


def test_sin_oportunidades_nuevas_no_hay_correo(base, tmp_path):
    _notify(base, tmp_path)
    with closing(connect(base)) as conn, conn:
        conn.execute("UPDATE notification_outbox SET status = 'aceptado'")  # como si ya se hubieran enviado

    resultado = _notify(base, tmp_path)

    assert (resultado.nuevos, resultado.preparados, resultado.vista_previa) == (0, {}, [])


# --- Outbox ---------------------------------------------------------------------------------------------

def test_la_clave_de_deduplicacion_y_la_outbox_que_no_se_borra(base, tmp_path):
    _notify(base, tmp_path)
    clave = avisos.dedup_key("Oscar@Ejemplo.test", "00000000001", "h", "nueva")
    assert clave == "oscar@ejemplo.test|00000000001|h|nueva"

    with closing(sqlite3.connect(base)) as conn:
        assert conn.execute("SELECT count(*) FROM notification_outbox WHERE dedup_key = ?", (clave,)).fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conn.execute("INSERT INTO notification_outbox (dedup_key, recipient, nro_sicop, version, motivo,"
                         " rules_version, created_at) VALUES (?, 'oscar@ejemplo.test', '00000000001', 'h', 'nueva',"
                         " 'x', 'x')", (clave,))
        with pytest.raises(sqlite3.IntegrityError, match="no se borran"):
            conn.execute("DELETE FROM notification_outbox")
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute("UPDATE notification_outbox SET status = 'enviado'")  # solo los 4 estados de la guía


# --- Vista previa ---------------------------------------------------------------------------------------

def test_vista_previa_en_html_y_texto(base, tmp_path):
    resultado = _notify(base, tmp_path)

    carpeta = tmp_path / "exports"
    assert sorted(p.name for p in resultado.vista_previa) == [
        "01_anabelle_ejemplo_test.html", "01_anabelle_ejemplo_test.txt",
        "02_oscar_ejemplo_test.html", "02_oscar_ejemplo_test.txt"]
    assert all(p.parent.parent == carpeta for p in resultado.vista_previa)
    html = next(p for p in resultado.vista_previa if p.name == "02_oscar_ejemplo_test.html").read_text(encoding="utf-8")
    texto = next(p for p in resultado.vista_previa if p.name == "02_oscar_ejemplo_test.txt").read_text(encoding="utf-8")

    for parte in ("SICOP · 3 oportunidades para revisar (3 nuevas)", "Hola, equipo.",
                  "Prioridad Alta", "Prioridad Media", "GPS y gestión de flotas",           # prioridad y familia
                  "Municipalidad Sintética A", "Cierre: ",                                   # institución y cierre
                  "«monitoreo GPS»",                                                          # evidencia
                  f"{BASE_URL}/oportunidades/00000000001"):                                   # enlace al panel
        assert parte in html and parte in texto, parte
    assert "&lt;script&gt;" in html and "<script>" not in html  # el título sintético con HTML se escapa
    assert texto.startswith("Para: oscar@ejemplo.test\nAsunto: ") and "no se envió" in texto
    assert "Oscar" not in html  # sin el nombre de la persona (pedido de Oscar)


# --- CLI ------------------------------------------------------------------------------------------------

def test_comando_notify_dry_run(base, tmp_path, capsys):
    settings = _settings(base, tmp_path)

    assert main(["notify", "--dry-run"], settings) == 0
    primera = capsys.readouterr().out
    assert main(["notify", "--dry-run"], settings) == 0
    segunda = capsys.readouterr().out

    assert "DRY-RUN · no se envía nada" in primera and "Avisos nuevos en la outbox: 6" in primera
    assert "Avisos nuevos en la outbox: 0 · ya avisados antes (no se repiten): 6" in segunda
    assert "Vista previa: " in segunda


# --- Página de destinatarios (solo administradores) -----------------------------------------------------

@pytest.fixture
def admin_y_encargada(base, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(base))
    with closing(connect(base)) as conn:
        usuarios.crear_usuario(conn, "ivania@ejemplo.test", "Ivania", CONTRASENA, "admin")
        usuarios.crear_usuario(conn, "encargada@ejemplo.test", "Encargada", CONTRASENA, "encargado")
    clientes = []
    for email in ("ivania@ejemplo.test", "encargada@ejemplo.test"):
        cliente = TestClient(app)
        assert iniciar_sesion(cliente, email).status_code == 303
        clientes.append(cliente)
    return clientes


def _post(cliente, ruta, **datos):
    token = token_csrf(cliente.get("/oportunidades").text)
    return cliente.post(ruta, data={"csrf_token": token, **datos}, follow_redirects=False)


def test_la_administradora_agrega_y_quita_destinatarios(admin_y_encargada, base):
    ivania, _ = admin_y_encargada

    assert _post(ivania, "/destinatarios", email="nuevo@ejemplo.test", nombre="Nuevo").status_code == 303
    pagina = ivania.get("/destinatarios").text
    assert "Destinatario agregado: Nuevo &lt;nuevo@ejemplo.test&gt;." in pagina
    assert "Agregó un destinatario de avisos: Nuevo &lt;nuevo@ejemplo.test&gt; · Ivania" in pagina

    with closing(connect(base)) as conn:
        nuevo = next(d.id for d in destinatarios.listar(conn) if d.email == "nuevo@ejemplo.test")
    assert _post(ivania, f"/destinatarios/{nuevo}/estado", activo="0").status_code == 303
    with closing(connect(base)) as conn:
        assert "nuevo@ejemplo.test" not in {d.email for d in destinatarios.activos(conn)}
    assert "Quitó un destinatario de avisos: Nuevo" in ivania.get("/destinatarios").text


@pytest.mark.parametrize("datos, mensaje", [
    ({"email": "OSCAR@ejemplo.test", "nombre": "Otro"}, "ya está en la lista"),
    ({"email": "no-es-correo", "nombre": "X"}, "correo no es válido"),
    ({"email": "x@ejemplo.test", "nombre": "  "}, "Escribe el nombre"),
])
def test_destinatario_invalido(admin_y_encargada, datos, mensaje):
    ivania, _ = admin_y_encargada

    respuesta = _post(ivania, "/destinatarios", **datos)

    assert respuesta.status_code == 400 and mensaje in respuesta.text


def test_la_encargada_no_cambia_destinatarios(admin_y_encargada, base):
    _, encargada = admin_y_encargada

    assert 'href="/destinatarios"' not in encargada.get("/oportunidades").text
    assert encargada.get("/destinatarios").status_code == 403
    assert _post(encargada, "/destinatarios", email="intruso@ejemplo.test", nombre="Intruso").status_code == 403
    assert _post(encargada, "/destinatarios/1/estado", activo="0").status_code == 403
    with closing(connect(base)) as conn:
        assert {d.email for d in destinatarios.activos(conn)} == {"Oscar@Ejemplo.test", "anabelle@ejemplo.test"}
