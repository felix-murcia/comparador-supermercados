"""Fixtures compartidas de integración contra Postgres real.

Requieren `DATABASE_URL_RW` (obligatoria), opcionalmente `DATABASE_URL_RO`
para los tests de routing, y el esquema migrado (`alembic upgrade head`).
Sin variables de entorno, los tests que las piden se saltan en lugar de fallar.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from decimal import Decimal
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.adaptadores.persistencia.modelos import (
    CadenaModelo,
    ProductoCadenaModelo,
    ProductoModelo,
    UsuarioModelo,
)

_TABLAS = (
    "ingesta_metricas",
    "precios",
    "lista_items",
    "listas",
    "busquedas",
    "productos_cadena",
    "productos",
    "cadenas",
    "usuarios",
)


def _url_entorno(nombre: str) -> str | None:
    return os.getenv(nombre) or None


@pytest_asyncio.fixture
async def motor_rw() -> AsyncIterator[AsyncEngine]:
    url = _url_entorno("DATABASE_URL_RW")
    if url is None:
        pytest.skip("DATABASE_URL_RW no está configurada")
    motor = create_async_engine(url)
    try:
        yield motor
    finally:
        await motor.dispose()


@pytest_asyncio.fixture
async def motor_ro() -> AsyncIterator[AsyncEngine]:
    url = _url_entorno("DATABASE_URL_RO")
    if url is None:
        pytest.skip("DATABASE_URL_RO no está configurada")
    motor = create_async_engine(url)
    try:
        yield motor
    finally:
        await motor.dispose()


@pytest_asyncio.fixture
async def _base_limpia(motor_rw: AsyncEngine) -> AsyncIterator[None]:
    async with motor_rw.begin() as conexion:
        existe = await conexion.scalar(
            text("SELECT to_regclass('public.productos') IS NOT NULL")
        )
        if not existe:
            pytest.skip("Esquema no migrado: ejecuta `alembic upgrade head`")
        await conexion.execute(text(f"TRUNCATE TABLE {', '.join(_TABLAS)} CASCADE"))
    yield


@pytest_asyncio.fixture
async def sesion_rw(
    motor_rw: AsyncEngine, _base_limpia: None
) -> AsyncIterator[AsyncSession]:
    fabrica = async_sessionmaker(motor_rw, expire_on_commit=False)
    async with fabrica() as sesion:
        yield sesion
        await sesion.rollback()


@pytest_asyncio.fixture
async def sesion_ro(
    motor_ro: AsyncEngine, _base_limpia: None
) -> AsyncIterator[AsyncSession]:
    fabrica = async_sessionmaker(motor_ro, expire_on_commit=False)
    async with fabrica() as sesion:
        yield sesion
        await sesion.rollback()


# ===== Factories para los tests de repositorios =====


@pytest_asyncio.fixture
async def cadena_dia(sesion_rw: AsyncSession) -> UUID:
    modelo = CadenaModelo(slug="dia", nombre="DIA", logo_svg="<svg></svg>")
    sesion_rw.add(modelo)
    await sesion_rw.flush()
    await sesion_rw.refresh(modelo)
    await sesion_rw.commit()
    return modelo.id


@pytest_asyncio.fixture
async def producto_base(sesion_rw: AsyncSession) -> UUID:
    modelo = ProductoModelo(
        nombre="Leche entera",
        marca="Pascual",
        categoria="lacteos",
        formato="1L",
        litros_o_kg=Decimal(1),
        ean="8412345678901",
    )
    sesion_rw.add(modelo)
    await sesion_rw.flush()
    await sesion_rw.refresh(modelo)
    await sesion_rw.commit()
    return modelo.id


@pytest_asyncio.fixture
async def producto_cadena_base(
    sesion_rw: AsyncSession, cadena_dia: UUID, producto_base: UUID
) -> UUID:
    modelo = ProductoCadenaModelo(
        producto_id=producto_base,
        cadena_id=cadena_dia,
        url_producto="https://dia.test/leche-entera",
        nombre_en_cadena="Leche entera Pascual 1L",
    )
    sesion_rw.add(modelo)
    await sesion_rw.flush()
    await sesion_rw.refresh(modelo)
    await sesion_rw.commit()
    return modelo.id


@pytest_asyncio.fixture
async def crear_usuario(
    sesion_rw: AsyncSession,
) -> Callable[[str], Awaitable[UUID]]:
    async def _crear(provider_id: str) -> UUID:
        modelo = UsuarioModelo(
            provider="google",
            provider_id=provider_id,
            email=f"{provider_id}@example.test",
            nombre=f"Usuaria {provider_id}",
        )
        sesion_rw.add(modelo)
        await sesion_rw.flush()
        await sesion_rw.refresh(modelo)
        await sesion_rw.commit()
        return modelo.id

    return _crear
