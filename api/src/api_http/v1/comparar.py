"""Endpoint `GET /v1/comparar`.

Devuelve los precios vigentes de un producto en las cadenas elegidas, con los
filtros y el orden aplicados en SQL sobre la réplica. La resolución de precio
por provincia sigue el ADR-009 (provincia → nacional).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.api_http.dependencias import SessionRO
from src.dominio.precios.entidades import FiltrosComparacion
from src.dominio.precios.estados import ORDEN_POR_DEFECTO, AmbitoPrecio, Orden
from src.dominio.precios.ranking import posicionar

router = APIRouter(prefix="/v1", tags=["comparativa"])


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


class CompararResponse(BaseModel):
    """Página de resultados de la comparativa."""

    orden: Orden
    limit: int
    offset: int
    resultados: list[ResultadoResponse]


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

    resultados = await SQLAlchemyRepositorioPrecios(sesion).buscar_comparativa(filtros)
    posicionados = posicionar(resultados, orden, offset)

    return CompararResponse(
        orden=orden,
        limit=limit,
        offset=offset,
        resultados=[
            ResultadoResponse.model_validate(r, from_attributes=True)
            for r in posicionados
        ],
    )
