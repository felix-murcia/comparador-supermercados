"""Implementación SQLAlchemy de `RepositorioPrecios` (append-only)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import precio_desde_modelo
from src.adaptadores.persistencia.modelos import PrecioModelo
from src.dominio.precios.entidades import PrecioNuevo, PrecioRegistrado


class SQLAlchemyRepositorioPrecios:
    """Solo `insertar` escribe; el histórico nunca se actualiza ni borra."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insertar(self, datos: PrecioNuevo) -> PrecioRegistrado:
        modelo = PrecioModelo(
            producto_cadena_id=datos.producto_cadena_id,
            precio_eur=datos.importe_eur,
            precio_por_litro_kg=datos.por_litro_kg,
            disponible=datos.disponible,
            promocion=datos.promocion,
            ambito=datos.ambito,
            provincia=datos.provincia,
            estado=datos.estado,
            url_fuente=datos.url_fuente,
            fecha_consulta=datos.fecha_consulta,
        )
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return precio_desde_modelo(modelo)

    async def ultimo_verificado(
        self, producto_cadena_id: UUID
    ) -> PrecioRegistrado | None:
        modelo = await self._session.scalar(
            select(PrecioModelo)
            .where(
                PrecioModelo.producto_cadena_id == producto_cadena_id,
                PrecioModelo.estado == "verificado",
            )
            .order_by(
                PrecioModelo.fecha_consulta.desc(),
                PrecioModelo.creado_en.desc(),
            )
            .limit(1)
        )
        if modelo is None:
            return None
        return precio_desde_modelo(modelo)

    async def historico(
        self, producto_cadena_id: UUID, limite: int = 10
    ) -> list[PrecioRegistrado]:
        modelos = (
            await self._session.scalars(
                select(PrecioModelo)
                .where(PrecioModelo.producto_cadena_id == producto_cadena_id)
                .order_by(
                    PrecioModelo.fecha_consulta.desc(),
                    PrecioModelo.creado_en.desc(),
                )
                .limit(limite)
            )
        ).all()
        return [precio_desde_modelo(modelo) for modelo in modelos]
