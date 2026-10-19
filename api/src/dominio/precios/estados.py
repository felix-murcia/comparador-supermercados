"""Estados posibles de un precio tras la verificación."""

from __future__ import annotations

from typing import Final, Literal

EstadoPrecio = Literal["verificado", "sospechoso", "rechazado"]

ESTADOS_PRECIO: Final[tuple[EstadoPrecio, ...]] = (
    "verificado",
    "sospechoso",
    "rechazado",
)
