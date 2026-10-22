"""Caso de uso: calcular el ahorro de una lista (A + C, `ADR-008`).

Reúne los precios actuales de cada producto de la lista en las cadenas
seleccionadas y aplica el cálculo puro del dominio.

Un producto comprado en una cadena no está en las demás: el artículo de DIA
no lo vende Carrefour. Para que la comparación signifique algo, cuando falta
el producto se busca su equivalente en la otra cadena (el mismo producto de
marca propia), según `ADR-026`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from src.dominio.listas.ahorro import (
    Equivalente,
    ItemConPrecios,
    ResumenAhorro,
    calcular_ahorro,
)
from src.dominio.precios.entidades import ProductoEnCadena
from src.dominio.productos.entidades import DescripcionProducto
from src.dominio.productos.reglas import es_equivalente, nombre_generico
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

        # Productos de las cadenas elegidas con su precio, para buscar
        # equivalentes. Se piden por categoría porque acota mucho el
        # conjunto; el resto de filtros van en el dominio.
        categorias = {
            item.producto_categoria for item in items if item.producto_categoria
        }
        candidatos = await self._repositorio_precios.productos_con_precio(
            categorias=sorted(categorias),
            cadenas=list(cadenas),
        )

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

            descripcion = DescripcionProducto(
                nombre=item.producto_nombre or "",
                marca=item.producto_marca,
                categoria=item.producto_categoria,
                litros_o_kg=item.producto_litros_o_kg,
                formato=item.producto_formato,
            )

            datos.append(
                ItemConPrecios(
                    producto_id=item.item.producto_id,
                    nombre=item.producto_nombre,
                    cantidad=item.item.cantidad,
                    precios=precios_por_cadena,
                    cadena_compra=cadena_compra,
                    precio_compra=precio_compra,
                    nombre_base=nombre_generico(
                        item.producto_nombre or "",
                        item.producto_marca,
                        item.producto_formato,
                    ),
                    equivalentes=self._equivalentes(
                        descripcion,
                        precios_por_cadena,
                        candidatos,
                    ),
                )
            )

        seleccion = list(cadenas)
        if not seleccion:
            # Sin selección explícita, se comparan las cadenas donde hay precio.
            seleccion = sorted({cadena for item in datos for cadena in item.precios})

        return calcular_ahorro(datos, seleccion)

    def _equivalentes(
        self,
        descripcion: DescripcionProducto,
        precios_por_cadena: dict[str, Decimal],
        candidatos: Sequence[ProductoEnCadena],
    ) -> dict[str, Equivalente]:
        """Equivalente más barato de cada cadena donde falta el producto.

        Solo se busca en cadenas donde el producto no está: si está, su precio
        exacto es mejor que cualquier equivalente.
        """
        if not descripcion.nombre:
            return {}

        equivalentes: dict[str, Equivalente] = {}
        for candidato in candidatos:
            if candidato.cadena in precios_por_cadena:
                continue
            if (
                candidato.cadena in equivalentes
                and candidato.precio_eur >= equivalentes[candidato.cadena].precio
            ):
                # Ya hay un equivalente más barato en esa cadena.
                continue
            otro = DescripcionProducto(
                nombre=candidato.nombre,
                marca=candidato.marca,
                categoria=candidato.categoria,
                litros_o_kg=candidato.litros_o_kg,
                formato=candidato.formato,
            )
            if not es_equivalente(descripcion, otro):
                continue
            equivalentes[candidato.cadena] = Equivalente(
                nombre=candidato.nombre,
                precio=candidato.precio_eur,
                marca=candidato.marca,
            )
        return equivalentes
