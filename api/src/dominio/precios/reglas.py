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


def desviacion_relativa(nuevo: Decimal, anterior: Decimal) -> Decimal:
    """Diferencia relativa entre dos precios; 0 si el precio anterior es 0."""
    if anterior == 0:
        return Decimal(0)
    return abs(nuevo - anterior) / anterior


def es_coherente_por_unidad(
    calculado: Decimal,
    referencia: Decimal,
    tolerancia: Decimal = Decimal("0.05"),
) -> bool:
    """True si el precio por unidad no se desvía más que la tolerancia."""
    if referencia == 0:
        return True
    return desviacion_relativa(calculado, referencia) <= tolerancia
