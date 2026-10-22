"""Entidades y value objects del dominio de productos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.dominio.productos.errores import FormatoInvalidoError

UNIDADES_FORMATO = ("L", "ml", "kg", "g")


@dataclass(frozen=True)
class Formato:
    """Tamaño de un producto: cantidad en la unidad indicada."""

    litros_o_kg: Decimal
    unidad: str  # "L" | "ml" | "kg" | "g"

    def __post_init__(self) -> None:
        if self.unidad not in UNIDADES_FORMATO:
            raise FormatoInvalidoError(self.unidad)
        if self.litros_o_kg < 0:
            raise FormatoInvalidoError(self.litros_o_kg)

    def a_litros_o_kg(self) -> Decimal:
        """Normaliza a litros o kg: ml y g se dividen entre 1000."""
        if self.unidad in ("ml", "g"):
            return self.litros_o_kg / Decimal(1000)
        return self.litros_o_kg


@dataclass(frozen=True)
class ProductoNuevo:
    """Datos para crear un producto; id y creado_en los asigna la BD."""

    nombre: str
    marca: str | None = None
    categoria: str | None = None
    formato: str | None = None
    litros_o_kg: Decimal | None = None
    ean: str | None = None


@dataclass(frozen=True)
class Producto:
    """Producto canónico normalizado."""

    id: UUID
    nombre: str
    marca: str | None
    categoria: str | None
    formato: str | None
    litros_o_kg: Decimal | None
    ean: str | None
    creado_en: datetime


@dataclass(frozen=True)
class ProductoIngestable:
    """Producto activo y cadenas donde está disponible, para la ingesta diaria."""

    id: UUID
    nombre: str
    cadenas: tuple[str, ...]


@dataclass(frozen=True)
class DescripcionProducto:
    """Lo que un producto es para quien compra, más allá de su marca.

    Dos productos de cadenas distintas con la misma descripción son
    equivalentes: cubren la misma necesidad de compra aunque el artículo
    concreto sea de marca propia en cada cadena.
    """

    nombre: str
    marca: str | None = None
    categoria: str | None = None
    litros_o_kg: Decimal | None = None
    formato: str | None = None
