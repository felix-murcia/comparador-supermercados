"""Endpoint `POST /v1/busquedas`.

Calcula la clave de caché de la búsqueda: si el resultado está en caché se
devuelve al momento; si no, se encola el job que procesará el worker.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.adaptadores.cache.redis_cache import get_cache
from src.adaptadores.cache.redis_limitador import get_limitador
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRW
from src.aplicacion.busquedas.crear_busqueda import CrearBusqueda
from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.config import settings
from src.dominio.busquedas.entidades import PeticionBusqueda
from src.dominio.precios.estados import ORDEN_POR_DEFECTO, Orden

router = APIRouter(prefix="/v1", tags=["búsquedas"])


class BusquedaRequest(BaseModel):
    """Body de una búsqueda de precios."""

    query: str = Field(min_length=1)
    cadenas: list[str] = Field(default_factory=list)
    orden: Orden = ORDEN_POR_DEFECTO
    filtros: dict[str, str] = Field(default_factory=dict)
    provincia: str | None = None


class BusquedaResponse(BaseModel):
    """Acierto de caché o job encolado."""

    job_id: UUID | None
    cache_hit: bool
    resultados: list[dict[str, Any]] = Field(default_factory=list)


async def get_crear_busqueda(sesion: SessionRW) -> CrearBusqueda:
    """Caso de uso con la caché, el limitador y el repositorio de búsquedas."""
    return CrearBusqueda(
        repositorio_busquedas=SQLAlchemyRepositorioBusquedas(sesion),
        cache=get_cache(),
        limitador=get_limitador(),
        limite_por_minuto=settings.rate_limit_busquedas_por_minuto,
    )


@router.post("/busquedas", response_model=BusquedaResponse)
async def crear_busqueda(
    body: BusquedaRequest,
    identidad: Identidad,
    sesion: SessionRW,
    caso: Annotated[CrearBusqueda, Depends(get_crear_busqueda)],
) -> BusquedaResponse:
    """Encola la búsqueda o devuelve el resultado cacheado."""
    usuario = await ObtenerPerfil(SQLAlchemyRepositorioUsuarios(sesion)).ejecutar(
        identidad
    )

    resultado = await caso.ejecutar(
        PeticionBusqueda(
            query=body.query,
            cadenas=tuple(body.cadenas),
            orden=body.orden,
            filtros=body.filtros,
            provincia=body.provincia,
        ),
        usuario.id,
        f"{usuario.provider}:{usuario.provider_id}",
    )

    return BusquedaResponse(
        job_id=resultado.job_id,
        cache_hit=resultado.cache_hit,
        resultados=list(resultado.resultados),
    )
