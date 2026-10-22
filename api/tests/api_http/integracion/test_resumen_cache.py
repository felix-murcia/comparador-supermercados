"""La caché del resumen se invalida cuando cambia la lista.

El resumen depende de los items: si se añade, cambia o quita un producto,
el coste cacheado deja de ser cierto. Sin invalidarlo, la lista mostraba el
producto nuevo pero el coste tardaba el TTL de la caché en actualizarse.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.cache.redis_cache import RedisCache
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.dominio.listas.reglas import PREFIJO_RESUMEN
from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.productos.entidades import ProductoNuevo
from src.main import app

_URL_RW = os.getenv("DATABASE_URL_RW")
_SECRETO = os.getenv("NEXTAUTH_SECRET")
_REDIS_URL = os.getenv("REDIS_URL")

if not _URL_RW or not _SECRETO or not _REDIS_URL:
    pytest.skip(
        "Requiere DATABASE_URL_RW, NEXTAUTH_SECRET y REDIS_URL para la integración",
        allow_module_level=True,
    )

assert _SECRETO is not None
assert _REDIS_URL is not None

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
async def redis() -> AsyncIterator[Redis]:
    url = _REDIS_URL
    assert url is not None
    conexion = Redis.from_url(url, decode_responses=True)
    try:
        yield conexion
    finally:
        await conexion.aclose()


@pytest_asyncio.fixture
async def cache(redis: Redis) -> RedisCache:
    return RedisCache(redis)


async def _producto_con_precio(
    sesion: AsyncSession, cadena_id: UUID
) -> tuple[str, str]:
    producto = await SQLAlchemyRepositorioProductos(sesion).crear(
        ProductoNuevo(nombre="Leche entera", marca="Pascual")
    )
    producto_cadena_id = await SQLAlchemyRepositorioProductosCadenas(sesion).crear(
        producto_id=producto.id,
        cadena_id=cadena_id,
        url_producto="https://dia.test/leche",
        nombre_en_cadena="Leche entera 1L",
    )
    await SQLAlchemyRepositorioPrecios(sesion).insertar(
        PrecioNuevo(
            producto_cadena_id=producto_cadena_id,
            importe_eur=Decimal("1.19"),
            url_fuente="https://dia.test/leche",
            fecha_consulta=datetime.now(UTC),
        )
    )
    await sesion.commit()
    return str(producto.id), str(cadena_id)


async def test_anadir_un_item_invalida_el_resumen_cacheado(
    cliente: AsyncClient,
    cache: RedisCache,
    sesion_rw: AsyncSession,
    cadena_dia: UUID,
) -> None:
    provider_id = f"resumen-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, cadena_id = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]

    # El resumen vacío se cachea.
    await cliente.get(f"/v1/listas/{lista_id}/resumen?cadenas=dia", headers=cabeceras)
    clave = f"{PREFIJO_RESUMEN}:{lista_id}:dia"
    assert await cache.get(clave) is not None

    # Al añadir un producto, el resumen cacheado deja de valer.
    await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cadena_compra_id": cadena_id, "cantidad": 1},
        headers=cabeceras,
    )
    assert await cache.get(clave) is None

    # Y el siguiente resumen ya trae el coste del producto nuevo.
    resumen = await cliente.get(
        f"/v1/listas/{lista_id}/resumen?cadenas=dia", headers=cabeceras
    )
    assert resumen.json()["coste_total"] == "1.19"


async def test_quitar_un_item_invalida_el_resumen_cacheado(
    cliente: AsyncClient,
    cache: RedisCache,
    sesion_rw: AsyncSession,
    cadena_dia: UUID,
) -> None:
    provider_id = f"resumen-borrar-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, cadena_id = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]
    item = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cadena_compra_id": cadena_id, "cantidad": 1},
        headers=cabeceras,
    )
    item_id = item.json()["id"]

    await cliente.get(f"/v1/listas/{lista_id}/resumen?cadenas=dia", headers=cabeceras)
    clave = f"{PREFIJO_RESUMEN}:{lista_id}:dia"
    assert await cache.get(clave) is not None

    await cliente.delete(f"/v1/listas/{lista_id}/items/{item_id}", headers=cabeceras)
    assert await cache.get(clave) is None
