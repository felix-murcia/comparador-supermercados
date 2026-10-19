"""Endpoint `GET /v1/comparar`.

Devuelve los precios vigentes de un producto en las cadenas elegidas, con los
filtros y el orden aplicados en SQL sobre la réplica. La resolución de precio
por provincia sigue el ADR-009 (provincia → nacional).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ValidationError

from src.adaptadores.cache.redis_cache import get_cache
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.api_http.dependencias import SessionRO
from src.dominio.busquedas.reglas import calcular_cache_key_comparacion
from src.dominio.precios.entidades import FiltrosComparacion
from src.dominio.precios.estados import ORDEN_POR_DEFECTO, AmbitoPrecio, Orden
from src.dominio.precios.ranking import posicionar
from src.puertos.cache import Cache

router = APIRouter(prefix="/v1", tags=["comparativa"])

TTL_COMPARACION_SEGUNDOS = 300

logger = logging.getLogger(__name__)


class ResultadoResponse(BaseModel):
    """Precio de un producto en una cadena, con su posición en el ranking."""

    posicion: int
    producto_id: UUID
    producto_cadena_id: UUID
    nombre: str
    marca: str | None
    formato: str | None
    categoria: str | None
    ean: str | None
    cadena: str
    precio_eur: Decimal
    precio_por_litro_kg: Decimal | None
    ambito: AmbitoPrecio
    provincia: str | None
    url_producto: str | None = None
    disponible: bool | None = None


class CompararResponse(BaseModel):
    """Página de resultados de la comparativa."""

    orden: Orden
    limit: int
    offset: int
    resultados: list[ResultadoResponse]


def _filtros_cache(filtros: FiltrosComparacion) -> dict[str, str]:
    """Filtros que forman parte de la clave de caché de la comparativa."""
    return {
        "precio_min": "" if filtros.precio_min is None else str(filtros.precio_min),
        "precio_max": "" if filtros.precio_max is None else str(filtros.precio_max),
        "marca": filtros.marca or "",
        "categoria": filtros.categoria or "",
        "solo_con_stock": "1" if filtros.solo_con_stock else "",
        "limit": str(filtros.limite),
        "offset": str(filtros.offset),
    }


def _cache_optional() -> Cache | None:
    """Caché de comparativas; sin Redis el endpoint funciona igual."""
    try:
        return get_cache()
    except RuntimeError:
        return None


@router.get("/comparar", response_model=CompararResponse)
async def comparar(
    sesion: SessionRO,
    q: Annotated[str, Query(min_length=1, description="Producto a buscar")],
    cadenas: Annotated[
        list[str], Query(default_factory=list, description="Cadenas a comparar")
    ],
    orden: Orden = ORDEN_POR_DEFECTO,
    precio_min: Decimal | None = None,
    precio_max: Decimal | None = None,
    marca: str | None = None,
    categoria: str | None = None,
    solo_con_stock: bool = False,
    provincia: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    cache: Annotated[Cache | None, Depends(_cache_optional)] = None,
) -> CompararResponse:
    """Precios que cumplen los filtros, ordenados según el criterio pedido."""
    filtros = FiltrosComparacion(
        query=q,
        cadenas=tuple(cadenas),
        orden=orden,
        precio_min=precio_min,
        precio_max=precio_max,
        marca=marca,
        categoria=categoria,
        solo_con_stock=solo_con_stock,
        provincia=provincia,
        limite=limit,
        offset=offset,
    )

    clave = calcular_cache_key_comparacion(
        filtros.query,
        filtros.cadenas,
        filtros.orden,
        _filtros_cache(filtros),
        filtros.provincia,
    )

    if cache is not None:
        cached = await cache.get(clave)
        if cached is not None:
            try:
                return CompararResponse.model_validate(cached)
            except ValidationError:
                logger.warning("Caché de comparativa corrupta; se recalcula")

    resultados = await SQLAlchemyRepositorioPrecios(sesion).buscar_comparativa(filtros)
    posicionados = posicionar(resultados, orden, offset)

    respuesta = CompararResponse(
        orden=orden,
        limit=limit,
        offset=offset,
        resultados=[
            ResultadoResponse.model_validate(r, from_attributes=True)
            for r in posicionados
        ],
    )

    if cache is not None:
        await cache.set(
            clave, respuesta.model_dump(mode="json"), TTL_COMPARACION_SEGUNDOS
        )

    return respuesta
