"""Implementación SQLAlchemy de `RepositorioBusquedas`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import busqueda_desde_modelo
from src.adaptadores.persistencia.modelos import BusquedaModelo
from src.dominio.busquedas.entidades import Busqueda, BusquedaNueva
from src.dominio.busquedas.estados import EstadoBusqueda


class SQLAlchemyRepositorioBusquedas:
    """Jobs de búsqueda asíncrona; las escrituras requieren sesión RW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def crear(self, datos: BusquedaNueva) -> Busqueda:
        modelo = BusquedaModelo(
            usuario_id=datos.usuario_id,
            query=datos.query,
            cadenas=list(datos.cadenas),
            provincia=datos.provincia,
            cache_key=datos.cache_key,
        )
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return busqueda_desde_modelo(modelo)

    async def obtener(self, busqueda_id: UUID) -> Busqueda | None:
        modelo = await self._session.get(BusquedaModelo, busqueda_id)
        if modelo is None:
            return None
        return busqueda_desde_modelo(modelo)

    async def obtener_por_cache_key(self, cache_key: str) -> Busqueda | None:
        modelo = await self._session.scalar(
            select(BusquedaModelo)
            .where(BusquedaModelo.cache_key == cache_key)
            .order_by(BusquedaModelo.creado_en.desc())
            .limit(1)
        )
        if modelo is None:
            return None
        return busqueda_desde_modelo(modelo)

    async def actualizar_estado(
        self,
        busqueda_id: UUID,
        estado: EstadoBusqueda,
        progreso: int,
        completado_en: datetime | None = None,
    ) -> Busqueda | None:
        modelo = await self._session.get(BusquedaModelo, busqueda_id)
        if modelo is None:
            return None
        modelo.estado = estado
        modelo.progreso = progreso
        if completado_en is not None:
            modelo.completado_en = completado_en
        await self._session.flush()
        await self._session.refresh(modelo)
        return busqueda_desde_modelo(modelo)
