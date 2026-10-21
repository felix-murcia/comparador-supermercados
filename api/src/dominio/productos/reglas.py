"""Reglas puras de formato de producto."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from src.dominio.normalizacion import normalizar_texto
from src.dominio.productos.entidades import Formato

_PATRON_FORMATO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(l|ml|kg|g)\b")

# Espacio entre la cantidad y la unidad: "1 L" y "1L" son el mismo producto.
# Se cubren todas las unidades que usan los retailers (litros, kilos, gramos,
# mililitros, unidades, rollos...). El "x" del multiplicador ("4x120 g") se
# deja aparte: no es una unidad.
_ESPACIO_ANTES_UNIDAD = re.compile(r"(\d)\s+(?!x\b)([a-záéíóúñ]+)\b")

# Multiplicador sin espacio: "4x120 g" y "4 x 120 g" son el mismo formato.
_MULTIPLICADOR = re.compile(r"(\d)\s*x\s*(\d)")

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


def normalizar_nombre(texto: str) -> str:
    """Minúsculas, sin tildes y sin espacios repetidos, para comparar nombres.

    Además quita el espacio entre la cantidad y la unidad ("1 L" y "1L" son el
    mismo producto): los retailers escriben la unidad de las dos formas y, sin
    esta normalización, la ingesta crearía dos productos distintos para el
    mismo artículo y el precio se quedaría solo en uno de ellos.

    La base de datos aplica la misma normalización en la función
    `nombre_buscable_normalizado` (migración 0004), que es la que usa la
    búsqueda por texto completo. `test_normalizar_nombre_coincide_con_sql`
    comprueba que las dos coinciden.
    """
    normalizado = normalizar_texto(texto)
    normalizado = _MULTIPLICADOR.sub(r"\1x\2", normalizado)
    return _ESPACIO_ANTES_UNIDAD.sub(r"\1\2", normalizado)
