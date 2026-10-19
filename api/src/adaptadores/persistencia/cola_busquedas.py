"""Cola de jobs sobre la tabla `busquedas` (ADR-007)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import busqueda_desde_modelo
from src.adaptadores.persistencia.modelos import BusquedaModelo
from src.dominio.busquedas.entidades import Busqueda


class PostgresColaJobs:
    """Reclama jobs pendientes con `FOR UPDATE SKIP LOCKED`.

    Un job en `en_progreso` cuyo `creado_en` es anterior al timeout se vuelve a
    reclamar: así, si el worker cae a mitad de un job, otro lo retoma.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def reclamar(self, timeout_minutos: int) -> Busqueda | None:
        limite = datetime.now(UTC) - timedelta(minutes=timeout_minutos)
        candidatos = (
            select(BusquedaModelo.id)
            .where(
                or_(
                    BusquedaModelo.estado == "pendiente",
                    and_(
                        BusquedaModelo.estado == "en_progreso",
                        BusquedaModelo.creado_en < limite,
                    ),
                )
            )
            .order_by(BusquedaModelo.creado_en)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        sentencia = (
            update(BusquedaModelo)
            .where(BusquedaModelo.id == candidatos.scalar_subquery())
            .values(estado="en_progreso", progreso=0)
            .returning(BusquedaModelo)
            .execution_options(synchronize_session="fetch")
        )

        modelo = (await self._session.execute(sentencia)).scalars().one_or_none()
        if modelo is None:
            return None
        return busqueda_desde_modelo(modelo)

    async def contar_pendientes(self) -> int:
        """Jobs que aún no han terminado (pendientes o en progreso)."""
        total = await self._session.scalar(
            select(func.count())
            .select_from(BusquedaModelo)
            .where(BusquedaModelo.estado.in_(("pendiente", "en_progreso")))
        )
        return int(total or 0)
