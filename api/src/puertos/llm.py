"""Puerto del cliente de LLM usado por el productor de precios.

El productor necesita un modelo con búsqueda web: el puerto solo garantiza
que se le pueda pedir una completion en texto.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ClienteLLM(Protocol):
    """Devuelve la respuesta en texto del modelo para un prompt."""

    async def completar(self, prompt: str) -> str: ...
