from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.dominio.productos.entidades import ProductoNuevo

pytestmark = pytest.mark.asyncio


async def test_crear_producto_lo_persiste(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)

    creado = await repositorio.crear(
        ProductoNuevo(
            nombre="Leche entera",
            marca="Pascual",
            categoria="lacteos",
            formato="1L",
            litros_o_kg=Decimal(1),
            ean="8412345678901",
        )
    )

    assert creado.creado_en is not None
    assert await repositorio.obtener(creado.id) == creado


async def test_obtener_producto_inexistente_devuelve_none(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)

    assert await repositorio.obtener(uuid4()) is None


async def test_obtener_por_ean(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)
    creado = await repositorio.crear(
        ProductoNuevo(nombre="Pan de molde", ean="8411111111111")
    )

    assert await repositorio.obtener_por_ean("8411111111111") == creado
    assert await repositorio.obtener_por_ean("0000000000000") is None


async def test_buscar_por_nombre_encuentra_coincidencias(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)
    await repositorio.crear(ProductoNuevo(nombre="Leche entera"))
    await repositorio.crear(ProductoNuevo(nombre="Leche desnatada"))
    await repositorio.crear(ProductoNuevo(nombre="Pan de molde"))

    resultados = await repositorio.buscar_por_nombre("leche")

    assert {producto.nombre for producto in resultados} == {
        "Leche entera",
        "Leche desnatada",
    }


async def test_buscar_por_nombre_prioriza_la_coincidencia_exacta(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)
    await repositorio.crear(ProductoNuevo(nombre="Leche desnatada"))
    await repositorio.crear(ProductoNuevo(nombre="Leche entera"))

    resultados = await repositorio.buscar_por_nombre("Leche entera")

    assert resultados[0].nombre == "Leche entera"


async def test_buscar_por_nombre_escapa_comodines(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)
    await repositorio.crear(ProductoNuevo(nombre="Zumo 100% naranja"))
    await repositorio.crear(ProductoNuevo(nombre="Zumo de piña"))

    resultados = await repositorio.buscar_por_nombre("100%")

    assert [producto.nombre for producto in resultados] == ["Zumo 100% naranja"]


async def test_buscar_por_nombre_respeta_el_limite(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioProductos(sesion_rw)
    await repositorio.crear(ProductoNuevo(nombre="Leche entera"))
    await repositorio.crear(ProductoNuevo(nombre="Leche desnatada"))
    await repositorio.crear(ProductoNuevo(nombre="Leche semidesnatada"))

    resultados = await repositorio.buscar_por_nombre("leche", limite=2)

    assert len(resultados) == 2
