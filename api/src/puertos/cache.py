"""Puerto de caché de búsquedas.

Solo se cachean resultados `verificado`. Las claves llevan prefijo de versión
(`v1:`) para poder invalidar masivamente sin `SCAN`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

ValorCache = dict[str, Any]


@runtime_checkable
class Cache(Protocol):
    """Almacén clave-valor con TTL e invalidación por prefijo."""

    async def get(self, key: str) -> ValorCache | None: ...

    async def set(self, key: str, value: ValorCache, ttl: int) -> None: ...

    async def invalidar_prefijo(self, prefijo: str) -> None: ...
