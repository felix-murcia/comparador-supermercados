"""Entidades del dominio de búsquedas asíncronas."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from src.dominio.busquedas.estados import EstadoBusqueda
from src.dominio.precios.estados import ORDEN_POR_DEFECTO, Orden


@dataclass(frozen=True)
class PeticionBusqueda:
    """Datos de una búsqueda de precios."""

    query: str
    cadenas: tuple[str, ...] = ()
    orden: Orden = ORDEN_POR_DEFECTO
    filtros: Mapping[str, str] = field(default_factory=dict)
    provincia: str | None = None


@dataclass(frozen=True)
class ResultadoCrearBusqueda:
    """Acierto de caché o job encolado."""

    job_id: UUID | None
    cache_hit: bool
    resultados: tuple[dict[str, Any], ...] = ()


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
