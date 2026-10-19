"""Estados posibles de una búsqueda asíncrona."""

from __future__ import annotations

from typing import Final, Literal

EstadoBusqueda = Literal["pendiente", "en_progreso", "completada", "fallida"]

ESTADOS_BUSQUEDA: Final[tuple[EstadoBusqueda, ...]] = (
    "pendiente",
    "en_progreso",
    "completada",
    "fallida",
)
