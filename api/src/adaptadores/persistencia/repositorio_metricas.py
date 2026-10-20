"""Implementación SQLAlchemy de `RepositorioMetricas`."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import IngestaMetricasModelo
from src.dominio.ingesta.entidades import (
    MetricaDia,
    MetricaIngesta,
    MetricasIngesta,
)

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
        """Reparto por estado y motivos más frecuentes."""
        condiciones = []
        if desde is not None:
            condiciones.append(IngestaMetricasModelo.creado_en >= desde)

        por_estado = {
            estado: total
            for estado, total in (
                await self._session.execute(
                    select(IngestaMetricasModelo.estado, func.count())
                    .where(*condiciones)
                    .group_by(IngestaMetricasModelo.estado)
                )
            ).all()
        }

        motivos = (
            await self._session.execute(
                select(IngestaMetricasModelo.motivo, func.count())
                .where(*condiciones, IngestaMetricasModelo.motivo.is_not(None))
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

    async def resumen_por_dia(self, dias: int) -> list[MetricaDia]:
        """Reparto por estado y día (para las gráficas del panel interno)."""
        desde = datetime.now(UTC) - timedelta(days=dias)
        filas = (
            await self._session.execute(
                select(
                    func.date_trunc("day", IngestaMetricasModelo.creado_en).label(
                        "dia"
                    ),
                    IngestaMetricasModelo.estado,
                    func.count().label("total"),
                )
                .where(IngestaMetricasModelo.creado_en >= desde)
                .group_by("dia", IngestaMetricasModelo.estado)
                .order_by("dia")
            )
        ).all()

        por_dia: dict[date, MetricaDia] = {}
        for dia, estado, total in filas:
            fecha = dia.date() if isinstance(dia, datetime) else cast(date, dia)
            cantidad = cast(int, total)
            actual = por_dia.get(fecha)
            verificado = actual.verificado if actual else 0
            sospechoso = actual.sospechoso if actual else 0
            rechazado = actual.rechazado if actual else 0
            if estado == "verificado":
                verificado += cantidad
            elif estado == "sospechoso":
                sospechoso += cantidad
            else:
                rechazado += cantidad
            por_dia[fecha] = MetricaDia(
                dia=fecha,
                verificado=verificado,
                sospechoso=sospechoso,
                rechazado=rechazado,
            )
        return list(por_dia.values())

    async def motivos_frecuentes(self, limite: int = 10) -> list[tuple[str, int]]:
        """Motivos más frecuentes de sospecha o rechazo."""
        filas = (
            await self._session.execute(
                select(IngestaMetricasModelo.motivo, func.count())
                .where(IngestaMetricasModelo.motivo.is_not(None))
                .group_by(IngestaMetricasModelo.motivo)
                .order_by(func.count().desc(), IngestaMetricasModelo.motivo)
                .limit(limite)
            )
        ).all()
        return [(str(motivo), total) for motivo, total in filas]
