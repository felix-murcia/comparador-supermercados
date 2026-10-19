"""Implementación SQLAlchemy de `RepositorioProductosCadenas`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import ProductoCadenaModelo


class SQLAlchemyRepositorioProductosCadenas:
    """Relación producto ↔ cadena; las escrituras requieren sesión RW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener_por_producto_y_cadena(
        self, producto_id: UUID, cadena_id: UUID
    ) -> UUID | None:
        modelo = await self._session.scalar(
            select(ProductoCadenaModelo)
            .where(
                ProductoCadenaModelo.producto_id == producto_id,
                ProductoCadenaModelo.cadena_id == cadena_id,
            )
            .limit(1)
        )
        if modelo is None:
            return None
        return modelo.id

    async def crear(
        self,
        producto_id: UUID,
        cadena_id: UUID,
        url_producto: str,
        nombre_en_cadena: str,
    ) -> UUID:
        modelo = ProductoCadenaModelo(
            producto_id=producto_id,
            cadena_id=cadena_id,
            url_producto=url_producto,
            nombre_en_cadena=nombre_en_cadena,
        )
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return modelo.id
