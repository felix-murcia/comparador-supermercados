from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.seed import ejecutar_seed
from src.adaptadores.persistencia.modelos import (
    CadenaModelo,
    PrecioModelo,
    ProductoCadenaModelo,
    ProductoModelo,
)

pytestmark = pytest.mark.asyncio


async def _contar(sesion: AsyncSession, modelo: type[object]) -> int:
    total = await sesion.scalar(select(func.count()).select_from(modelo))
    return int(total or 0)


async def test_seed_crea_el_catalogo_completo(sesion_rw: AsyncSession) -> None:
    await ejecutar_seed(sesion_rw)
    await sesion_rw.commit()

    assert await _contar(sesion_rw, CadenaModelo) == 3
    assert await _contar(sesion_rw, ProductoModelo) == 100
    assert await _contar(sesion_rw, ProductoCadenaModelo) == 300
    assert await _contar(sesion_rw, PrecioModelo) == 300

    cadenas = (await sesion_rw.scalars(select(CadenaModelo))).all()
    assert {cadena.slug for cadena in cadenas} == {"dia", "carrefour", "mercadona"}
    assert all(cadena.logo_svg.startswith("<svg") for cadena in cadenas)

    productos = (await sesion_rw.scalars(select(ProductoModelo))).all()
    assert all(producto.formato for producto in productos)
    assert all(
        producto.litros_o_kg is not None and producto.litros_o_kg > 0
        for producto in productos
    )

    sin_url = await sesion_rw.scalar(
        select(func.count())
        .select_from(ProductoCadenaModelo)
        .where(ProductoCadenaModelo.url_producto == "")
    )
    assert sin_url == 0

    no_verificados = await sesion_rw.scalar(
        select(func.count())
        .select_from(PrecioModelo)
        .where(
            (PrecioModelo.estado != "verificado") | (PrecioModelo.ambito != "nacional")
        )
    )
    assert no_verificados == 0


async def test_seed_es_idempotente(sesion_rw: AsyncSession) -> None:
    await ejecutar_seed(sesion_rw)
    await sesion_rw.commit()

    await ejecutar_seed(sesion_rw)
    await sesion_rw.commit()

    assert await _contar(sesion_rw, CadenaModelo) == 3
    assert await _contar(sesion_rw, ProductoModelo) == 100
    assert await _contar(sesion_rw, ProductoCadenaModelo) == 300
    assert await _contar(sesion_rw, PrecioModelo) == 300
