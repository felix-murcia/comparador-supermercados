"""Reglas puras de formato de producto."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from src.dominio.productos.entidades import Formato

_PATRON_FORMATO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(l|ml|kg|g)\b")

_UNIDADES = {"l": "L", "ml": "ml", "kg": "kg", "g": "g"}


def parsear_formato(texto: str | None) -> Formato | None:
    """Convierte "1L", "500 g" o "1,5 L" en `Formato`; None si no se entiende."""
    if not texto:
        return None

    coincidencia = _PATRON_FORMATO.search(texto.strip().lower())
    if not coincidencia:
        return None

    try:
        cantidad = Decimal(coincidencia.group(1).replace(",", "."))
    except InvalidOperation:
        return None

    return Formato(litros_o_kg=cantidad, unidad=_UNIDADES[coincidencia.group(2)])


def familia_unidad(unidad: str) -> str:
    """Familia de la unidad para comparar precios: "l" (volumen) o "kg" (masa)."""
    return "l" if unidad in ("L", "ml") else "kg"
