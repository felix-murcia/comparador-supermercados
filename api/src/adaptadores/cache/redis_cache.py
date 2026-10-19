"""Caché de resultados de búsqueda en Redis.

Las claves llevan prefijo de versión (`v1:`) para poder invalidar todas de
golpe sin `SCAN`: cada versión tiene un conjunto índice con sus claves, y
`invalidar_prefijo` borra ese conjunto y sus valores.

Si Redis no está disponible, la caché degrada a "no hay nada cacheado": la
app sigue funcionando, solo pierde el acierto de caché.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable
from functools import lru_cache
from typing import Any, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import settings
from src.puertos.cache import ValorCache

logger = logging.getLogger(__name__)

PREFIJO_INDICE = "cache:indices:"


def _normalizar_prefijo(prefijo: str) -> str:
    return prefijo if prefijo.endswith(":") else f"{prefijo}:"


def _prefijo_de_version(clave: str) -> str:
    return _normalizar_prefijo(clave.partition(":")[0])


class RedisCache:
    """Caché clave-valor con TTL e invalidación por prefijo de versión."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @staticmethod
    def _indice(prefijo: str) -> str:
        return f"{PREFIJO_INDICE}{_normalizar_prefijo(prefijo)}"

    async def get(self, key: str) -> ValorCache | None:
        try:
            crudo = await self._redis.get(key)
        except RedisError as error:
            logger.warning("Redis no disponible en get: %s", type(error).__name__)
            return None

        if crudo is None:
            return None

        try:
            valor = json.loads(crudo)
        except (TypeError, ValueError):
            logger.warning("Valor ilegible en la caché: %s", key)
            return None
        if not isinstance(valor, dict):
            return None
        return valor

    async def set(self, key: str, value: ValorCache, ttl: int) -> None:
        indice = self._indice(_prefijo_de_version(key))
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl)
            await cast(Awaitable[Any], self._redis.sadd(indice, key))
            await cast(Awaitable[Any], self._redis.expire(indice, ttl))
        except (RedisError, TypeError, ValueError) as error:
            logger.warning(
                "No se pudo guardar en caché %s: %s", key, type(error).__name__
            )

    async def invalidar_prefijo(self, prefijo: str) -> None:
        indice = self._indice(prefijo)
        try:
            claves = await cast(Awaitable[set[str]], self._redis.smembers(indice))
            if claves:
                await self._redis.delete(*claves)
            await self._redis.delete(indice)
        except RedisError as error:
            logger.warning(
                "No se pudo invalidar el prefijo %s: %s", prefijo, type(error).__name__
            )

    async def aclose(self) -> None:
        await self._redis.aclose()


@lru_cache(maxsize=1)
def get_cache() -> RedisCache:
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL no está configurada")

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    return RedisCache(client)


async def dispose_cache() -> None:
    """Cierra el cliente de Redis si se llegó a crear."""
    if not get_cache.cache_info().currsize:
        return

    try:
        await get_cache().aclose()
    except Exception as exc:  # noqa: BLE001 - cierre best-effort
        logger.warning("Redis cache close failed: %s", type(exc).__name__)
    finally:
        get_cache.cache_clear()
