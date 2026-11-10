"""Respuesta técnica: matriz de cumplimiento (DECISION_PROPUESTA.md, etapa 2; app/respuesta_tecnica.py).

Base y usuarios SINTÉTICOS de tests/test_seguimiento.py (Oscar admin; Ivania y Ana encargadas). Resumen SINTÉTICO.
"""

from contextlib import closing

import pytest
from starlette.datastructures import MultiDict

from app import historial, respuesta_tecnica as rt
from app.compras import Compra, LineaCompra
from app.database import connect
from tests.test_enriquecimiento import navegador
from tests.test_panel import token_csrf
from tests.test_seguimiento import NRO, OTRO, _asignar, _dar_seguimiento, _id, clientes, db  # noqa: F401

COMPRA = Compra("20269999001", "2026LD-000099-0009999999", "Monitoreo GPS (SINTÉTICO)", None, None, None,
                "Municipalidad Sintética A",
                [LineaCompra("1", None, "00000000", "Servicio de GPS", "en_catalogo", "8", "0", None)])
RESUMEN = {"que_piden": [
    {"linea": "1", "bien_o_servicio": "Dispositivo GPS", "cantidad": "8",
     "especificaciones_clave": ["Reporte cada 60 s", "Batería de respaldo 4 h"], "cita": "[DOC 1 · pág. 3]"},
    {"linea": "no encontrado", "bien_o_servicio": "Plataforma web", "cantidad": "1", "especificaciones_clave": [],
     "cita": "no encontrado"},
]}


def test_filas_iniciales_del_resumen_marcadas_con_su_origen():
    m = rt.valores_iniciales(COMPRA, RESUMEN)
    assert [(f["linea"], f["pide"], f["cita"], f["origen"]) for f in m["filas"]] == [
        ("1", "Reporte cada 60 s", "[DOC 1 · pág. 3]", "resumen"),
        ("1", "Batería de respaldo 4 h", "[DOC 1 · pág. 3]", "resumen"),
        ("", "Plataforma web", "", "resumen")]                      # sin especificaciones: lo que se compra
    assert all(f["estado"] == "" and f["ofrece"] == "" for f in m["filas"])   # nada se da por cumplido
    assert m["procedimiento"] == "2026LD-000099-0009999999" and m["empresa"] == "Hermatix M2M Communication S.A."


def test_sin_resumen_una_fila_por_linea_del_cartel():
    m = rt.valores_iniciales(COMPRA, None)
    assert [(f["linea"], f["pide"], f["origen"]) for f in m["filas"]] == [("1", "Servicio de GPS", "cartel")]


def test_formulario_ignora_las_filas_vacias():
    f = MultiDict([("procedimiento", "P-1"), ("empresa", "Empresa SINTÉTICA")]
                  + [(f"fil_{c}", v) for c, v in (("linea", "1"), ("pide", "A"), ("cita", ""), ("ofrece", "B"),
                                                  ("prueba", "Ficha"), ("estado", "cumple"), ("nota", ""),
                                                  ("origen", ""))]
                  + [(f"fil_{c}", "") for c in ("linea", "pide", "cita", "ofrece", "prueba", "estado", "nota",
                                                "origen")])
    datos = rt.desde_formulario(f)
    assert len(datos["filas"]) == 1 and datos["filas"][0]["ofrece"] == "B"


@pytest.mark.parametrize("cambio, mensaje", [
    ({"procedimiento": ""}, "procedimiento"),
    ({"empresa": " "}, "empresa"),
    ({"filas": []}, "no tiene filas"),
    ({"filas": [{"pide": "", "ofrece": "algo"}]}, "fila 1 no dice"),
    ({"filas": [{"pide": "A", "estado": "inventado"}]}, "estado que no existe"),
    ({"filas": [{"pide": "A" * 1001}]}, "más de 1000"),
])
def test_leer_rechaza_lo_que_no_sirve(cambio, mensaje):
    datos = {"procedimiento": "P-1", "empresa": "Empresa SINTÉTICA", "filas": [{"pide": "A"}], **cambio}
    with pytest.raises(rt.MatrizError, match=mensaje):
        rt.leer(datos)


def test_no_cumple_y_sin_marcar_se_cuentan_y_no_se_esconden():
    filas = rt.leer({"procedimiento": "P-1", "empresa": "E", "filas": [
        {"pide": "A", "estado": "cumple"}, {"pide": "B", "estado": "no_cumple"}, {"pide": "C"}]})
    assert [f.estado_texto for f in filas] == ["Cumple", "No cumple", "Sin marcar"]
    assert rt.conteo(filas) == {"Cumple": 1, "No cumple": 1, "Sin marcar": 1}
    pagina = rt.html({"procedimiento": "P-1", "empresa": "E <b>"}, filas, __import__("datetime").date(2026, 11, 9))
    assert "No cumple" in pagina and "Sin marcar" in pagina and "9 de noviembre de 2026" in pagina
    assert "E &lt;b&gt;" in pagina                                    # el texto va escapado


# --- Panel ---------------------------------------------------------------------------------------------------------

def _formulario(**cambios) -> dict:
    datos = {"procedimiento": "2026LD-000099-0009999999", "empresa": "Empresa SINTÉTICA S.A.",
             "institucion": "Municipalidad Sintética A", "objeto": "Monitoreo GPS (SINTÉTICO)",
             "fil_linea": ["1", ""], "fil_pide": ["Reporte cada 60 s", ""], "fil_cita": ["DOC 1 · pág. 3", ""],
             "fil_ofrece": ["FleetMatix reporta cada 30 s (SINTÉTICO)", ""], "fil_prueba": ["Ficha técnica, pág. 2", ""],
             "fil_estado": ["cumple", ""], "fil_nota": ["", ""], "fil_origen": ["resumen", ""]}
    datos.update(cambios)
    return datos


def _enviar(cliente, accion, nro=NRO, **cambios):
    token = token_csrf(cliente.get(f"/oportunidades/{nro}/respuesta-tecnica").text)
    return cliente.post(f"/oportunidades/{nro}/respuesta-tecnica",
                        data={"csrf_token": token, "accion": accion, **_formulario(**cambios)}, follow_redirects=False)


def _acciones(db, accion):
    with closing(connect(db)) as conn:
        return conn.execute("SELECT count(*) FROM audit_log WHERE accion = ?", (accion,)).fetchone()[0]


def test_solo_quien_entra_al_expediente(clientes, db):
    oscar, ivania, ana = clientes["oscar"], clientes["ivania"], clientes["ana"]
    assert oscar.get(f"/oportunidades/{OTRO}/respuesta-tecnica").status_code == 404     # sin seguimiento
    assert _dar_seguimiento(oscar).status_code == 303
    assert _asignar(oscar, _id(db, "ivania@ejemplo.test")).status_code == 303
    assert oscar.get(f"/oportunidades/{NRO}/respuesta-tecnica").status_code == 200      # administrador
    assert ivania.get(f"/oportunidades/{NRO}/respuesta-tecnica").status_code == 200     # su encargada
    assert ana.get(f"/oportunidades/{NRO}/respuesta-tecnica").status_code == 403        # otra encargada


def test_matriz_nueva_y_borrador(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    pagina = oscar.get(f"/oportunidades/{NRO}/respuesta-tecnica").text
    assert "Matriz de cumplimiento" in pagina and "Empresa SINTÉTICA" not in pagina   # sin resumen ni líneas: vacía
    assert "Hermatix M2M Communication S.A." in pagina                                  # config/oferta.yaml
    assert f'href="/oportunidades/{NRO}/respuesta-tecnica"' in oscar.get(f"/oportunidades/{NRO}").text

    r = _enviar(oscar, "guardar")
    assert r.status_code == 303 and r.headers["location"] == f"/oportunidades/{NRO}/respuesta-tecnica"
    with closing(connect(db)) as conn:
        datos, quien, _ = rt.borrador(conn, NRO)
    assert quien == "Oscar" and len(datos["filas"]) == 1 and datos["filas"][0]["estado"] == "cumple"
    assert _acciones(db, "guardar_respuesta_tecnica") == 1
    pagina = oscar.get(f"/oportunidades/{NRO}/respuesta-tecnica").text
    assert "Borrador guardado." in pagina and "FleetMatix reporta cada 30 s" in pagina
    assert "Del resumen con IA: revisar contra el pliego" in pagina and "Cumple: 1" in pagina


def test_un_dato_malo_vuelve_al_formulario_sin_perder_lo_escrito(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    r = _enviar(oscar, "pdf", fil_pide=["", ""], fil_ofrece=["Algo ofrecido (SINTÉTICO)", ""])
    assert r.status_code == 400 and "no dice qué pide el cartel" in r.text and "Algo ofrecido" in r.text
    assert _acciones(db, "generar_respuesta_tecnica") == 0 and _acciones(db, "guardar_respuesta_tecnica") == 1


def test_sin_token_csrf_no_guarda(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    r = oscar.post(f"/oportunidades/{NRO}/respuesta-tecnica", data={"accion": "guardar", **_formulario()},
                   follow_redirects=False)
    assert r.status_code in (400, 403)
    with closing(connect(db)) as conn:
        assert rt.borrador(conn, NRO) is None


@navegador
def test_descargar_pdf(clientes, db):
    oscar = clientes["oscar"]
    _dar_seguimiento(oscar)
    r = _enviar(oscar, "pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and f"respuesta_tecnica_{NRO}_" in r.headers["content-disposition"]
    assert _acciones(db, "generar_respuesta_tecnica") == 1
    assert "generar_respuesta_tecnica" in historial.ACCIONES
