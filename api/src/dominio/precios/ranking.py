"""Ranking de resultados de comparación.

El €/L se calcula con 4 decimales (valor de la base de datos); el redondeo a
2 decimales para la interfaz es responsabilidad del frontend.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal

from src.dominio.precios.entidades import ResultadoComparacion
from src.dominio.precios.estados import ORDEN_POR_DEFECTO, Orden


def _clave_precio_unitario(resultado: ResultadoComparacion) -> tuple[object, ...]:
    return (resultado.precio_eur, resultado.nombre, resultado.cadena)


def _clave_precio_kg_l(resultado: ResultadoComparacion) -> tuple[object, ...]:
    precio = resultado.precio_por_litro_kg
    return (precio is None, precio or Decimal(0), resultado.nombre, resultado.cadena)


def ordenar_resultados(
    resultados: Sequence[ResultadoComparacion], orden: Orden
) -> list[ResultadoComparacion]:
    """Ordena los resultados según el criterio pedido.

    El desempate es estable: a igualdad de precio decide el nombre del
    producto y después la cadena. Con `relevancia` el orden lo decide el
    repositorio (conoce la similitud con la consulta) y aquí solo se respeta.
    """
    if orden == "precio_unitario":
        return sorted(resultados, key=_clave_precio_unitario)
    if orden == "precio_kg_l":
        return sorted(resultados, key=_clave_precio_kg_l)
    return list(resultados)


def posicionar(
    resultados: Sequence[ResultadoComparacion],
    orden: Orden = ORDEN_POR_DEFECTO,
    offset: int = 0,
) -> list[ResultadoComparacion]:
    """Ordena y numera los resultados (1 = primero) según el desplazamiento."""
    ordenados = ordenar_resultados(resultados, orden)
    return [
        replace(resultado, posicion=offset + indice + 1)
        for indice, resultado in enumerate(ordenados)
    ]
