"""Implementación SQLAlchemy de `RepositorioListas`."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import (
    item_lista_desde_modelo,
    lista_desde_modelo,
)
from src.adaptadores.persistencia.modelos import ItemListaModelo, ListaModelo
from src.dominio.listas.entidades import ItemLista, ItemListaNuevo, Lista


class SQLAlchemyRepositorioListas:
    """Listas e items; las escrituras requieren sesión RW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def crear(self, usuario_id: UUID | None, nombre: str) -> Lista:
        modelo = ListaModelo(usuario_id=usuario_id, nombre=nombre)
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return lista_desde_modelo(modelo)

    async def obtener(self, lista_id: UUID) -> Lista | None:
        modelo = await self._session.get(ListaModelo, lista_id)
        if modelo is None:
            return None
        return lista_desde_modelo(modelo)

    async def listar_por_usuario(self, usuario_id: UUID) -> list[Lista]:
        modelos = (
            await self._session.scalars(
                select(ListaModelo)
                .where(ListaModelo.usuario_id == usuario_id)
                .order_by(ListaModelo.creado_en.desc(), ListaModelo.nombre)
            )
        ).all()
        return [lista_desde_modelo(modelo) for modelo in modelos]

    async def renombrar(self, lista_id: UUID, nombre: str) -> Lista | None:
        modelo = await self._session.get(ListaModelo, lista_id)
        if modelo is None:
            return None
        modelo.nombre = nombre
        await self._session.flush()
        await self._session.refresh(modelo)
        return lista_desde_modelo(modelo)

    async def eliminar(self, lista_id: UUID) -> bool:
        """Borra la lista; sus items caen en cascada (FK `ON DELETE CASCADE`)."""
        resultado = await self._session.execute(
            delete(ListaModelo)
            .where(ListaModelo.id == lista_id)
            .returning(ListaModelo.id)
        )
        return resultado.first() is not None

    async def agregar_item(self, datos: ItemListaNuevo) -> ItemLista:
        modelo = ItemListaModelo(
            lista_id=datos.lista_id,
            producto_id=datos.producto_id,
            cantidad=datos.cantidad,
            cadena_compra_id=datos.cadena_compra_id,
            precio_snapshot=datos.precio_snapshot,
        )
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return item_lista_desde_modelo(modelo)

    async def obtener_items(self, lista_id: UUID) -> list[ItemLista]:
        modelos = (
            await self._session.scalars(
                select(ItemListaModelo)
                .where(ItemListaModelo.lista_id == lista_id)
                .order_by(ItemListaModelo.creado_en, ItemListaModelo.id)
            )
        ).all()
        return [item_lista_desde_modelo(modelo) for modelo in modelos]

    async def actualizar_item(
        self,
        item_id: UUID,
        *,
        cantidad: int | None = None,
        cadena_compra_id: UUID | None = None,
        precio_snapshot: Decimal | None = None,
    ) -> ItemLista | None:
        modelo = await self._session.get(ItemListaModelo, item_id)
        if modelo is None:
            return None
        if cantidad is not None:
            modelo.cantidad = cantidad
        if cadena_compra_id is not None:
            modelo.cadena_compra_id = cadena_compra_id
        if precio_snapshot is not None:
            modelo.precio_snapshot = precio_snapshot
        await self._session.flush()
        await self._session.refresh(modelo)
        return item_lista_desde_modelo(modelo)

    async def eliminar_item(self, item_id: UUID) -> bool:
        resultado = await self._session.execute(
            delete(ItemListaModelo)
            .where(ItemListaModelo.id == item_id)
            .returning(ItemListaModelo.id)
        )
        return resultado.first() is not None
