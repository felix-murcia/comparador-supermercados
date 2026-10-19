"""Entidades y value objects del dominio de productos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.dominio.productos.errores import FormatoInvalidoError

UNIDADES_FORMATO = ("L", "ml", "kg", "g")


@dataclass(frozen=True)
class Formato:
    """Tamaño de un producto: cantidad en la unidad indicada."""

    litros_o_kg: Decimal
    unidad: str  # "L" | "ml" | "kg" | "g"

    def __post_init__(self) -> None:
        if self.unidad not in UNIDADES_FORMATO:
            raise FormatoInvalidoError(self.unidad)
        if self.litros_o_kg < 0:
            raise FormatoInvalidoError(self.litros_o_kg)

    def a_litros_o_kg(self) -> Decimal:
        """Normaliza a litros o kg: ml y g se dividen entre 1000."""
        if self.unidad in ("ml", "g"):
            return self.litros_o_kg / Decimal(1000)
        return self.litros_o_kg
