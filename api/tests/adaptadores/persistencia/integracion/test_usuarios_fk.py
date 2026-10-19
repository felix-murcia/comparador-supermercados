from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import (
    BusquedaModelo,
    ListaModelo,
    UsuarioModelo,
)
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.dominio.busquedas.entidades import BusquedaNueva

pytestmark = pytest.mark.asyncio


async def test_provider_y_provider_id_unicos(sesion_rw: AsyncSession) -> None:
    sesion_rw.add(
        UsuarioModelo(provider="google", provider_id="ana", email="ana@example.test")
    )
    await sesion_rw.flush()

    sesion_rw.add(
        UsuarioModelo(provider="google", provider_id="ana", email="otra@example.test")
    )

    with pytest.raises(IntegrityError):
        await sesion_rw.flush()

    await sesion_rw.rollback()


async def test_borrar_usuario_desvincula_busquedas_y_listas(
    sesion_rw: AsyncSession, crear_usuario: Callable[[str], Awaitable[UUID]]
) -> None:
    usuario_id = await crear_usuario("borrame")
    busqueda = await SQLAlchemyRepositorioBusquedas(sesion_rw).crear(
        BusquedaNueva(
            query="leche",
            cadenas=("dia",),
            cache_key="v1:borrame",
            usuario_id=usuario_id,
        )
    )
    lista = await SQLAlchemyRepositorioListas(sesion_rw).crear(usuario_id, "Compra")
    await sesion_rw.commit()

    await sesion_rw.execute(delete(UsuarioModelo).where(UsuarioModelo.id == usuario_id))
    await sesion_rw.commit()

    usuario_busqueda = await sesion_rw.scalar(
        select(BusquedaModelo.usuario_id).where(BusquedaModelo.id == busqueda.id)
    )
    usuario_lista = await sesion_rw.scalar(
        select(ListaModelo.usuario_id).where(ListaModelo.id == lista.id)
    )

    assert usuario_busqueda is None
    assert usuario_lista is None
