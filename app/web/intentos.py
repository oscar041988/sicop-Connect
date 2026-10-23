"""Límite de intentos de login (contra la fuerza bruta: probar miles de contraseñas seguidas).

Se cuenta por correo + IP: así un atacante bloquea su propia computadora, no la cuenta de otra persona.
Tras MAX_FALLOS fallos dentro de VENTANA, ese par queda bloqueado durante BLOQUEO, aunque la contraseña sea
correcta. Entrar bien pone el contador en cero.

El contador vive en la memoria del proceso (opción A, decidida por Ivania el 2026-10-12): se pierde al reiniciar
la app, lo que solo regala MAX_FALLOS intentos más. Sirve porque la app corre en un solo proceso.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

MAX_FALLOS = 5
VENTANA = 15 * 60   # segundos en los que se cuentan los fallos
BLOQUEO = 15 * 60   # segundos de bloqueo al llegar a MAX_FALLOS
MAX_CLAVES = 10_000  # tope de pares guardados, para que un ataque con muchas IP no llene la memoria


class LimiteIntentos:
    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._fallos: dict[tuple[str, str], list[float]] = {}
        self._bloqueados: dict[tuple[str, str], float] = {}
        # Las rutas síncronas de FastAPI corren en varios hilos: el candado evita que dos peticiones
        # a la vez pierdan un fallo al contarlo.
        self._candado = threading.Lock()

    @staticmethod
    def clave(email: str, ip: str) -> tuple[str, str]:
        return email.strip().lower(), ip

    def segundos_de_bloqueo(self, clave: tuple[str, str]) -> int:
        """Segundos que faltan para poder intentar otra vez (0 = no está bloqueado)."""
        with self._candado:
            hasta = self._bloqueados.get(clave)
            if hasta is None:
                return 0
            faltan = hasta - self._reloj()
            if faltan <= 0:
                del self._bloqueados[clave]
                return 0
            return int(faltan) + 1

    def registrar_fallo(self, clave: tuple[str, str]) -> bool:
        """Anota un fallo; devuelve True si con este fallo el par queda bloqueado."""
        with self._candado:
            ahora = self._reloj()
            # Se cuentan las dos listas: un ataque con muchas IP llena los bloqueos, no los fallos (cada clave
            # bloqueada sale de los fallos), y antes los bloqueos crecían sin tope.
            if len(self._fallos) + len(self._bloqueados) >= MAX_CLAVES:
                self._olvidar_viejos(ahora)
            recientes = [t for t in self._fallos.get(clave, []) if ahora - t < VENTANA]
            recientes.append(ahora)
            if len(recientes) >= MAX_FALLOS:
                self._fallos.pop(clave, None)
                self._bloqueados[clave] = ahora + BLOQUEO
                return True
            self._fallos[clave] = recientes
            return False

    def registrar_exito(self, clave: tuple[str, str]) -> None:
        with self._candado:
            self._fallos.pop(clave, None)

    def _olvidar_viejos(self, ahora: float) -> None:
        self._fallos = {c: f for c, f in self._fallos.items() if ahora - f[-1] < VENTANA}
        self._bloqueados = {c: h for c, h in self._bloqueados.items() if h > ahora}
        if len(self._fallos) >= MAX_CLAVES // 2:  # todos recientes: se descartan los más viejos
            for c in sorted(self._fallos, key=lambda c: self._fallos[c][-1])[: len(self._fallos) - MAX_CLAVES // 4]:
                del self._fallos[c]
        if len(self._bloqueados) >= MAX_CLAVES // 2:
            # Todos vigentes: se sueltan los que vencen antes. Ese par podría volver a probar antes de tiempo,
            # pero solo pasa durante un ataque con miles de IP y es mejor que quedarse sin memoria.
            for c in sorted(self._bloqueados, key=self._bloqueados.get)[: len(self._bloqueados) - MAX_CLAVES // 4]:
                del self._bloqueados[c]
