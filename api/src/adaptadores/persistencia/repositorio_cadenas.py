"""Implementación SQLAlchemy de `RepositorioCadenas`."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import cadena_desde_modelo
from src.adaptadores.persistencia.modelos import CadenaModelo
from src.dominio.cadenas.entidades import Cadena


class SQLAlchemyRepositorioCadenas:
    """Lecturas del catálogo de cadenas."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener_por_slug(self, slug: str) -> Cadena | None:
        modelo = await self._session.scalar(
            select(CadenaModelo).where(CadenaModelo.slug == slug).limit(1)
        )
        if modelo is None:
            return None
        return cadena_desde_modelo(modelo)
