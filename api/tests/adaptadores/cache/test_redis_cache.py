"""Tests de `RedisCache` contra un Redis de test (Redis real o fake)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from src.adaptadores.cache.redis_cache import RedisCache
from src.puertos.cache import Cache

REDIS_URL = os.getenv("REDIS_URL")


@pytest_asyncio.fixture
async def redis() -> AsyncIterator[Redis]:
    if not REDIS_URL:
        pytest.skip("REDIS_URL no está configurada")
    client = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def cache(redis: Redis) -> RedisCache:
    return RedisCache(redis)


def test_el_cache_cumple_el_protocolo() -> None:
    assert isinstance(RedisCache(Redis()), Cache)


@pytest.mark.asyncio
async def test_guarda_y_recupera_un_valor(cache: RedisCache) -> None:
    await cache.set("v1:abc", {"resultados": [{"precio_eur": 1.29}]}, ttl=60)

    assert await cache.get("v1:abc") == {"resultados": [{"precio_eur": 1.29}]}


@pytest.mark.asyncio
async def test_devuelve_none_si_no_existe(cache: RedisCache) -> None:
    assert await cache.get("v1:no-existe") is None


@pytest.mark.asyncio
async def test_el_valor_caduca(cache: RedisCache) -> None:
    await cache.set("v1:caduca", {"resultados": []}, ttl=1)

    await asyncio.sleep(1.2)

    assert await cache.get("v1:caduca") is None


@pytest.mark.asyncio
async def test_invalida_todas_las_claves_del_prefijo(cache: RedisCache) -> None:
    await cache.set("v1:uno", {"resultados": [1]}, ttl=60)
    await cache.set("v1:dos", {"resultados": [2]}, ttl=60)
    await cache.set("v2:tres", {"resultados": [3]}, ttl=60)

    await cache.invalidar_prefijo("v1:")

    assert await cache.get("v1:uno") is None
    assert await cache.get("v1:dos") is None
    assert await cache.get("v2:tres") == {"resultados": [3]}


@pytest.mark.asyncio
async def test_el_indice_no_caduca_antes_que_sus_claves(
    cache: RedisCache, redis: Redis
) -> None:
    """Guardar una clave con TTL corto no puede acortar el índice.

    La búsqueda se cachea 24 h y la comparativa 5 min: si la segunda renewa
    el índice con su TTL corto, el índice caduca antes que la clave larga y
    esa clave queda huérfana (la invalidación por prefijo deja de encontrarla).
    """
    await cache.set("v1:larga", {"resultados": [1]}, ttl=3600)
    await cache.set("v1:corta", {"resultados": [2]}, ttl=60)

    ttl_indice = await redis.ttl("cache:indices:v1:")

    assert ttl_indice > 60, "el índice caducaría antes que sus claves"
    await cache.invalidar_prefijo("v1:")
    assert await cache.get("v1:larga") is None
    assert await cache.get("v1:corta") is None


@pytest.mark.asyncio
async def test_no_rompe_si_redis_no_esta_disponible() -> None:
    cliente = Redis.from_url("redis://127.0.0.1:1/0", decode_responses=True)
    cache = RedisCache(cliente)

    assert await cache.get("v1:abc") is None
    await cache.set("v1:abc", {"resultados": []}, ttl=60)
    await cache.invalidar_prefijo("v1:")
    await cliente.aclose()
