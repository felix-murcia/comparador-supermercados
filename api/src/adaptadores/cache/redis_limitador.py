"""Limitador de peticiones sobre Redis (ventana fija por clave)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import lru_cache

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import settings
from src.dominio.errores import RateLimitError

logger = logging.getLogger(__name__)

PREFIJO = "rate:"


class RedisLimitador:
    """Contador por clave y ventana; si Redis falla, no bloquea la app."""

    def __init__(
        self,
        redis: Redis,
        *,
        dormir: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._redis = redis
        self._dormir = dormir

    async def comprobar(
        self, clave: str, limite: int, ventana_segundos: int = 60
    ) -> None:
        if limite <= 0:
            return

        contador = f"{PREFIJO}{clave}"
        try:
            actual = await self._redis.incr(contador)
            if actual == 1:
                await self._redis.expire(contador, ventana_segundos)
        except RedisError as error:
            logger.warning(
                "Redis no disponible en el limitador: %s", type(error).__name__
            )
            return

        if actual > limite:
            raise RateLimitError(limite, ventana_segundos)

    async def aclose(self) -> None:
        await self._redis.aclose()


@lru_cache(maxsize=1)
def get_limitador() -> RedisLimitador:
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL no está configurada")

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    return RedisLimitador(client)


async def dispose_limitador() -> None:
    """Cierra el cliente de Redis del limitador si se llegó a crear."""
    if not get_limitador.cache_info().currsize:
        return

    try:
        await get_limitador().aclose()
    except Exception as exc:  # noqa: BLE001 - cierre best-effort
        logger.warning("Redis limitador close failed: %s", type(exc).__name__)
    finally:
        get_limitador.cache_clear()
