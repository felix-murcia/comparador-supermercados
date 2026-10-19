"""Entidades y value objects del dominio de precios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.dominio.precios.errores import PrecioInvalidoError
from src.dominio.precios.estados import AmbitoPrecio, EstadoPrecio


@dataclass(frozen=True)
class Precio:
    """Precio de un producto en una cadena: importe y €/L o €/kg."""

    importe_eur: Decimal
    por_litro_kg: Decimal | None = None

    def __post_init__(self) -> None:
        if self.importe_eur < 0:
            raise PrecioInvalidoError("importe_eur no puede ser negativo")
        if self.por_litro_kg is not None and self.por_litro_kg < 0:
            raise PrecioInvalidoError("por_litro_kg no puede ser negativo")


@dataclass(frozen=True)
class PrecioNuevo:
    """Datos para insertar un precio; id y creado_en los asigna la BD."""

    producto_cadena_id: UUID
    importe_eur: Decimal
    url_fuente: str
    fecha_consulta: datetime
    estado: EstadoPrecio = "verificado"
    por_litro_kg: Decimal | None = None
    disponible: bool | None = None
    promocion: str | None = None
    ambito: AmbitoPrecio = "nacional"
    provincia: str | None = None


@dataclass(frozen=True)
class PrecioRegistrado:
    """Fila de `precios` ya persistida (append-only)."""

    id: UUID
    producto_cadena_id: UUID
    importe_eur: Decimal
    por_litro_kg: Decimal | None
    disponible: bool | None
    promocion: str | None
    ambito: AmbitoPrecio
    provincia: str | None
    estado: EstadoPrecio
    url_fuente: str
    fecha_consulta: datetime
    creado_en: datetime
