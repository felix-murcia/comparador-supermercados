"""Repara productos duplicados en la base de datos.

Antes de normalizar el nombre del producto, la ingesta creaba dos filas para
el mismo artículo cuando el retailer escribía la unidad con y sin espacio
("Leche entera Pascual 1L" y "Leche entera Pascual 1 L"). Cada fila se
quedaba con una parte de los precios y la comparativa mostraba el producto
duplicado.

El script agrupa los productos por su nombre normalizado y fusiona cada grupo
en una sola fila:

- Se conserva el producto con EAN (es el identificador real del retailer) o,
  si varios lo tienen, el más antiguo.
- **Los precios no se tocan nunca**: la tabla `precios` es append-only y hay
  un trigger en la base de datos que lo impide. Lo que se mueve es la ficha
  (`productos_cadena`), que es lo que agrupa los precios de una cadena. Si el
  superviviente ya tenía ficha en esa cadena y estaba vacía, se elimina su
  ficha y se le pasa la del duplicado, con sus precios intactos.
- Los productos que se quedan sin precios ni fichas se eliminan.

Es idempotente: si no hay duplicados, no hace nada.

Uso:
    python -m scripts.reparar_duplicados
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.engines import dispose_engines, get_sessionmaker_rw
from src.adaptadores.persistencia.modelos import (
    PrecioModelo,
    ProductoCadenaModelo,
    ProductoModelo,
)
from src.dominio.productos.reglas import normalizar_nombre

logger = logging.getLogger(__name__)


async def _grupos_duplicados(sesion: AsyncSession) -> dict[str, list[ProductoModelo]]:
    """Productos agrupados por nombre normalizado, solo los que se repiten."""
    productos = (
        await sesion.scalars(
            select(ProductoModelo).order_by(ProductoModelo.creado_en, ProductoModelo.id)
        )
    ).all()

    grupos: dict[str, list[ProductoModelo]] = defaultdict(list)
    for producto in productos:
        grupos[normalizar_nombre(producto.nombre)].append(producto)

    return {clave: grupo for clave, grupo in grupos.items() if len(grupo) > 1}


def _elegir_superviviente(grupo: list[ProductoModelo]) -> ProductoModelo:
    """El que se conserva: el del EAN; si hay varios, el más antiguo."""
    con_ean = [p for p in grupo if p.ean]
    if con_ean:
        return min(con_ean, key=lambda p: (p.creado_en, str(p.id)))
    return min(grupo, key=lambda p: (p.creado_en, str(p.id)))


async def _precios_de_ficha(sesion: AsyncSession, ficha_id: UUID) -> int:
    return (
        await sesion.scalar(
            select(func.count())
            .select_from(PrecioModelo)
            .where(PrecioModelo.producto_cadena_id == ficha_id)
        )
    ) or 0


async def _fichas_por_cadena(
    sesion: AsyncSession, productos: list[ProductoModelo]
) -> dict[UUID, list[ProductoCadenaModelo]]:
    fichas = (
        await sesion.scalars(
            select(ProductoCadenaModelo).where(
                ProductoCadenaModelo.producto_id.in_([p.id for p in productos])
            )
        )
    ).all()
    por_cadena: dict[UUID, list[ProductoCadenaModelo]] = defaultdict(list)
    for ficha in fichas:
        por_cadena[ficha.cadena_id].append(ficha)
    return por_cadena


async def _fusionar(
    sesion: AsyncSession, grupo: list[ProductoModelo]
) -> tuple[int, int]:
    """Fusiona un grupo de duplicados. Devuelve (productos, fichas) eliminados."""
    superviviente = _elegir_superviviente(grupo)
    otros = [p for p in grupo if p.id != superviviente.id]
    if not otros:
        return 0, 0

    por_cadena = await _fichas_por_cadena(sesion, grupo)
    productos_eliminados = 0
    fichas_eliminadas = 0

    for otro in otros:
        for cadena_id, fichas in por_cadena.items():
            propias = [f for f in fichas if f.producto_id == otro.id]
            if not propias:
                continue
            del_superviviente = next(
                (f for f in fichas if f.producto_id == superviviente.id), None
            )
            for ficha in propias:
                if del_superviviente is None:
                    # El superviviente no tenía ficha en esta cadena: se le
                    # pasa la ficha con sus precios (no se tocan).
                    await sesion.execute(
                        update(ProductoCadenaModelo)
                        .where(ProductoCadenaModelo.id == ficha.id)
                        .values(producto_id=superviviente.id)
                    )
                    continue
                precios = await _precios_de_ficha(sesion, del_superviviente.id)
                if precios:
                    # Ambas fichas tienen precios: no se pueden fusionar sin
                    # tocar `precios` (append-only). Se deja como está.
                    logger.warning(
                        "No se fusionan las fichas de %s: ambas tienen precios.",
                        cadena_id,
                    )
                    continue
                # La ficha del superviviente está vacía: se elimina y se le
                # pasa la del duplicado, con sus precios intactos.
                await sesion.execute(
                    delete(ProductoCadenaModelo).where(
                        ProductoCadenaModelo.id == del_superviviente.id
                    )
                )
                await sesion.execute(
                    update(ProductoCadenaModelo)
                    .where(ProductoCadenaModelo.id == ficha.id)
                    .values(producto_id=superviviente.id)
                )
                fichas_eliminadas += 1

    # Los productos que se quedan sin fichas ni precios se eliminan.
    for otro in otros:
        quedan = await sesion.scalar(
            select(func.count())
            .select_from(ProductoCadenaModelo)
            .where(ProductoCadenaModelo.producto_id == otro.id)
        )
        if quedan:
            continue
        await sesion.execute(delete(ProductoModelo).where(ProductoModelo.id == otro.id))
        productos_eliminados += 1

    return productos_eliminados, fichas_eliminadas


async def reparar() -> tuple[int, int]:
    """Fusiona los duplicados. Devuelve (productos, fichas) eliminados."""
    sessionmaker = get_sessionmaker_rw()
    async with sessionmaker() as sesion:
        grupos = await _grupos_duplicados(sesion)
        if not grupos:
            logger.info("No hay productos duplicados.")
            return 0, 0

        productos = 0
        fichas = 0
        for clave, grupo in grupos.items():
            logger.info("Fusionando %d productos de %r", len(grupo), clave)
            eliminados, fichas_eliminadas = await _fusionar(sesion, grupo)
            productos += eliminados
            fichas += fichas_eliminadas

        await sesion.commit()

    logger.info(
        "Reparación terminada: %d productos y %d fichas eliminados.",
        productos,
        fichas,
    )
    return productos, fichas


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    try:
        await reparar()
    finally:
        await dispose_engines()


if __name__ == "__main__":
    asyncio.run(main())
