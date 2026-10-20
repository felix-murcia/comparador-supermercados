"""Caso de uso: calcular el ahorro de una lista (A + C, `ADR-008`).

Reúne los precios actuales de cada producto de la lista en las cadenas
seleccionadas y aplica el cálculo puro del dominio.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from src.dominio.listas.ahorro import ItemConPrecios, ResumenAhorro, calcular_ahorro
from src.puertos.repositorios import (
    RepositorioCadenas,
    RepositorioListas,
    RepositorioPrecios,
)

logger = logging.getLogger(__name__)


class CalcularAhorroLista:
    """Calcula el ahorro de una lista en las cadenas seleccionadas."""

    def __init__(
        self,
        *,
        repositorio_listas: RepositorioListas,
        repositorio_precios: RepositorioPrecios,
        repositorio_cadenas: RepositorioCadenas,
    ) -> None:
        self._repositorio_listas = repositorio_listas
        self._repositorio_precios = repositorio_precios
        self._repositorio_cadenas = repositorio_cadenas

    async def ejecutar(self, lista_id: UUID, cadenas: Sequence[str]) -> ResumenAhorro:
        """Devuelve el coste, el % A por cadena y el % C de la lista."""
        items = await self._repositorio_listas.obtener_items_detallados(lista_id)
        datos: list[ItemConPrecios] = []

        for item in items:
            precios = await self._repositorio_precios.precios_actuales(
                item.item.producto_id
            )
            precios_por_cadena = {
                precio.cadena: precio.precio_eur
                for precio in precios
                if precio.cadena in cadenas
            }

            cadena_compra: str | None = None
            precio_compra = None
            if item.item.cadena_compra_id is not None:
                cadena = await self._repositorio_cadenas.obtener_por_id(
                    item.item.cadena_compra_id
                )
                if cadena is not None:
                    cadena_compra = cadena.slug
                    precio_compra = precios_por_cadena.get(cadena.slug)

            datos.append(
                ItemConPrecios(
                    producto_id=item.item.producto_id,
                    nombre=item.producto_nombre,
                    cantidad=item.item.cantidad,
                    precios=precios_por_cadena,
                    cadena_compra=cadena_compra,
                    precio_compra=precio_compra,
                )
            )

        return calcular_ahorro(datos, cadenas)
