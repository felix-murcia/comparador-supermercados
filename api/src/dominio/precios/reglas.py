"""Reglas puras de precios, testeables sin mocks."""

from __future__ import annotations

from decimal import Decimal


def calcular_precio_por_litro(
    precio_eur: Decimal,
    litros_o_kg: Decimal,
) -> Decimal | None:
    """€/L o €/kg redondeado a 4 decimales; None si litros_o_kg <= 0."""
    if litros_o_kg <= 0:
        return None
    return (precio_eur / litros_o_kg).quantize(Decimal("0.0001"))
