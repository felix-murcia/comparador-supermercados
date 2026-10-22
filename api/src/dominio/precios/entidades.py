"""Entidades y value objects del dominio de precios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.dominio.precios.errores import PrecioInvalidoError
from src.dominio.precios.estados import AmbitoPrecio, EstadoPrecio, Orden


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


@dataclass(frozen=True)
class ResultadoComparacion:
    """Precio de un producto en una cadena, con su posición en el ranking."""

    producto_id: UUID
    producto_cadena_id: UUID
    nombre: str
    cadena: str
    precio_eur: Decimal
    marca: str | None = None
    formato: str | None = None
    categoria: str | None = None
    ean: str | None = None
    precio_por_litro_kg: Decimal | None = None
    ambito: AmbitoPrecio = "nacional"
    provincia: str | None = None
    url_producto: str | None = None
    disponible: bool | None = None
    cadena_id: UUID | None = None
    posicion: int = 0


@dataclass(frozen=True)
class PrecioVigente:
    """Precio actual de un producto en una cadena."""

    producto_cadena_id: UUID
    cadena: str
    nombre_cadena: str
    precio_eur: Decimal
    precio_por_litro_kg: Decimal | None = None
    url_producto: str | None = None
    ambito: AmbitoPrecio = "nacional"
    provincia: str | None = None
    disponible: bool | None = None
    fecha_consulta: datetime | None = None


@dataclass(frozen=True)
class ProductoEnCadena:
    """Producto con su precio actual en una cadena.

    Es el candidato a equivalente: al comparar una lista entre cadenas, el
    producto que una persona compró en DIA no está en Carrefour, pero sí
    puede estarlo su equivalente de marca propia.
    """

    producto_id: UUID
    producto_cadena_id: UUID
    nombre: str
    cadena: str
    precio_eur: Decimal
    marca: str | None = None
    categoria: str | None = None
    formato: str | None = None
    litros_o_kg: Decimal | None = None
    url_producto: str | None = None


@dataclass(frozen=True)
class HistoricoPrecio:
    """Un punto del histórico de precios de un producto en una cadena."""

    cadena: str
    fecha: datetime
    precio_eur: Decimal


@dataclass(frozen=True)
class FiltrosComparacion:
    """Filtros, orden y paginación de la comparativa de precios."""

    query: str
    cadenas: tuple[str, ...] = ()
    orden: Orden = "precio_unitario"
    precio_min: Decimal | None = None
    precio_max: Decimal | None = None
    marca: str | None = None
    categoria: str | None = None
    solo_con_stock: bool = False
    provincia: str | None = None
    limite: int = 20
    offset: int = 0
