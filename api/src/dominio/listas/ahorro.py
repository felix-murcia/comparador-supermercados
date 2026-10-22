"""Cálculo del ahorro de una lista de la compra.

Implementa las dos métricas de `ADR-008`:

* **A**: cuánto se ahorra comprando todo en una cadena frente a la más cara.
* **C**: cuánto se pierde por no comprar en el supermercado más barato.

Es lógica pura: no toca la base de datos ni depende de ningún framework.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

PRECISION = Decimal("0.0001")
CERO = Decimal(0)


@dataclass(frozen=True)
class Equivalente:
    """Producto de otra cadena que cubre la misma necesidad de compra."""

    nombre: str
    precio: Decimal
    marca: str | None = None


@dataclass(frozen=True)
class ItemConPrecios:
    """Producto de la lista con su precio actual en cada cadena."""

    producto_id: UUID
    nombre: str
    cantidad: int
    precios: Mapping[str, Decimal]
    cadena_compra: str | None = None
    precio_compra: Decimal | None = None
    # Nombre sin marca, para los avisos: «Leche desnatada 1 L» en vez de
    # «Leche desnatada Dia Láctea 1 L».
    nombre_base: str = ""
    # Equivalente usado en cada cadena, cuando el producto no está en ella.
    equivalentes: Mapping[str, Equivalente] = field(default_factory=dict)


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

    Cuando el producto no está en una cadena pero sí tiene un equivalente
    (`ADR-026`), se compara con el equivalente: el artículo concreto es de
    una marca que la otra cadena no vende, pero la necesidad de compra sí
    existe allí. El aviso dice con qué se ha comparado.
    """
    avisos: list[str] = []
    costes: dict[str, Decimal] = {cadena: CERO for cadena in cadenas}
    no_disponibles: dict[str, list[str]] = {cadena: [] for cadena in cadenas}
    sustituciones: dict[str, list[tuple[str, str, Equivalente]]] = {
        cadena: [] for cadena in cadenas
    }
    coste_optimo = CERO
    coste_mixta_real = CERO

    for item in items:
        precios_seleccionados = {
            cadena: precio
            for cadena, precio in item.precios.items()
            if cadena in costes
        }
        nombre_aviso = item.nombre_base or item.nombre

        if not precios_seleccionados and not item.equivalentes:
            avisos.append(
                f"«{item.nombre}» no está disponible en las cadenas elegidas "
                "y se ha excluido del cálculo"
            )
            continue

        for cadena, precio in precios_seleccionados.items():
            costes[cadena] += precio * item.cantidad

        for cadena in costes:
            if cadena in precios_seleccionados:
                continue
            equivalente = item.equivalentes.get(cadena)
            if equivalente is None:
                no_disponibles[cadena].append(nombre_aviso)
                continue
            costes[cadena] += equivalente.precio * item.cantidad
            sustituciones[cadena].append((nombre_aviso, item.nombre, equivalente))

        # El óptimo es el precio más bajo de la necesidad, venga del producto
        # exacto o de un equivalente.
        candidatos = [*precios_seleccionados.values()]
        candidatos.extend(
            equivalente.precio
            for cadena, equivalente in item.equivalentes.items()
            if cadena in costes
        )
        if candidatos:
            coste_optimo += min(candidatos) * item.cantidad

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
        for nombre_aviso, _original, equivalente in sustituciones[cadena]:
            marca = f" ({equivalente.marca})" if equivalente.marca else ""
            avisos.append(
                f"En «{cadena}», «{nombre_aviso}» se ha comparado con "
                f"«{equivalente.nombre}»{marca}"
            )
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
