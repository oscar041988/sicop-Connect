"""Bloqueo de archivo: impide que dos ciclos corran a la vez (lección 8).

Se usa el bloqueo del sistema operativo (fcntl en Linux, msvcrt en Windows), no la mera existencia del
archivo: si el proceso se cae o se apaga el equipo, el sistema suelta el bloqueo solo y el siguiente ciclo
no queda trabado. El archivo guarda quién lo tiene (hora y proceso) para el mensaje del segundo ciclo.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

# En Windows se bloquea un byte lejos del inicio: así el texto de la hora y el proceso se puede leer igual.
_POSICION = 1 << 20


class CicloOcupado(Exception):
    """Otro proceso tiene el bloqueo. El mensaje dice quién, si se pudo leer."""


if os.name == "nt":
    import msvcrt

    def _tomar(fd: int) -> bool:
        os.lseek(fd, _POSICION, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _soltar(fd: int) -> None:
        os.lseek(fd, _POSICION, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _tomar(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _soltar(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _leer(fd: int) -> str:
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        return os.read(fd, 500).decode("utf-8", "replace").strip()
    except OSError:
        return ""


@contextmanager
def bloqueo(path: Path, quien: str):
    """Toma el bloqueo o lanza CicloOcupado sin esperar. `quien` se escribe en el archivo mientras dura."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if not _tomar(fd):
            raise CicloOcupado(_leer(fd))
        try:
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, quien.encode("utf-8"))
            yield
        finally:
            _soltar(fd)
    finally:
        os.close(fd)
