"""Corregir la oferta desde el chat (DECISION_IA.md §10, paso 4 de §10.7; migración 0045).

La oferta la sigue armando la app (app/propuesta.py). Una versión guarda la LISTA de cambios que se le aplican, en
orden; la versión 1 no tiene ninguno. La IA solo PROPONE un cambio (app/ai/chat.py); se aplica cuando una persona
pulsa «Aplicar» (decisión de Ivania, 2026-11-11), y eso crea la versión siguiente. Nada se borra.

La lista cerrada de cambios (§10.3.1):
* cambiar_respuesta · marcar (cumple / acepta) — no en una sección en rojo: eso se arregla respondiendo el requisito.
* quitar_seccion · restaurar_seccion · agregar_seccion · mover_seccion — solo porque alguien lo pidió; una sección
  en rojo no se quita (nada pendiente se esconde).
* quitar_anexo · restaurar_anexo — el archivo no se toca; un anexo pendiente no se quita.
Nunca: precios, el texto del pliego ni sacar algo del rojo. No hay acciones para eso.

Una sección se reconoce por su número y su título, no por su lugar: si el pliego cambia y un cambio ya no encuentra
su sección, no se pierde en silencio: sale en la portada como pendiente.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from dataclasses import dataclass, replace
from datetime import datetime

from app import historial
from app.ai import oferta as ia_oferta
from app.database import transaccion
from app.historial import Quien
from app.importers.comun import HORA_CR

ACCIONES = ("cambiar_respuesta", "marcar", "quitar_seccion", "restaurar_seccion", "agregar_seccion", "mover_seccion",
            "quitar_anexo", "restaurar_anexo")
LARGO_TEXTO = 2000


class CambioInvalido(ValueError):
    """El cambio no se puede hacer; el mensaje es el que ve la persona."""


@dataclass(frozen=True)
class Version:
    id: int
    numero: int
    cambios: list[dict]
    descripcion: str
    creado_por: str
    creado_en: str


@dataclass(frozen=True)
class Propuesta:
    id: int
    mensaje_id: int | None
    cambio: dict
    descripcion: str
    estado: str
    decidido_por: str | None
    decidido_en: str | None


def _normal(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def clave(bloque) -> str:
    """Cómo se reconoce una sección entre versiones: su número y su título."""
    return f"{bloque.numero}·{_normal(bloque.titulo)}"


def clave_anexo(anexo) -> str:
    return _normal(anexo.titulo)


def secciones(bloques: list) -> list:
    """Las secciones que se pueden cambiar: las que llevan respuesta y las agregadas (no el texto antes de la primera)."""
    return [b for b in bloques if b.respuesta is not None or getattr(b, "agregada", False)]


# --- Aplicar una lista de cambios ----------------------------------------------------------------------------------

def _nombre(bloque) -> str:
    return f"«{(bloque.numero + '. ') if bloque.numero else ''}{bloque.titulo or 'sin título'}»"


def aplicar(bloques: list, anexos: list, cambios: list[dict]) -> tuple[list, list, list[str]]:
    """Aplica los cambios en orden. Devuelve (bloques, anexos, avisos). Un cambio que no se puede aplicar no se
    pierde: queda como aviso (va a la portada, con lo pendiente)."""
    from app.propuesta import Bloque
    bloques = [replace(b, respuesta=list(b.respuesta) if b.respuesta is not None else None) for b in bloques]
    anexos = list(anexos)
    quitadas, quitados, avisos = set(), set(), []
    for n, c in enumerate(cambios, start=1):
        try:
            accion = c.get("accion")
            if accion == "agregar_seccion":
                nueva = Bloque("", c["titulo"], c["texto"], respuesta=None, agregada=True)
                destino = _buscar(bloques, c.get("antes_de")) if c.get("antes_de") else None
                bloques.insert(bloques.index(destino) if destino else len(bloques), nueva)
            elif accion in ("quitar_anexo", "restaurar_anexo"):
                anexo = next((a for a in anexos if clave_anexo(a) == c["anexo"]), None)
                if anexo is None:
                    raise CambioInvalido(f"no se encontró el anexo «{c['anexo']}»")
                if accion == "quitar_anexo":
                    if anexo.pendiente:
                        raise CambioInvalido(f"el anexo «{anexo.titulo}» está pendiente: no se quita (nada pendiente "
                                             "se esconde)")
                    quitados.add(c["anexo"])
                else:
                    quitados.discard(c["anexo"])
            else:
                b = _buscar(bloques, c.get("seccion"))
                if b is None:
                    raise CambioInvalido(f"no se encontró la sección «{c.get('seccion', '').split('·')[-1]}»")
                if accion in ("cambiar_respuesta", "marcar", "quitar_seccion") and b.pendiente:
                    raise CambioInvalido(f"la sección {_nombre(b)} está en rojo: eso se arregla respondiendo el "
                                         "requisito en el asistente")
                if accion == "cambiar_respuesta":
                    if b.respuesta is None:
                        b.texto = c["texto"]                # una sección agregada: su texto es de Hermatix
                    else:
                        b.respuesta = [c["texto"]]
                elif accion == "marcar":
                    if b.respuesta is None:
                        raise CambioInvalido(f"la sección {_nombre(b)} no lleva respuesta")
                    b.tipo, b.respuesta = c["tipo"], [ia_oferta.TIPOS[c["tipo"]]]
                elif accion == "quitar_seccion":
                    quitadas.add(clave(b))
                elif accion == "restaurar_seccion":
                    quitadas.discard(clave(b))
                elif accion == "mover_seccion":
                    destino = _buscar(bloques, c.get("antes_de"))
                    if destino is None or destino is b:
                        raise CambioInvalido("no se encontró la sección de destino")
                    bloques.remove(b)
                    bloques.insert(bloques.index(destino), b)
                else:
                    raise CambioInvalido(f"«{accion}» no es un cambio permitido")
        except (CambioInvalido, KeyError) as exc:
            motivo = str(exc) if isinstance(exc, CambioInvalido) else "faltan datos del cambio"
            avisos.append(f"Cambio {n} de la oferta («{c.get('descripcion') or c.get('accion')}») no se aplicó: "
                          f"{motivo}.")
    bloques = [b for b in bloques if clave(b) not in quitadas]
    anexos = [a for a in anexos if clave_anexo(a) not in quitados]
    for grupo in (2, 3, 4):                                   # los anexos se vuelven a numerar
        for k, a in enumerate((a for a in anexos if a.grupo == grupo), start=1):
            a.numero = f"{grupo}.{k}"
    return bloques, anexos, avisos


def _buscar(bloques: list, llave: str | None):
    return next((b for b in bloques if llave and clave(b) == llave), None)


# --- Describir un cambio (lo escribe la app, no la IA) -------------------------------------------------------------

def describir(c: dict, bloques: list, anexos: list) -> str:
    b = _buscar(bloques, c.get("seccion"))
    nombre = _nombre(b) if b else "la sección"
    a = c.get("accion")
    if a == "cambiar_respuesta":
        return f"Cambiar la respuesta de {nombre} a: «{c['texto']}»"
    if a == "marcar":
        return f"Marcar {nombre} como «{ia_oferta.TIPOS[c['tipo']]}»"
    if a == "quitar_seccion":
        return f"Quitar {nombre} de esta oferta (solo de esta; la estructura de las demás no cambia)"
    if a == "restaurar_seccion":
        return f"Volver a poner {nombre}"
    if a == "mover_seccion":
        destino = _buscar(bloques, c.get("antes_de"))
        return f"Mover {nombre} antes de {_nombre(destino) if destino else 'otra sección'}"
    if a == "agregar_seccion":
        donde = _buscar(bloques, c.get("antes_de"))
        return f"Agregar la sección «{c['titulo']}»{' antes de ' + _nombre(donde) if donde else ' al final'}: «{c['texto']}»"
    anexo = next((x for x in anexos if clave_anexo(x) == c.get("anexo")), None)
    titulo = f"«{anexo.numero} · {anexo.titulo}»" if anexo else "el anexo"
    return f"{'Quitar' if a == 'quitar_anexo' else 'Volver a poner'} el anexo {titulo} (el archivo no se toca)"


def validar(c: dict, bloques: list, anexos: list, cambios_actuales: list[dict]) -> str:
    """Comprueba que el cambio se puede aplicar sobre la oferta de ahora. Devuelve su descripción o lanza."""
    if c.get("accion") not in ACCIONES:
        raise CambioInvalido("eso no lo puedo cambiar: solo respuestas, secciones y anexos, nunca precios ni el pliego")
    for campo in ("texto", "titulo"):
        if campo in c:
            c[campo] = " ".join(str(c[campo]).split())[:LARGO_TEXTO]
            if not c[campo]:
                raise CambioInvalido(f"falta el {campo} del cambio")
    if c["accion"] == "marcar" and c.get("tipo") not in ia_oferta.TIPOS:
        raise CambioInvalido("marcar es «cumple» o «acepta»")
    _, _, avisos = aplicar(bloques, anexos, [c])
    if avisos:
        raise CambioInvalido(avisos[0].split("no se aplicó: ", 1)[-1].rstrip("."))
    return describir(c, bloques, anexos)


# --- Versiones y propuestas en la base -----------------------------------------------------------------------------

def _momento(ahora: datetime) -> str:
    return ahora.astimezone(HORA_CR).isoformat(timespec="seconds")


def versiones(conn: sqlite3.Connection, nro_sicop: str) -> list[Version]:
    return [Version(i, n, json.loads(c), d, p, e) for (i, n, c, d, p, e) in conn.execute(
        "SELECT id, numero, cambios_json, descripcion, creado_por_nombre, creado_en FROM oferta_versiones"
        " WHERE nro_sicop = ? ORDER BY numero", (nro_sicop,))]


def ultima(conn: sqlite3.Connection, nro_sicop: str) -> Version | None:
    lista = versiones(conn, nro_sicop)
    return lista[-1] if lista else None


def version(conn: sqlite3.Connection, nro_sicop: str, numero: int) -> Version | None:
    return next((v for v in versiones(conn, nro_sicop) if v.numero == numero), None)


def _nueva_version(conn: sqlite3.Connection, nro_sicop: str, cambios: list[dict], descripcion: str, quien: Quien,
                   ahora: datetime) -> int:
    numero = (ultima(conn, nro_sicop).numero if ultima(conn, nro_sicop) else 0) + 1
    return conn.execute(
        "INSERT INTO oferta_versiones (nro_sicop, numero, cambios_json, descripcion, creado_por, creado_por_nombre,"
        " creado_en) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nro_sicop, numero, json.dumps(cambios, ensure_ascii=False), descripcion, quien.user_id, quien.nombre,
         _momento(ahora))).lastrowid


def asegurar_primera(conn: sqlite3.Connection, nro_sicop: str, quien: Quien, ahora: datetime) -> None:
    """La primera vez que se arma la oferta queda como versión 1 (sin cambios)."""
    if ultima(conn, nro_sicop) is None:
        with transaccion(conn):
            _nueva_version(conn, nro_sicop, [], "Oferta armada por la app, sin cambios.", quien, ahora)


def propuestas(conn: sqlite3.Connection, nro_sicop: str) -> list[Propuesta]:
    return [Propuesta(i, m, json.loads(c), d, e, p, en) for (i, m, c, d, e, p, en) in conn.execute(
        "SELECT id, mensaje_id, cambio_json, descripcion, estado, decidido_por_nombre, decidido_en"
        " FROM oferta_propuestas WHERE nro_sicop = ? ORDER BY id", (nro_sicop,))]


def proponer(conn: sqlite3.Connection, nro_sicop: str, cambio: dict, descripcion: str, mensaje_id: int,
             ahora: datetime) -> int:
    with transaccion(conn):
        return conn.execute(
            "INSERT INTO oferta_propuestas (nro_sicop, mensaje_id, cambio_json, descripcion, creado_en)"
            " VALUES (?, ?, ?, ?, ?)", (nro_sicop, mensaje_id, json.dumps(cambio, ensure_ascii=False), descripcion,
                                        _momento(ahora))).lastrowid


def _pendiente(conn: sqlite3.Connection, nro_sicop: str, propuesta_id: int) -> Propuesta:
    p = next((x for x in propuestas(conn, nro_sicop) if x.id == propuesta_id), None)
    if p is None:
        raise CambioInvalido("Esa propuesta no es de este cartel.")
    if p.estado != "pendiente":
        raise CambioInvalido(f"Esa propuesta ya se decidió ({p.estado}).")
    return p


def decidir(conn: sqlite3.Connection, nro_sicop: str, propuesta_id: int, aplicar_: bool, bloques: list, anexos: list,
            quien: Quien, ahora: datetime) -> Version | None:
    """«Aplicar» (crea la versión siguiente) o «No». bloques y anexos son los de la oferta de ahora, sin los cambios
    de la última versión (app/propuesta.preparar con cambios=False): se comprueba que el cambio todavía se puede."""
    p = _pendiente(conn, nro_sicop, propuesta_id)
    if not aplicar_:
        with transaccion(conn):
            conn.execute("UPDATE oferta_propuestas SET estado = 'rechazada', decidido_por = ?, decidido_por_nombre = ?,"
                         " decidido_en = ? WHERE id = ?", (quien.user_id, quien.nombre, _momento(ahora), p.id))
            historial.registrar(conn, quien, "rechazar_cambio_oferta", f"{nro_sicop}: propuesta #{p.id}")
        return None
    anterior = ultima(conn, nro_sicop)
    cambios = list(anterior.cambios) if anterior else []
    actuales, anexos_actuales, _ = aplicar(bloques, anexos, cambios)
    validar(dict(p.cambio), actuales, anexos_actuales, cambios)          # lanza si ya no se puede
    with transaccion(conn):
        if anterior is None:
            _nueva_version(conn, nro_sicop, [], "Oferta armada por la app, sin cambios.", quien, ahora)
        version_id = _nueva_version(conn, nro_sicop, cambios + [{**p.cambio, "descripcion": p.descripcion}],
                                    p.descripcion, quien, ahora)
        conn.execute("UPDATE oferta_propuestas SET estado = 'aplicada', decidido_por = ?, decidido_por_nombre = ?,"
                     " decidido_en = ?, version_id = ? WHERE id = ?",
                     (quien.user_id, quien.nombre, _momento(ahora), version_id, p.id))
        historial.registrar(conn, quien, "aplicar_cambio_oferta", f"{nro_sicop}: propuesta #{p.id}")
    return ultima(conn, nro_sicop)
