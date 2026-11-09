"""Oferta económica desde el panel del cartel (DECISION_PROPUESTA.md; app/oferta_economica.py y oferta_form.html).

Base y usuarios SINTÉTICOS de tests/test_seguimiento.py (Oscar admin; Ivania y Ana encargadas). Precios SINTÉTICOS.
"""

from contextlib import closing

import pytest

from app import historial, oferta_economica as oe
from app.database import connect
from tests.test_enriquecimiento import navegador
from tests.test_panel import token_csrf
from tests.test_seguimiento import NRO, OTRO, _asignar, _dar_seguimiento, _id, clientes, db  # noqa: F401


def _formulario(**cambios) -> dict:
    datos = {
        "procedimiento": "2026LD-000099-0009999999", "tipo_procedimiento": "Licitación Reducida",
        "institucion": "Municipalidad Sintética A", "destinatario": "Proveeduría", "lugar": "San José",
        "fecha": "2026-11-09", "partida": "1",
        "objeto": "Servicio de monitoreo GPS de vehículos (SINTÉTICO)",
        "empresa_nombre": "Empresa SINTÉTICA S.A.", "empresa_cedula": "3-101-000000",
        "rep_nombre": "Persona SINTÉTICA", "rep_cargo": "representante legal", "rep_calidades": "", "rep_cedula": "",
        "moneda": "CRC", "meses": "12",
        "lin_numero": ["1", ""], "lin_cantidad": ["8", ""], "lin_descripcion": ["Monitoreo GPS (SINTÉTICO)", ""],
        "lin_precio": ["25000.00", ""],
        "iva_modo": "exento", "iva_tasa": "", "iva_exento": "exoneración SINTÉTICA",
        "cond_garantia": "Todo el contrato.", "cond_entrega": "10 días hábiles.", "cond_forma_pago": "30 días.",
        "cond_validez": "4 meses.",
        "des_mano_de_obra_nombre": "Mano de obra", "des_mano_de_obra_pct": "30",
        "des_insumos_nombre": "Equipos", "des_insumos_pct": "40",
        "des_gastos_administrativos_nombre": "Gastos", "des_gastos_administrativos_pct": "15",
        "des_utilidad_nombre": "Utilidad", "des_utilidad_pct": "15",
    }
    datos.update(cambios)
    return datos


def _enviar(cliente, accion, nro=NRO, **cambios):
    token = token_csrf(cliente.get(f"/oportunidades/{nro}/oferta").text)
    return cliente.post(f"/oportunidades/{nro}/oferta", data={"csrf_token": token, "accion": accion,
                                                               **_formulario(**cambios)}, follow_redirects=False)


def _acciones(db, accion):
    with closing(connect(db)) as conn:
        return conn.execute("SELECT count(*) FROM audit_log WHERE accion = ?", (accion,)).fetchone()[0]


def test_solo_quien_entra_al_expediente(clientes, db):
    oscar, ivania, ana = clientes["oscar"], clientes["ivania"], clientes["ana"]
    assert oscar.get(f"/oportunidades/{OTRO}/oferta").status_code == 404      # sin seguimiento
    assert _dar_seguimiento(oscar).status_code == 303
    assert _asignar(oscar, _id(db, "ivania@ejemplo.test")).status_code == 303
    assert oscar.get(f"/oportunidades/{NRO}/oferta").status_code == 200       # administrador
    assert ivania.get(f"/oportunidades/{NRO}/oferta").status_code == 200      # su encargada
    assert ana.get(f"/oportunidades/{NRO}/oferta").status_code == 403         # otra encargada: hay precios
    assert ana.post(f"/oportunidades/{NRO}/oferta", data={"accion": "guardar"}).status_code in (400, 403)


def test_formulario_nuevo_sale_del_cartel_y_el_borrador_se_guarda(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    pagina = oscar.get(f"/oportunidades/{NRO}/oferta").text
    assert "Municipalidad Sintética A" in pagina and "Servicio de monitoreo GPS de vehículos" in pagina
    assert "Hermatix M2M Communication S.A." in pagina                         # config/oferta.yaml
    assert f'href="/oportunidades/{NRO}/oferta"' in oscar.get(f"/oportunidades/{NRO}").text

    r = _enviar(oscar, "guardar")
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}/oferta"
    with closing(connect(db)) as conn:
        datos, quien, _ = oe.borrador(conn, NRO)
    assert quien == "Oscar" and datos["lineas"] == [{"numero": "1", "cantidad": "8",
                                                      "descripcion": "Monitoreo GPS (SINTÉTICO)",
                                                      "precio_unitario": "25000.00"}]   # la fila vacía no cuenta
    assert _acciones(db, "guardar_oferta") == 1
    pagina = oscar.get(f"/oportunidades/{NRO}/oferta").text
    assert "Borrador guardado." in pagina and 'value="25000.00"' in pagina


def test_un_dato_malo_vuelve_al_formulario_sin_perder_lo_escrito(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    r = _enviar(oscar, "pdf", des_utilidad_pct="20")                       # suman 105 %
    assert r.status_code == 400 and "suman 105" in r.text and 'value="25000.00"' in r.text
    assert _acciones(db, "generar_oferta") == 0 and _acciones(db, "guardar_oferta") == 1


def test_sin_token_csrf_no_guarda(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    r = oscar.post(f"/oportunidades/{NRO}/oferta", data={"accion": "guardar", **_formulario()}, follow_redirects=False)
    assert r.status_code in (400, 403)
    with closing(connect(db)) as conn:
        assert oe.borrador(conn, NRO) is None


@navegador
def test_descargar_pdf(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    r = _enviar(oscar, "pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and f"oferta_economica_{NRO}_" in r.headers["content-disposition"]
    assert _acciones(db, "generar_oferta") == 1
    with closing(connect(db)) as conn:
        detalle = conn.execute("SELECT detalle FROM audit_log WHERE accion = 'generar_oferta'").fetchone()[0]
    assert detalle == NRO and "25000" not in detalle                            # el historial no guarda montos
    assert "guardar_oferta" in historial.ACCIONES
