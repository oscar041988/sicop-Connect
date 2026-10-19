"""Dinero exacto: Decimal siempre acompañado de su moneda. Nunca se suman monedas distintas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

# Formato de SICOP observado: punto decimal, sin separador de miles, sin signo (docs/MAPEO_DATOS.md).
_DECIMAL_SICOP = re.compile(r"^\d+(?:\.\d+)?$")
_MONEDA = re.compile(r"^[A-Z]{3}$")


class MonedasDistintasError(ValueError):
    """Se intentó sumar montos en monedas distintas."""


def parse_decimal(texto: str) -> Decimal:
    """Convierte «1234.50» en Decimal exacto. Rechaza comas, miles, signos y notación científica."""
    if not _DECIMAL_SICOP.match(texto):
        raise ValueError(f"{texto!r} no es un número con punto decimal")
    return Decimal(texto)


def texto_decimal(valor: Decimal) -> str:
    """Decimal → texto sin notación científica («1280200», «150.375»)."""
    return format(valor, "f")


@dataclass(frozen=True)
class Monto:
    valor: Decimal
    moneda: str

    def __post_init__(self) -> None:
        if not isinstance(self.valor, Decimal):
            raise TypeError("El valor de un Monto debe ser Decimal (nunca float)")
        if not _MONEDA.match(self.moneda):
            raise ValueError(f"Moneda no válida: {self.moneda!r}")

    def __add__(self, otro: Monto) -> Monto:
        if self.moneda != otro.moneda:
            raise MonedasDistintasError(f"No se suman {self.moneda} y {otro.moneda}")
        return Monto(self.valor + otro.valor, self.moneda)


def totales_por_moneda(montos: Iterable[Monto]) -> dict[str, Monto]:
    """Un total separado por cada moneda: {'CRC': Monto(...), 'USD': Monto(...)}."""
    totales: dict[str, Monto] = {}
    for monto in montos:
        totales[monto.moneda] = totales[monto.moneda] + monto if monto.moneda in totales else monto
    return dict(sorted(totales.items()))
