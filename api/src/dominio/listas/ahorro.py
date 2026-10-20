"""Cálculo del ahorro de una lista de la compra.

Implementa las dos métricas de `ADR-008`:

* **A**: cuánto se ahorra comprando todo en una cadena frente a la más cara.
* **C**: cuánto se pierde por no comprar en el supermercado más barato.

Es lógica pura: no toca la base de datos ni depende de ningún framework.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

PRECISION = Decimal("0.0001")
CERO = Decimal(0)


@dataclass(frozen=True)
class ItemConPrecios:
    """Producto de la lista con su precio actual en cada cadena."""

    producto_id: UUID
    nombre: str
    cantidad: int
    precios: Mapping[str, Decimal]
    cadena_compra: str | None = None
    precio_compra: Decimal | None = None


@dataclass(frozen=True)
class CosteCadena:
    """Coste de comprar toda la lista en una cadena."""

    cadena: str
    coste: Decimal
    porcentaje_a: Decimal | None = None
    productos_no_disponibles: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResumenAhorro:
    """Resumen del ahorro de la lista: coste, % A por cadena y % C."""

    coste_total: Decimal
    por_cadena: tuple[CosteCadena, ...]
    coste_optimo: Decimal
    coste_mixta_real: Decimal
    porcentaje_c: Decimal | None = None
    avisos: tuple[str, ...] = ()


def _porcentaje(diferencia: Decimal, base: Decimal) -> Decimal | None:
    """`(diferencia / base)` redondeado a 4 decimales; `None` si la base es 0."""
    if base == 0:
        return None
    return (diferencia / base).quantize(PRECISION, rounding=ROUND_HALF_UP)


def calcular_ahorro(
    items: Sequence[ItemConPrecios], cadenas: Sequence[str]
) -> ResumenAhorro:
    """Calcula el ahorro de la lista en las cadenas seleccionadas.

    Reglas de `ADR-008`: los productos que no están disponibles en una cadena
    se excluyen de esa cadena (con aviso), los que no están en ninguna se
    excluyen de todo el cálculo, con una sola cadena el % A no aplica y con
    `coste_mixta_real == 0` el % C no aplica.
    """
    avisos: list[str] = []
    costes: dict[str, Decimal] = {cadena: CERO for cadena in cadenas}
    no_disponibles: dict[str, list[str]] = {cadena: [] for cadena in cadenas}
    coste_optimo = CERO
    coste_mixta_real = CERO

    for item in items:
        precios_seleccionados = {
            cadena: precio
            for cadena, precio in item.precios.items()
            if cadena in costes
        }

        if not precios_seleccionados:
            avisos.append(
                f"«{item.nombre}» no está disponible en las cadenas elegidas "
                "y se ha excluido del cálculo"
            )
            continue

        for cadena, precio in precios_seleccionados.items():
            costes[cadena] += precio * item.cantidad

        for cadena in costes:
            if cadena not in precios_seleccionados:
                no_disponibles[cadena].append(item.nombre)

        coste_optimo += min(precios_seleccionados.values()) * item.cantidad

        if item.cadena_compra and item.cadena_compra in precios_seleccionados:
            precio_compra = item.precio_compra
            if precio_compra is None:
                precio_compra = precios_seleccionados[item.cadena_compra]
            coste_mixta_real += precio_compra * item.cantidad

    coste_mas_cara = max(costes.values(), default=CERO)
    solo_una_cadena = len(cadenas) < 2

    por_cadena = tuple(
        CosteCadena(
            cadena=cadena,
            coste=costes[cadena],
            porcentaje_a=(
                None
                if solo_una_cadena
                else _porcentaje(coste_mas_cara - costes[cadena], coste_mas_cara)
            ),
            productos_no_disponibles=tuple(no_disponibles[cadena]),
        )
        for cadena in cadenas
    )

    for cadena in cadenas:
        if no_disponibles[cadena]:
            avisos.append(
                f"En «{cadena}» no hay precio para: {', '.join(no_disponibles[cadena])}"
            )

    return ResumenAhorro(
        coste_total=coste_mixta_real,
        por_cadena=por_cadena,
        coste_optimo=coste_optimo,
        coste_mixta_real=coste_mixta_real,
        porcentaje_c=_porcentaje(coste_mixta_real - coste_optimo, coste_mixta_real),
        avisos=tuple(avisos),
    )
