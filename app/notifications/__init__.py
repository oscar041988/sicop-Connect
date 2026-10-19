"""Proveedores de correo. Las excepciones viven aquí para que app/avisos.py no dependa de Google."""


class EnvioRechazado(Exception):
    """El proveedor respondió que no: el correo no salió (estado «fallido»)."""


class EnvioIncierto(Exception):
    """Sin respuesta clara: quizá salió (estado «incierto»). Se revisa antes de reintentar."""
