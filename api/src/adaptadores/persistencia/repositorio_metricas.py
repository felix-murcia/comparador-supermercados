"""Implementación SQLAlchemy de `RepositorioMetricas`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import IngestaMetricasModelo
from src.dominio.ingesta.entidades import MetricaIngesta, MetricasIngesta

TOP_MOTIVOS = 10


class SQLAlchemyRepositorioMetricas:
    """Registra y resume las métricas de la ingesta."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def registrar(self, metrica: MetricaIngesta) -> None:
        modelo = IngestaMetricasModelo(
            producto_cadena_id=metrica.producto_cadena_id,
            cadena=metrica.cadena,
            estado=metrica.estado,
            motivo=metrica.motivo,
        )
        self._session.add(modelo)
        await self._session.flush()

    async def resumen(self, desde: datetime | None = None) -> MetricasIngesta:
        filtros = []
        if desde is not None:
            filtros.append(IngestaMetricasModelo.creado_en >= desde)

        por_estado = {
            estado: total
            for estado, total in (
                await self._session.execute(
                    select(IngestaMetricasModelo.estado, func.count())
                    .where(*filtros)
                    .group_by(IngestaMetricasModelo.estado)
                )
            ).all()
        }

        motivos = (
            await self._session.execute(
                select(IngestaMetricasModelo.motivo, func.count())
                .where(*filtros, IngestaMetricasModelo.motivo.is_not(None))
                .group_by(IngestaMetricasModelo.motivo)
                .order_by(func.count().desc(), IngestaMetricasModelo.motivo)
                .limit(TOP_MOTIVOS)
            )
        ).all()

        return MetricasIngesta(
            total=sum(por_estado.values()),
            verificado=por_estado.get("verificado", 0),
            sospechoso=por_estado.get("sospechoso", 0),
            rechazado=por_estado.get("rechazado", 0),
            motivos=tuple((str(motivo), total) for motivo, total in motivos),
        )
