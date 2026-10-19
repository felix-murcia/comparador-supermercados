"""Integración de `POST /v1/busquedas` contra Postgres y Redis reales."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.cache.redis_cache import RedisCache
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.dominio.busquedas.reglas import calcular_cache_key
from src.main import app

_URL_RW = os.getenv("DATABASE_URL_RW")
_REDIS_URL = os.getenv("REDIS_URL")
_SECRETO = os.getenv("NEXTAUTH_SECRET")

if not _URL_RW or not _REDIS_URL or not _SECRETO:
    pytest.skip(
        "Requiere DATABASE_URL_RW, REDIS_URL y NEXTAUTH_SECRET para la integración",
        allow_module_level=True,
    )

assert _SECRETO is not None
assert _REDIS_URL is not None

REDIS_TEST_URL = _REDIS_URL

pytestmark = pytest.mark.asyncio


def _token(provider_id: str) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    return pyjwt.encode(
        {
            "sub": f"authjs:google:{provider_id}",
            "email": f"{provider_id}@example.test",
            "name": "Ana",
            "provider": "google",
            "provider_id": provider_id,
            "iat": ahora,
            "exp": ahora + 300,
        },
        _SECRETO,
        algorithm="HS256",
    )


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


@pytest_asyncio.fixture
async def cache() -> AsyncIterator[RedisCache]:
    redis = Redis.from_url(REDIS_TEST_URL, decode_responses=True)
    try:
        yield RedisCache(redis)
    finally:
        await redis.aclose()


async def test_sin_jwt_devuelve_401(cliente: AsyncClient) -> None:
    respuesta = await cliente.post("/v1/busquedas", json={"query": "leche"})

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_sin_cache_encola_el_job(
    cliente: AsyncClient, sesion_rw: AsyncSession
) -> None:
    provider_id = f"miss-{uuid4().hex[:8]}"

    respuesta = await cliente.post(
        "/v1/busquedas",
        json={"query": "leche", "cadenas": ["dia"]},
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cache_hit"] is False
    assert cuerpo["job_id"] is not None
    assert cuerpo["resultados"] == []

    job = await SQLAlchemyRepositorioBusquedas(sesion_rw).obtener(cuerpo["job_id"])
    assert job is not None
    assert job.query == "leche"
    assert job.cadenas == ("dia",)
    assert job.estado == "pendiente"
    assert job.cache_key == calcular_cache_key("leche", ("dia",), "precio_unitario")


async def test_con_cache_devuelve_los_resultados(
    cliente: AsyncClient, cache: RedisCache
) -> None:
    provider_id = f"hit-{uuid4().hex[:8]}"
    clave = calcular_cache_key("leche", ("dia",), "precio_unitario")
    await cache.set(
        clave,
        {"resultados": [{"nombre": "Leche entera", "precio_eur": "1.29"}]},
        ttl=60,
    )

    respuesta = await cliente.post(
        "/v1/busquedas",
        json={"query": "leche", "cadenas": ["dia"]},
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["cache_hit"] is True
    assert cuerpo["job_id"] is None
    assert cuerpo["resultados"] == [{"nombre": "Leche entera", "precio_eur": "1.29"}]


async def test_supera_el_limite_de_peticiones(
    cliente: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.api_http.v1.busquedas.settings.rate_limit_busquedas_por_minuto", 1
    )
    provider_id = f"limite-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}

    primera = await cliente.post(
        "/v1/busquedas", json={"query": "leche"}, headers=cabeceras
    )
    segunda = await cliente.post(
        "/v1/busquedas", json={"query": "leche"}, headers=cabeceras
    )

    assert primera.status_code == 200
    assert segunda.status_code == 429
    assert segunda.json()["code"] == "RATE_LIMIT"
