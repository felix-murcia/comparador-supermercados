"""Integración de los repositorios de cadenas y de productos por cadena."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_cadenas import (
    SQLAlchemyRepositorioCadenas,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.dominio.productos.entidades import ProductoNuevo

pytestmark = pytest.mark.asyncio


async def test_obtener_cadena_por_slug(sesion_rw: AsyncSession, cadena_dia) -> None:
    repositorio = SQLAlchemyRepositorioCadenas(sesion_rw)

    cadena = await repositorio.obtener_por_slug("dia")

    assert cadena is not None
    assert cadena.slug == "dia"
    assert cadena.nombre == "DIA"
    assert cadena.id == cadena_dia


async def test_obtener_cadena_por_slug_desconocida(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioCadenas(sesion_rw)

    assert await repositorio.obtener_por_slug("no-existe") is None


async def test_crea_y_recupera_el_producto_de_la_cadena(
    sesion_rw: AsyncSession, cadena_dia, producto_base
) -> None:
    repositorio = SQLAlchemyRepositorioProductosCadenas(sesion_rw)

    assert (
        await repositorio.obtener_por_producto_y_cadena(producto_base, cadena_dia)
        is None
    )

    creado = await repositorio.crear(
        producto_id=producto_base,
        cadena_id=cadena_dia,
        url_producto="https://dia.test/leche-entera",
        nombre_en_cadena="Leche entera Pascual 1L",
    )
    await sesion_rw.commit()

    assert (
        await repositorio.obtener_por_producto_y_cadena(producto_base, cadena_dia)
        == creado
    )


async def test_el_producto_de_otra_cadena_no_se_confunde(
    sesion_rw: AsyncSession, cadena_dia, producto_base
) -> None:
    repositorio = SQLAlchemyRepositorioProductosCadenas(sesion_rw)
    otra_cadena = await SQLAlchemyRepositorioCadenas(sesion_rw).obtener_por_slug("dia")
    assert otra_cadena is not None

    creado = await repositorio.crear(
        producto_id=producto_base,
        cadena_id=cadena_dia,
        url_producto="https://dia.test/leche-entera",
        nombre_en_cadena="Leche entera Pascual 1L",
    )
    await sesion_rw.commit()

    otro_producto = await SQLAlchemyRepositorioProductos(sesion_rw).crear(
        ProductoNuevo(nombre="Leche de avena", marca="Pascual")
    )
    await sesion_rw.commit()

    assert (
        await repositorio.obtener_por_producto_y_cadena(otro_producto.id, cadena_dia)
        is None
    )
    assert creado != otro_producto.id
