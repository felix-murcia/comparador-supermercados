"""Endpoints internos de administración (`/v1/admin`).

Solo accesibles para los emails de la lista blanca `ADMIN_EMAILS`.
Las métricas no contienen datos personales: solo estados, motivos y fechas.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel

from src.adaptadores.persistencia.repositorio_metricas import (
    SQLAlchemyRepositorioMetricas,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRO
from src.config import settings
from src.dominio.usuarios.admin import es_admin
from src.dominio.usuarios.errores import UsuarioNoAutorizadoError

router = APIRouter(prefix="/v1/admin", tags=["admin"])

DIAS_POR_DEFECTO = 7
TOP_MOTIVOS = 10


class MetricaDiaResponse(BaseModel):
    """Reparto por estado de un día."""

    dia: date
    verificado: int
    sospechoso: int
    rechazado: int


class MotivoResponse(BaseModel):
    """Motivo de sospecha o rechazo y su frecuencia."""

    motivo: str
    total: int


class MetricasAdminResponse(BaseModel):
    """Resumen de la ingesta para el panel interno."""

    total: int
    verificado: int
    sospechoso: int
    rechazado: int
    por_dia: list[MetricaDiaResponse]
    motivos: list[MotivoResponse]


@router.get("/metricas", response_model=MetricasAdminResponse)
async def metricas_ingesta(
    identidad: Identidad,
    sesion: SessionRO,
) -> MetricasAdminResponse:
    """Reparto por estado de los últimos días y motivos más frecuentes."""
    if not es_admin(identidad.email, settings.admin_emails):
        raise UsuarioNoAutorizadoError("Se requiere ser administrador")

    repositorio = SQLAlchemyRepositorioMetricas(sesion)
    resumen = await repositorio.resumen()
    por_dia = await repositorio.resumen_por_dia(DIAS_POR_DEFECTO)
    motivos = await repositorio.motivos_frecuentes(TOP_MOTIVOS)

    return MetricasAdminResponse(
        total=resumen.total,
        verificado=resumen.verificado,
        sospechoso=resumen.sospechoso,
        rechazado=resumen.rechazado,
        por_dia=[
            MetricaDiaResponse(
                dia=metrica.dia,
                verificado=metrica.verificado,
                sospechoso=metrica.sospechoso,
                rechazado=metrica.rechazado,
            )
            for metrica in por_dia
        ],
        motivos=[
            MotivoResponse(motivo=motivo, total=total) for motivo, total in motivos
        ],
    )
