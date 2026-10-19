"""Endpoint `GET /v1/productos/{slug}`: ficha del producto.

Devuelve los precios vigentes por cadena y el histórico de precios (append-only)
para el rango temporal pedido.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.api_http.dependencias import SessionRO
from src.dominio.productos.errores import ProductoNoEncontradoError

router = APIRouter(prefix="/v1/productos", tags=["productos"])

MESES_POR_DEFECTO = 3


class ProductoResponse(BaseModel):
    """Datos del producto canónico."""

    id: UUID
    nombre: str
    marca: str | None
    categoria: str | None
    formato: str | None
    ean: str | None
    litros_o_kg: Decimal | None


class PrecioVigenteResponse(BaseModel):
    """Precio actual del producto en una cadena."""

    cadena: str
    nombre_cadena: str
    precio_eur: Decimal
    precio_por_litro_kg: Decimal | None
    url_producto: str | None
    ambito: str
    provincia: str | None
    disponible: bool | None
    fecha_consulta: datetime | None


class HistoricoResponse(BaseModel):
    """Un punto del histórico de precios."""

    cadena: str
    fecha: datetime
    precio_eur: Decimal


class FichaProductoResponse(BaseModel):
    """Ficha completa del producto."""

    producto: ProductoResponse
    precios_actuales: list[PrecioVigenteResponse]
    historico: list[HistoricoResponse]


@router.get("/{slug}", response_model=FichaProductoResponse)
async def ficha_producto(
    slug: str,
    sesion: SessionRO,
    provincia: str | None = None,
    meses: Annotated[int, Query(ge=1, le=12)] = MESES_POR_DEFECTO,
) -> FichaProductoResponse:
    """Precios actuales por cadena e histórico del producto."""
    producto = await SQLAlchemyRepositorioProductos(sesion).obtener_por_slug(slug)
    if producto is None:
        raise ProductoNoEncontradoError(slug)

    repositorio = SQLAlchemyRepositorioPrecios(sesion)
    precios = await repositorio.precios_actuales(producto.id, provincia)
    desde = datetime.now(UTC) - timedelta(days=30 * meses)
    historico = await repositorio.historico_producto(producto.id, desde)

    return FichaProductoResponse(
        producto=ProductoResponse(
            id=producto.id,
            nombre=producto.nombre,
            marca=producto.marca,
            categoria=producto.categoria,
            formato=producto.formato,
            ean=producto.ean,
            litros_o_kg=producto.litros_o_kg,
        ),
        precios_actuales=[
            PrecioVigenteResponse(
                cadena=precio.cadena,
                nombre_cadena=precio.nombre_cadena,
                precio_eur=precio.precio_eur,
                precio_por_litro_kg=precio.precio_por_litro_kg,
                url_producto=precio.url_producto,
                ambito=precio.ambito,
                provincia=precio.provincia,
                disponible=precio.disponible,
                fecha_consulta=precio.fecha_consulta,
            )
            for precio in precios
        ],
        historico=[
            HistoricoResponse(
                cadena=punto.cadena,
                fecha=punto.fecha,
                precio_eur=punto.precio_eur,
            )
            for punto in historico
        ],
    )
