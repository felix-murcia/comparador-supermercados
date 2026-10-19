"""Integración del repositorio de métricas de ingesta."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_metricas import (
    SQLAlchemyRepositorioMetricas,
)
from src.dominio.ingesta.entidades import MetricaIngesta
from src.puertos.repositorios import RepositorioMetricas

pytestmark = pytest.mark.asyncio


async def test_el_repositorio_cumple_el_protocolo(sesion_rw: AsyncSession) -> None:
    assert isinstance(SQLAlchemyRepositorioMetricas(sesion_rw), RepositorioMetricas)


async def test_resumen_vacio_sin_ingestas(sesion_rw: AsyncSession) -> None:
    resumen = await SQLAlchemyRepositorioMetricas(sesion_rw).resumen()

    assert resumen.total == 0
    assert resumen.porcentaje_verificado == 0.0
    assert resumen.motivos == ()


async def test_resume_el_reparto_por_estado_y_los_motivos(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioMetricas(sesion_rw)
    await repositorio.registrar(MetricaIngesta(cadena="dia", estado="verificado"))
    await repositorio.registrar(MetricaIngesta(cadena="dia", estado="verificado"))
    await repositorio.registrar(
        MetricaIngesta(
            cadena="carrefour",
            estado="sospechoso",
            motivo="desviacion_precio",
        )
    )
    await repositorio.registrar(
        MetricaIngesta(
            cadena="carrefour",
            estado="rechazado",
            motivo="precio_no_encontrado_en_html",
        )
    )
    await sesion_rw.commit()

    resumen = await repositorio.resumen()

    assert resumen.total == 4
    assert resumen.verificado == 2
    assert resumen.sospechoso == 1
    assert resumen.rechazado == 1
    assert resumen.porcentaje_verificado == 50.0
    assert resumen.porcentaje_sospechoso == 25.0
    assert resumen.porcentaje_rechazado == 25.0
    assert dict(resumen.motivos) == {
        "desviacion_precio": 1,
        "precio_no_encontrado_en_html": 1,
    }


async def test_ordena_los_motivos_por_frecuencia(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioMetricas(sesion_rw)
    for _ in range(3):
        await repositorio.registrar(
            MetricaIngesta(
                cadena="dia", estado="sospechoso", motivo="desviacion_precio"
            )
        )
    await repositorio.registrar(
        MetricaIngesta(cadena="dia", estado="rechazado", motivo="fetch_error")
    )
    await sesion_rw.commit()

    resumen = await repositorio.resumen()

    assert resumen.motivos[0] == ("desviacion_precio", 3)
    assert resumen.motivos[1] == ("fetch_error", 1)
