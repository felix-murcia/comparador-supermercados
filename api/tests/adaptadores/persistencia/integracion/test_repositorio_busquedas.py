from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.dominio.busquedas.entidades import BusquedaNueva

pytestmark = pytest.mark.asyncio


async def test_crear_busqueda_con_estado_inicial(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)

    busqueda = await repositorio.crear(
        BusquedaNueva(
            query="leche entera",
            cadenas=("dia", "carrefour"),
            cache_key="v1:abc123",
            provincia="Madrid",
        )
    )

    assert busqueda.estado == "pendiente"
    assert busqueda.progreso == 0
    assert busqueda.completado_en is None
    assert busqueda.cadenas == ("dia", "carrefour")
    assert await repositorio.obtener(busqueda.id) == busqueda
    assert await repositorio.obtener(uuid4()) is None


async def test_obtener_por_cache_key_devuelve_la_mas_reciente(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)
    await repositorio.crear(
        BusquedaNueva(query="leche", cadenas=("dia",), cache_key="v1:misma")
    )
    await sesion_rw.commit()
    reciente = await repositorio.crear(
        BusquedaNueva(query="leche entera", cadenas=("dia",), cache_key="v1:misma")
    )

    encontrada = await repositorio.obtener_por_cache_key("v1:misma")

    assert encontrada is not None
    assert encontrada.id == reciente.id
    assert await repositorio.obtener_por_cache_key("v1:otra") is None


async def test_actualizar_estado(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)
    busqueda = await repositorio.crear(
        BusquedaNueva(query="pan", cadenas=("dia",), cache_key="v1:pan")
    )
    completado_en = datetime(2026, 10, 19, 12, 30, tzinfo=UTC)

    actualizada = await repositorio.actualizar_estado(
        busqueda.id, "completada", 100, completado_en
    )

    assert actualizada is not None
    assert actualizada.estado == "completada"
    assert actualizada.progreso == 100
    assert actualizada.completado_en == completado_en
    assert await repositorio.actualizar_estado(uuid4(), "fallida", 0) is None
