"""Test end-to-end del flujo completo: búsqueda → comparar → lista → resumen.

Recorre la aplicación como lo haría una persona: lanza una búsqueda, la
completa, consulta la comparativa, añade un producto a una lista y pide el
resumen de ahorro. Requiere la BD y el Redis de test.
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
from src.adaptadores.persistencia.repositorio_cadenas import (
    SQLAlchemyRepositorioCadenas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.dominio.busquedas.reglas import calcular_cache_key
from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.productos.entidades import ProductoNuevo
from src.main import app

_URL_RW = os.getenv("DATABASE_URL_RW")
_URL_RO = os.getenv("DATABASE_URL_RO")
_REDIS_URL = os.getenv("REDIS_URL")
_SECRETO = os.getenv("NEXTAUTH_SECRET")

if not _URL_RW or not _URL_RO or not _REDIS_URL or not _SECRETO:
    pytest.skip(
        "Requiere DATABASE_URL_RW, DATABASE_URL_RO, REDIS_URL y NEXTAUTH_SECRET",
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
async def redis() -> AsyncIterator[Redis]:
    conexion = Redis.from_url(REDIS_TEST_URL, decode_responses=True)
    try:
        yield conexion
    finally:
        await conexion.aclose()


async def _catalogo(sesion: AsyncSession, cadena_dia: UUID) -> tuple[UUID, UUID, UUID]:
    """Crea el producto, su ficha en DIA y el precio provincial de Madrid."""
    cadenas = SQLAlchemyRepositorioCadenas(sesion)
    dia = await cadenas.obtener_por_id(cadena_dia)
    assert dia is not None

    producto = await SQLAlchemyRepositorioProductos(sesion).crear(
        ProductoNuevo(nombre="Leche entera", marca="Pascual")
    )
    await sesion.commit()

    mappings = SQLAlchemyRepositorioProductosCadenas(sesion)
    ficha = await mappings.crear(
        producto_id=producto.id,
        cadena_id=dia.id,
        url_producto="https://dia.test/leche",
        nombre_en_cadena="Leche entera 1L",
    )
    await sesion.commit()
    return producto.id, dia.id, ficha


async def test_flujo_completo_de_busqueda_lista_y_ahorro(
    cliente: AsyncClient,
    sesion_rw: AsyncSession,
    redis: Redis,
    cadena_dia: UUID,
) -> None:
    provider_id = f"e2e-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, dia_id, _ = await _catalogo(sesion_rw, cadena_dia)

    # El precio provincial de Madrid y el nacional: con provincia gana el
    # provincial y sin ella se usa el nacional (fallback del ADR-009).
    precios = SQLAlchemyRepositorioPrecios(sesion_rw)
    producto_cadena_id = await SQLAlchemyRepositorioProductosCadenas(
        sesion_rw
    ).obtener_por_producto_y_cadena(producto_id, dia_id)
    assert producto_cadena_id is not None
    await precios.insertar(
        PrecioNuevo(
            producto_cadena_id=producto_cadena_id,
            importe_eur=Decimal("1.00"),
            url_fuente="https://dia.test/leche",
            fecha_consulta=datetime.now(UTC),
        )
    )
    await precios.insertar(
        PrecioNuevo(
            producto_cadena_id=producto_cadena_id,
            importe_eur=Decimal("0.90"),
            url_fuente="https://dia.test/leche-madrid",
            fecha_consulta=datetime.now(UTC),
            ambito="provincia",
            provincia="madrid",
        )
    )
    await sesion_rw.commit()

    # 1. Búsqueda sin caché: encola un job.
    busqueda = await cliente.post(
        "/v1/busquedas",
        json={"query": "leche entera", "cadenas": ["dia"]},
        headers=cabeceras,
    )
    assert busqueda.status_code == 200
    assert busqueda.json()["cache_hit"] is False
    job_id = busqueda.json()["job_id"]
    assert job_id

    # 2. El job se consulta y está pendiente.
    estado = await cliente.get(f"/v1/busquedas/{job_id}", headers=cabeceras)
    assert estado.status_code == 200
    assert estado.json()["estado"] in {"pendiente", "en_progreso"}

    # 3. Comparativa: con provincia manda el precio provincial y sin ella el
    # nacional (fallback del ADR-009).
    con_provincia = await cliente.get(
        "/v1/comparar",
        params={"q": "leche", "cadenas": "dia", "provincia": "madrid"},
    )
    assert con_provincia.status_code == 200
    resultados = con_provincia.json()["resultados"]
    assert resultados
    assert resultados[0]["precio_eur"] == "0.90"
    assert resultados[0]["ambito"] == "provincia"

    sin_provincia = await cliente.get(
        "/v1/comparar", params={"q": "leche", "cadenas": "dia"}
    )
    assert sin_provincia.json()["resultados"][0]["precio_eur"] == "1.00"
    assert sin_provincia.json()["resultados"][0]["ambito"] == "nacional"

    # 4. Lista: se crea y se añade el producto con su precio del momento.
    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra E2E"}, headers=cabeceras
    )
    assert creada.status_code == 201
    lista_id = creada.json()["id"]

    item = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": str(producto_id), "cadena_compra_id": str(dia_id)},
        headers=cabeceras,
    )
    assert item.status_code == 201
    assert item.json()["precio_snapshot"] == "0.90"

    # 5. Resumen de ahorro: % A y % C calculados.
    resumen = await cliente.get(
        f"/v1/listas/{lista_id}/resumen",
        params={"cadenas": "dia"},
        headers=cabeceras,
    )
    assert resumen.status_code == 200
    cuerpo = resumen.json()
    assert cuerpo["coste_total"] == "1.00"
    assert cuerpo["porcentaje_c"] == "0.0000"
    assert cuerpo["por_cadena"][0]["cadena"] == "dia"

    # 6. Búsqueda con caché: no encola job.
    cache = RedisCache(redis)
    clave = calcular_cache_key("leche entera", ("dia",), "precio_unitario", {}, None)
    await cache.set(clave, {"resultados": [{"nombre": "Leche entera"}]}, ttl=60)

    con_cache = await cliente.post(
        "/v1/busquedas",
        json={"query": "leche entera", "cadenas": ["dia"]},
        headers=cabeceras,
    )
    assert con_cache.status_code == 200
    assert con_cache.json()["cache_hit"] is True
    assert con_cache.json()["job_id"] is None
    assert con_cache.json()["resultados"] == [{"nombre": "Leche entera"}]
