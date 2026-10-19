"""Entidades y value objects del dominio de precios."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.dominio.precios.errores import PrecioInvalidoError


@dataclass(frozen=True)
class Precio:
    """Precio de un producto en una cadena: importe y €/L o €/kg."""

    importe_eur: Decimal
    por_litro_kg: Decimal | None = None

    def __post_init__(self) -> None:
        if self.importe_eur < 0:
            raise PrecioInvalidoError("importe_eur no puede ser negativo")
        if self.por_litro_kg is not None and self.por_litro_kg < 0:
            raise PrecioInvalidoError("por_litro_kg no puede ser negativo")
