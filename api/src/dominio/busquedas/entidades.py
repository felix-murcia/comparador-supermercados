"""Entidades del dominio de búsquedas asíncronas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.dominio.busquedas.estados import EstadoBusqueda


@dataclass(frozen=True)
class BusquedaNueva:
    """Datos para encolar una búsqueda; id y creado_en los asigna la BD."""

    query: str
    cadenas: tuple[str, ...]
    cache_key: str
    usuario_id: UUID | None = None
    provincia: str | None = None


@dataclass(frozen=True)
class Busqueda:
    """Estado de un job de búsqueda asíncrona."""

    id: UUID
    query: str
    cadenas: tuple[str, ...]
    estado: EstadoBusqueda
    progreso: int
    cache_key: str
    creado_en: datetime
    usuario_id: UUID | None = None
    provincia: str | None = None
    completado_en: datetime | None = None
