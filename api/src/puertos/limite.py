"""Puerto del limitador de peticiones."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Limitador(Protocol):
    """Cuenta peticiones por clave y avisa cuando se supera el límite."""

    async def comprobar(
        self, clave: str, limite: int, ventana_segundos: int = 60
    ) -> None:
        """Lanza `RateLimitError` si la clave superó el límite en la ventana."""
        ...
