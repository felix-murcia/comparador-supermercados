"""Entidades del dominio de cadenas de supermercados."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Cadena:
    """Supermercado del que se extraen precios."""

    id: UUID
    slug: str
    nombre: str
    logo_svg: str
