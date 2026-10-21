"""Integración de `GET /v1/comparar` contra Postgres real."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.cache.redis_cache import RedisCache
from src.adaptadores.persistencia.modelos import (
    CadenaModelo,
    PrecioModelo,
    ProductoCadenaModelo,
    ProductoModelo,
)
from src.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


async def _preparar_datos(sesion: AsyncSession) -> None:
    dia = CadenaModelo(slug="dia", nombre="DIA", logo_svg="<svg></svg>")
    carrefour = CadenaModelo(
        slug="carrefour", nombre="Carrefour", logo_svg="<svg></svg>"
    )
    sesion.add_all([dia, carrefour])
    await sesion.flush()

    leche = ProductoModelo(
        nombre="Leche entera",
        marca="Pascual",
        categoria="lacteos",
        formato="1L",
        litros_o_kg=Decimal(1),
        ean="8412345678901",
    )
    avena = ProductoModelo(
        nombre="Leche de avena",
        marca="Pascual",
        categoria="lacteos",
        formato="1L",
        litros_o_kg=Decimal(1),
        ean="8412345678902",
    )
    agua = ProductoModelo(
        nombre="Agua mineral",
        marca="Aquarius",
        categoria="bebidas",
        formato="1.5L",
        litros_o_kg=Decimal("1.5"),
        ean="8412345678903",
    )
    aceite = ProductoModelo(
        nombre="Aceite de oliva virgen extra",
        marca="Carbonell",
        categoria="aceites",
        formato="1 L",
        litros_o_kg=Decimal(1),
        ean="8412345678904",
    )
    sesion.add_all([leche, avena, agua, aceite])
    await sesion.flush()

    aceite_dia = ProductoCadenaModelo(
        producto_id=aceite.id,
        cadena_id=dia.id,
        url_producto="https://dia.test/aceite",
        nombre_en_cadena="Aceite de oliva virgen extra 1 L",
    )
    sesion.add(aceite_dia)
    await sesion.flush()
    sesion.add(
        PrecioModelo(
            producto_cadena_id=aceite_dia.id,
            precio_eur=Decimal("4.50"),
            precio_por_litro_kg=Decimal("4.5000"),
            disponible=True,
            ambito="nacional",
            url_fuente="https://dia.test/aceite",
            fecha_consulta=datetime.now(UTC),
            estado="verificado",
        )
    )

    leche_dia = ProductoCadenaModelo(
        producto_id=leche.id,
        cadena_id=dia.id,
        url_producto="https://dia.test/leche",
        nombre_en_cadena="Leche entera 1L",
    )
    leche_carrefour = ProductoCadenaModelo(
        producto_id=leche.id,
        cadena_id=carrefour.id,
        url_producto="https://carrefour.test/leche",
        nombre_en_cadena="Leche entera Pascual 1L",
    )
    avena_dia = ProductoCadenaModelo(
        producto_id=avena.id,
        cadena_id=dia.id,
        url_producto="https://dia.test/avena",
        nombre_en_cadena="Leche de avena 1L",
    )
    agua_dia = ProductoCadenaModelo(
        producto_id=agua.id,
        cadena_id=dia.id,
        url_producto="https://dia.test/agua",
        nombre_en_cadena="Agua mineral 1.5L",
    )
    sesion.add_all([leche_dia, leche_carrefour, avena_dia, agua_dia])
    await sesion.flush()

    ahora = datetime.now(UTC)
    sesion.add_all(
        [
            PrecioModelo(
                producto_cadena_id=leche_dia.id,
                precio_eur=Decimal("1.29"),
                precio_por_litro_kg=Decimal("1.29"),
                disponible=True,
                estado="verificado",
                ambito="nacional",
                url_fuente="https://dia.test/leche",
                fecha_consulta=ahora,
            ),
            PrecioModelo(
                producto_cadena_id=leche_carrefour.id,
                precio_eur=Decimal("1.50"),
                precio_por_litro_kg=Decimal("1.50"),
                disponible=True,
                estado="verificado",
                ambito="nacional",
                url_fuente="https://carrefour.test/leche",
                fecha_consulta=ahora,
            ),
            PrecioModelo(
                producto_cadena_id=avena_dia.id,
                precio_eur=Decimal("1.10"),
                precio_por_litro_kg=Decimal("1.10"),
                disponible=False,
                estado="verificado",
                ambito="nacional",
                url_fuente="https://dia.test/avena",
                fecha_consulta=ahora,
            ),
            PrecioModelo(
                producto_cadena_id=agua_dia.id,
                precio_eur=Decimal("0.80"),
                precio_por_litro_kg=Decimal("0.5333"),
                disponible=True,
                estado="verificado",
                ambito="nacional",
                url_fuente="https://dia.test/agua",
                fecha_consulta=ahora,
            ),
            PrecioModelo(
                producto_cadena_id=agua_dia.id,
                precio_eur=Decimal("0.90"),
                precio_por_litro_kg=Decimal("0.6000"),
                disponible=True,
                estado="verificado",
                ambito="provincia",
                provincia="madrid",
                url_fuente="https://dia.test/agua-madrid",
                fecha_consulta=ahora,
            ),
        ]
    )
    await sesion.commit()


@pytest_asyncio.fixture
async def datos(
    sesion_rw: AsyncSession,
    sesion_ro: AsyncSession,
    esperar_replica: Callable[..., Awaitable[None]],
) -> None:
    await _preparar_datos(sesion_rw)
    await esperar_replica(sesion_rw, sesion_ro)
    await _limpiar_cache()


async def _limpiar_cache() -> None:
    """La comparativa se cachea: los tests necesitan datos frescos."""
    if not os.getenv("REDIS_URL"):
        return
    redis = Redis.from_url(str(os.getenv("REDIS_URL")), decode_responses=True)
    try:
        await RedisCache(redis).invalidar_prefijo("v1:")
    finally:
        await redis.aclose()


async def test_ordena_por_precio_unitario_por_defecto(
    cliente: AsyncClient, datos: None
) -> None:
    respuesta = await cliente.get("/v1/comparar", params={"q": "leche"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["orden"] == "precio_unitario"
    assert [r["nombre"] for r in cuerpo["resultados"]] == [
        "Leche de avena",
        "Leche entera",
        "Leche entera",
    ]
    assert [r["precio_eur"] for r in cuerpo["resultados"]] == [
        "1.10",
        "1.29",
        "1.50",
    ]
    assert [r["posicion"] for r in cuerpo["resultados"]] == [1, 2, 3]


async def test_filtra_por_cadenas(cliente: AsyncClient, datos: None) -> None:
    respuesta = await cliente.get(
        "/v1/comparar", params={"q": "leche", "cadenas": "carrefour"}
    )

    cuerpo = respuesta.json()
    assert [r["cadena"] for r in cuerpo["resultados"]] == ["carrefour"]


async def test_filtra_por_marca_y_categoria(cliente: AsyncClient, datos: None) -> None:
    por_marca = await cliente.get(
        "/v1/comparar", params={"q": "leche", "marca": "Pascual"}
    )
    por_categoria = await cliente.get(
        "/v1/comparar", params={"q": "agua", "categoria": "bebidas"}
    )
    otra_categoria = await cliente.get(
        "/v1/comparar", params={"q": "agua", "categoria": "lacteos"}
    )

    assert len(por_marca.json()["resultados"]) == 3
    assert len(por_categoria.json()["resultados"]) == 1
    assert otra_categoria.json()["resultados"] == []


async def test_filtra_por_rango_de_precio(cliente: AsyncClient, datos: None) -> None:
    respuesta = await cliente.get(
        "/v1/comparar", params={"q": "leche", "precio_min": "1.20"}
    )

    assert [r["precio_eur"] for r in respuesta.json()["resultados"]] == [
        "1.29",
        "1.50",
    ]


async def test_filtra_solo_con_stock(cliente: AsyncClient, datos: None) -> None:
    respuesta = await cliente.get(
        "/v1/comparar", params={"q": "leche", "solo_con_stock": "true"}
    )

    assert [r["nombre"] for r in respuesta.json()["resultados"]] == [
        "Leche entera",
        "Leche entera",
    ]


async def test_ordena_por_precio_por_kilo(cliente: AsyncClient, datos: None) -> None:
    respuesta = await cliente.get(
        "/v1/comparar", params={"q": "agua", "orden": "precio_kg_l"}
    )

    cuerpo = respuesta.json()
    assert cuerpo["orden"] == "precio_kg_l"
    assert cuerpo["resultados"][0]["precio_por_litro_kg"] == "0.5333"


async def test_usa_el_precio_de_la_provincia_y_hace_fallback(
    cliente: AsyncClient, datos: None
) -> None:
    con_provincia = await cliente.get(
        "/v1/comparar", params={"q": "agua", "provincia": "madrid"}
    )
    sin_provincia = await cliente.get("/v1/comparar", params={"q": "agua"})
    otra_provincia = await cliente.get(
        "/v1/comparar", params={"q": "agua", "provincia": "barcelona"}
    )

    assert con_provincia.json()["resultados"][0]["precio_eur"] == "0.90"
    assert con_provincia.json()["resultados"][0]["ambito"] == "provincia"
    assert sin_provincia.json()["resultados"][0]["precio_eur"] == "0.80"
    assert sin_provincia.json()["resultados"][0]["ambito"] == "nacional"
    assert otra_provincia.json()["resultados"][0]["precio_eur"] == "0.80"


async def test_pagina_los_resultados(cliente: AsyncClient, datos: None) -> None:
    respuesta = await cliente.get(
        "/v1/comparar", params={"q": "leche", "limit": 1, "offset": 1}
    )

    cuerpo = respuesta.json()
    assert cuerpo["limit"] == 1
    assert cuerpo["offset"] == 1
    assert [r["nombre"] for r in cuerpo["resultados"]] == ["Leche entera"]
    assert cuerpo["resultados"][0]["posicion"] == 2


async def test_sin_resultados_devuelve_lista_vacia(
    cliente: AsyncClient, datos: None
) -> None:
    respuesta = await cliente.get("/v1/comparar", params={"q": "chocolate"})

    assert respuesta.status_code == 200
    assert respuesta.json()["resultados"] == []


async def test_encuentra_el_producto_sea_espacio_o_no_antes_de_la_unidad(
    cliente: AsyncClient, datos: None
) -> None:
    """La unidad se escribe "1L" o "1 L": las dos consultas deben encontrarlo.

    El nombre en la base de datos es "Leche entera" con formato "1L", y el
    usuario escribe "leche entera 1L" o "leche entera 1 L".
    """
    sin_espacio = await cliente.get("/v1/comparar", params={"q": "leche entera 1L"})
    con_espacio = await cliente.get("/v1/comparar", params={"q": "leche entera 1 L"})

    assert sin_espacio.status_code == 200
    assert con_espacio.status_code == 200
    assert sin_espacio.json()["resultados"], "no encontró 'leche entera 1L'"
    assert con_espacio.json()["resultados"], "no encontró 'leche entera 1 L'"


async def test_busca_por_terminos_y_no_por_subcadena(
    cliente: AsyncClient, datos: None
) -> None:
    """La búsqueda va por términos: "aceite oliva" encuentra el producto.

    En el nombre hay palabras de por medio ("Aceite *de* oliva virgen
    extra"), así que la consulta no aparece como subcadena continua. Con la
    similitud de trigramas tampoco sale: da 0,448.
    """
    respuesta = await cliente.get("/v1/comparar", params={"q": "aceite oliva"})

    assert respuesta.status_code == 200
    nombres = [r["nombre"] for r in respuesta.json()["resultados"]]
    assert "Aceite de oliva virgen extra" in nombres


async def test_no_confunde_productos_por_parecidos(
    cliente: AsyncClient, datos: None
) -> None:
    """ "leche entera" no debe traer "Leche de avena" ni "Agua mineral"."""
    respuesta = await cliente.get("/v1/comparar", params={"q": "leche entera"})

    assert respuesta.status_code == 200
    nombres = [r["nombre"] for r in respuesta.json()["resultados"]]
    assert "Leche de avena" not in nombres
    assert "Agua mineral" not in nombres
