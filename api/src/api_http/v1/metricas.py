"""Endpoint interno de métricas de ingesta.

`GET /v1/_metrics/ingesta` resume el reparto de estados (verificado,
sospechoso, rechazado) y los motivos más frecuentes de la ingesta.

Es un endpoint interno: requiere sesión iniciada y, en producción, solo
debería exponerse en la red interna.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.adaptadores.persistencia.repositorio_metricas import (
    SQLAlchemyRepositorioMetricas,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRO
from src.dominio.ingesta.entidades import MetricasIngesta

router = APIRouter(prefix="/v1/_metrics", tags=["métricas"])


class MotivoResponse(BaseModel):
    """Motivo de rechazo o sospecha y cuántas veces se dio."""

    motivo: str
    total: int


class MetricasIngestaResponse(BaseModel):
    """Resumen de la ingesta de precios."""

    total: int
    verificado: int
    sospechoso: int
    rechazado: int
    porcentaje_verificado: float
    porcentaje_sospechoso: float
    porcentaje_rechazado: float
    motivos: list[MotivoResponse]

    @classmethod
    def desde(cls, metricas: MetricasIngesta) -> MetricasIngestaResponse:
        return cls(
            total=metricas.total,
            verificado=metricas.verificado,
            sospechoso=metricas.sospechoso,
            rechazado=metricas.rechazado,
            porcentaje_verificado=metricas.porcentaje_verificado,
            porcentaje_sospechoso=metricas.porcentaje_sospechoso,
            porcentaje_rechazado=metricas.porcentaje_rechazado,
            motivos=[
                MotivoResponse(motivo=motivo, total=total)
                for motivo, total in metricas.motivos
            ],
        )


@router.get("/ingesta", response_model=MetricasIngestaResponse)
async def metricas_ingesta(
    identidad: Identidad,
    sesion: SessionRO,
) -> MetricasIngestaResponse:
    """Reparto por estado y motivos más frecuentes de la ingesta."""
    metricas = await SQLAlchemyRepositorioMetricas(sesion).resumen()
    return MetricasIngestaResponse.desde(metricas)
