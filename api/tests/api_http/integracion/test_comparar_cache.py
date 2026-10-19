"""Integración de la caché de `GET /v1/comparar` (T4.5)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.cache.redis_cache import RedisCache
from src.api_http.v1.comparar import TTL_COMPARACION_SEGUNDOS
from src.dominio.busquedas.reglas import calcular_cache_key_comparacion
from src.main import app

_REDIS_URL = os.getenv("REDIS_URL")

if not _REDIS_URL:
    pytest.skip("REDIS_URL no está configurada", allow_module_level=True)

REDIS_TEST_URL = _REDIS_URL

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


@pytest_asyncio.fixture
async def redis() -> AsyncIterator[Redis]:
    cliente = Redis.from_url(REDIS_TEST_URL, decode_responses=True)
    try:
        yield cliente
    finally:
        await cliente.aclose()


@pytest_asyncio.fixture
async def cache(redis: Redis) -> RedisCache:
    return RedisCache(redis)


def _resultado_ejemplo() -> dict[str, object]:
    return {
        "posicion": 1,
        "producto_id": "11111111-1111-1111-1111-111111111111",
        "producto_cadena_id": "22222222-2222-2222-2222-222222222222",
        "nombre": "Leche entera",
        "marca": "Pascual",
        "formato": "1L",
        "categoria": "lacteos",
        "ean": "8412345678901",
        "cadena": "dia",
        "precio_eur": "1.29",
        "precio_por_litro_kg": "1.2900",
        "ambito": "nacional",
        "provincia": None,
    }


def _clave(
    consulta: str,
    cadenas: tuple[str, ...] = (),
    orden: str = "precio_unitario",
    provincia: str | None = None,
    limite: int = 20,
    offset: int = 0,
) -> str:
    return calcular_cache_key_comparacion(
        consulta,
        cadenas,
        orden,
        {
            "precio_min": "",
            "precio_max": "",
            "marca": "",
            "categoria": "",
            "solo_con_stock": "",
            "limit": str(limite),
            "offset": str(offset),
        },
        provincia,
    )


async def test_la_clave_incluye_la_provincia() -> None:
    nacional = _clave("leche")
    madrid = _clave("leche", provincia="madrid")
    barcelona = _clave("leche", provincia="barcelona")

    assert nacional != madrid
    assert madrid != barcelona


async def test_la_clave_incluye_los_filtros_de_paginacion() -> None:
    primera = _clave("leche", limite=20)
    otra_pagina = _clave("leche", limite=10)
    otro_desplazamiento = _clave("leche", offset=10)

    assert primera != otra_pagina
    assert primera != otro_desplazamiento


async def test_la_clave_incluye_las_cadenas_y_el_orden() -> None:
    base = _clave("leche")
    con_cadenas = _clave("leche", cadenas=("dia",))
    con_orden = _clave("leche", orden="precio_kg_l")

    assert base != con_cadenas
    assert base != con_orden


async def test_el_prefijo_de_la_comparativa_es_distinto_de_la_busqueda(
    cache: RedisCache,
) -> None:
    from src.dominio.busquedas.reglas import calcular_cache_key

    comparativa = _clave("leche")
    busqueda = calcular_cache_key("leche", (), "precio_unitario", {}, None)

    assert comparativa != busqueda
    assert comparativa.startswith("v1:")


async def test_la_invalidacion_tras_la_ingesta_limpia_la_comparativa(
    cache: RedisCache,
) -> None:
    clave = _clave("leche")
    await cache.set(clave, {"resultados": []}, ttl=60)

    await cache.invalidar_prefijo("v1:")

    assert await cache.get(clave) is None


async def test_el_ttl_de_la_comparativa_es_de_300_segundos(redis: Redis) -> None:
    clave = _clave(f"leche-ttl-{uuid4().hex[:8]}")
    await redis.set(clave, "{}", ex=TTL_COMPARACION_SEGUNDOS)

    ttl = await redis.ttl(clave)

    assert 0 < ttl <= TTL_COMPARACION_SEGUNDOS
    await redis.delete(clave)


async def test_la_comparativa_se_sirve_de_la_cache(
    cliente: AsyncClient, cache: RedisCache, sesion_rw: AsyncSession
) -> None:
    consulta = f"leche-{uuid4().hex[:8]}"
    clave = _clave(consulta)
    await cache.set(
        clave,
        {
            "orden": "precio_unitario",
            "limit": 20,
            "offset": 0,
            "resultados": [_resultado_ejemplo()],
        },
        ttl=60,
    )

    respuesta = await cliente.get("/v1/comparar", params={"q": consulta})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["resultados"] == [_resultado_ejemplo()]
    assert cuerpo["resultados"][0]["precio_eur"] == "1.29"
