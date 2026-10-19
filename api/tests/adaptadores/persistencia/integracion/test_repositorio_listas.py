from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.dominio.listas.entidades import ItemListaNuevo

pytestmark = pytest.mark.asyncio


async def test_crear_y_obtener_lista(sesion_rw: AsyncSession) -> None:
    repositorio = SQLAlchemyRepositorioListas(sesion_rw)
    usuario_id = uuid4()

    lista = await repositorio.crear(usuario_id, "Compra semanal")

    assert lista.usuario_id == usuario_id
    assert await repositorio.obtener(lista.id) == lista
    assert await repositorio.obtener(uuid4()) is None


async def test_listar_por_usuario_solo_devuelve_las_suyas(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioListas(sesion_rw)
    usuario_a = uuid4()
    usuario_b = uuid4()
    await repositorio.crear(usuario_a, "Despensa")
    await repositorio.crear(usuario_a, "Semanal")
    await repositorio.crear(usuario_b, "Ajena")

    listas = await repositorio.listar_por_usuario(usuario_a)

    assert {lista.nombre for lista in listas} == {"Despensa", "Semanal"}


async def test_agregar_item_y_listarlo(
    sesion_rw: AsyncSession, producto_base: UUID, cadena_dia: UUID
) -> None:
    repositorio = SQLAlchemyRepositorioListas(sesion_rw)
    lista = await repositorio.crear(None, "Favoritos")

    item = await repositorio.agregar_item(
        ItemListaNuevo(
            lista_id=lista.id,
            producto_id=producto_base,
            cantidad=2,
            cadena_compra_id=cadena_dia,
            precio_snapshot=Decimal("1.29"),
        )
    )

    assert item.cantidad == 2
    assert item.precio_snapshot == Decimal("1.29")
    assert await repositorio.obtener_items(lista.id) == [item]


async def test_actualizar_item(
    sesion_rw: AsyncSession, producto_base: UUID, cadena_dia: UUID
) -> None:
    repositorio = SQLAlchemyRepositorioListas(sesion_rw)
    lista = await repositorio.crear(None, "Compra")
    item = await repositorio.agregar_item(
        ItemListaNuevo(lista_id=lista.id, producto_id=producto_base)
    )

    actualizado = await repositorio.actualizar_item(
        item.id,
        cantidad=3,
        cadena_compra_id=cadena_dia,
        precio_snapshot=Decimal("1.59"),
    )

    assert actualizado is not None
    assert actualizado.cantidad == 3
    assert actualizado.cadena_compra_id == cadena_dia
    assert actualizado.precio_snapshot == Decimal("1.59")
    assert await repositorio.actualizar_item(uuid4(), cantidad=1) is None


async def test_eliminar_item(sesion_rw: AsyncSession, producto_base: UUID) -> None:
    repositorio = SQLAlchemyRepositorioListas(sesion_rw)
    lista = await repositorio.crear(None, "Compra")
    item = await repositorio.agregar_item(
        ItemListaNuevo(lista_id=lista.id, producto_id=producto_base)
    )

    assert await repositorio.eliminar_item(item.id) is True
    assert await repositorio.eliminar_item(item.id) is False
    assert await repositorio.obtener_items(lista.id) == []
