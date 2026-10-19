"""Sticky post-escritura para evitar leer una réplica con lag.

El estado vive en Redis con TTL, no en memoria del proceso, para que funcione
con varias réplicas de la API.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from redis.asyncio import Redis

from src.config import settings

logger = logging.getLogger(__name__)


class StickyReads:
    """Marca usuarios que acaban de escribir y deben leer del primario."""

    def __init__(self, redis: Redis, ttl_segundos: int) -> None:
        if ttl_segundos < 0:
            raise ValueError("ttl_segundos no puede ser negativo")
        self._redis = redis
        self._ttl_segundos = ttl_segundos

    @staticmethod
    def _clave(usuario_id: str) -> str:
        return f"sticky:rw:{usuario_id}"

    async def marcar(self, usuario_id: str) -> None:
        if self._ttl_segundos == 0:
            return
        await self._redis.set(
            self._clave(usuario_id),
            "1",
            ex=self._ttl_segundos,
        )

    async def activo(self, usuario_id: str) -> bool:
        if self._ttl_segundos == 0:
            return False
        return bool(await self._redis.exists(self._clave(usuario_id)))

    async def aclose(self) -> None:
        await self._redis.aclose()


@lru_cache(maxsize=1)
def get_sticky_reads() -> StickyReads:
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL no está configurada")

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    return StickyReads(client, settings.sticky_reads_segundos)


async def dispose_sticky_reads() -> None:
    """Cierra el cliente de Redis si se llegó a crear."""
    if not get_sticky_reads.cache_info().currsize:
        return

    try:
        await get_sticky_reads().aclose()
    except Exception as exc:  # noqa: BLE001 - cierre best-effort
        logger.warning("Sticky Redis close failed: %s", type(exc).__name__)
    finally:
        get_sticky_reads.cache_clear()
