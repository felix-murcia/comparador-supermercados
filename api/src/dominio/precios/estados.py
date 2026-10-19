"""Estados y ámbitos posibles de un precio verificado."""

from __future__ import annotations

from typing import Final, Literal

EstadoPrecio = Literal["verificado", "sospechoso", "rechazado"]

ESTADOS_PRECIO: Final[tuple[EstadoPrecio, ...]] = (
    "verificado",
    "sospechoso",
    "rechazado",
)

AmbitoPrecio = Literal["nacional", "provincia"]

AMBITOS_PRECIO: Final[tuple[AmbitoPrecio, ...]] = ("nacional", "provincia")
