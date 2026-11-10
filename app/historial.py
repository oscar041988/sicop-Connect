"""Historial de cambios de administración (tabla audit_log, migración 0005): quién cambió qué y cuándo.
Hoy: usuarios, destinatarios de los avisos, avisos revisados a mano y seguimiento de carteles.

No se borra ni se modifica (triggers). Nunca guarda contraseñas ni hashes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

ACCIONES = {
    "crear_usuario": "Creó un usuario",
    "cambiar_nivel": "Cambió un nivel",
    "activar": "Activó un usuario",
    "desactivar": "Desactivó un usuario",
    "cambiar_contrasena": "Puso una contraseña nueva",
    "eliminar_usuario": "Eliminó un usuario",
    "agregar_destinatario": "Agregó un destinatario de avisos",
    "activar_destinatario": "Volvió a activar un destinatario",
    "desactivar_destinatario": "Quitó un destinatario de avisos",
    "reintentar_aviso": "Volvió a preparar un aviso",
    "confirmar_aviso": "Confirmó que un aviso sí salió",
    "abrir_seguimiento": "Dio seguimiento a un cartel",
    "asignar_encargado": "Asignó el encargado de un cartel",
    "cambiar_etapa": "Cambió la etapa de un cartel en seguimiento",
    "subir_archivo": "Subió un archivo al expediente de un cartel",
    "escribir_nota": "Escribió una nota en el expediente de un cartel",
    "descargar_expediente": "Descargó todo el expediente de un cartel",
    "crear_elemento_perfil": "Agregó un elemento al perfil de Hermatix",
    "nueva_version_perfil": "Cargó una versión de un elemento del perfil",
    "marcar_pendiente_perfil": "Marcó pendiente un elemento del perfil",
    "ver_documento_perfil": "Vio un documento del perfil",
    "descargar_documento_perfil": "Descargó un documento del perfil",
    "generar_lista_verificacion": "Generó con IA la lista de verificación de un cartel",
    "corregir_item_verificacion": "Corrigió un requisito de la lista de verificación",
    "agregar_item_verificacion": "Agregó un requisito a la lista de verificación",
    "quitar_item_verificacion": "Quitó un requisito de la lista de verificación",
    "empezar_asistente": "Empezó el asistente de elegibilidad de un cartel",
    "redactar_preguntas_asistente": "Pidió a la IA las preguntas del asistente de un cartel",
    "responder_asistente": "Respondió una pregunta del asistente",
    "confirmar_perfil_asistente": "Confirmó un dato del perfil en el asistente",
    "ver_documento_asistente": "Vio un documento de una respuesta del asistente",
    "descargar_documento_asistente": "Descargó un documento de una respuesta del asistente",
    "generar_reporte": "Generó el Reporte de cartel en PDF",
    "guardar_oferta": "Guardó el borrador de la oferta económica",
    "generar_oferta": "Generó la oferta económica en PDF",
    "guardar_respuesta_tecnica": "Guardó el borrador de la respuesta técnica",
    "generar_respuesta_tecnica": "Generó la respuesta técnica en PDF",
    "ampliar_asistente": "Abrió el resto de las preguntas del asistente (después de los excluyentes)",
    "revisar_resultado": "Decidió si un requisito cumple en el resultado de elegibilidad",
    "calcular_resultado": "Calculó el resultado de elegibilidad de un cartel",
    "marcar_cumple_linea": "Marcó si Hermatix cumple una fila de «Qué piden» del resumen",
}
DE_USUARIOS = ("crear_usuario", "cambiar_nivel", "activar", "desactivar", "cambiar_contrasena", "eliminar_usuario")
DE_DESTINATARIOS = ("agregar_destinatario", "activar_destinatario", "desactivar_destinatario")
DE_AVISOS = ("reintentar_aviso", "confirmar_aviso")
DE_SEGUIMIENTO = ("abrir_seguimiento", "asignar_encargado", "cambiar_etapa", "subir_archivo", "escribir_nota",
                  "descargar_expediente")
DE_PERFIL = ("crear_elemento_perfil", "nueva_version_perfil", "marcar_pendiente_perfil")
ACCESOS_PERFIL = ("ver_documento_perfil", "descargar_documento_perfil")
DE_VERIFICACION = ("generar_lista_verificacion", "corregir_item_verificacion", "agregar_item_verificacion",
                   "quitar_item_verificacion")
DE_ASISTENTE = ("empezar_asistente", "redactar_preguntas_asistente", "responder_asistente",
                "confirmar_perfil_asistente", "ver_documento_asistente", "descargar_documento_asistente",
                "ampliar_asistente", "revisar_resultado", "calcular_resultado")
# Registro del asistente (lección 5, solo administradores): lista, preguntas, respuestas, documentos, resultado,
# «¿Cumple?» del resumen y el perfil con sus accesos.
REGISTRO_ASISTENTE = DE_VERIFICACION + DE_ASISTENTE + ("marcar_cumple_linea",) + DE_PERFIL + ACCESOS_PERFIL


@dataclass(frozen=True)
class Quien:
    """Quién hace el cambio: un administrador desde el panel o la terminal (user_id None)."""
    user_id: int | None
    nombre: str


TERMINAL = Quien(None, "terminal")


@dataclass
class Evento:
    actor: str
    accion: str
    detalle: str
    fecha: str


def registrar(conn: sqlite3.Connection, quien: Quien, accion: str, detalle: str) -> None:
    if accion not in ACCIONES:
        raise ValueError(f"Acción desconocida para el historial: {accion}")
    conn.execute("INSERT INTO audit_log (user_id, actor, accion, detalle, created_at) VALUES (?, ?, ?, ?, ?)",
                 (quien.user_id, quien.nombre, accion, detalle,
                  datetime.now(timezone.utc).isoformat(timespec="seconds")))


def ultimos(conn: sqlite3.Connection, acciones: tuple[str, ...], limite: int = 50) -> list[Evento]:
    """Los cambios más recientes de esas acciones (p. ej. DE_USUARIOS), del más nuevo al más viejo."""
    marcas = ", ".join("?" for _ in acciones)
    return [Evento(*fila) for fila in conn.execute(
        f"SELECT actor, accion, detalle, created_at FROM audit_log WHERE accion IN ({marcas}) ORDER BY id DESC LIMIT ?",
        (*acciones, limite))]
