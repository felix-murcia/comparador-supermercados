"""Integración de `SQLAlchemyRepositorioUsuarios` contra Postgres real."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import UsuarioModelo
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.dominio.usuarios.entidades import IdentidadOAuth

pytestmark = pytest.mark.asyncio


async def test_upsert_crea_la_fila_y_luego_la_actualiza(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioUsuarios(sesion_rw)

    creado = await repositorio.upsert(
        IdentidadOAuth(
            provider="google",
            provider_id="123",
            email="ana@example.test",
            nombre="Ana",
            avatar_url="https://avatars.test/ana.png",
        )
    )
    await sesion_rw.commit()

    actualizado = await repositorio.upsert(
        IdentidadOAuth(
            provider="google",
            provider_id="123",
            email="ana.nueva@example.test",
            nombre="Ana Nueva",
        )
    )
    await sesion_rw.commit()

    assert actualizado.id == creado.id
    assert actualizado.email == "ana.nueva@example.test"
    assert actualizado.nombre == "Ana Nueva"
    assert actualizado.avatar_url is None

    total = await sesion_rw.scalar(select(func.count()).select_from(UsuarioModelo))
    assert total == 1


async def test_upsert_distingue_proveedores_con_el_mismo_id(
    sesion_rw: AsyncSession,
) -> None:
    repositorio = SQLAlchemyRepositorioUsuarios(sesion_rw)

    de_google = await repositorio.upsert(
        IdentidadOAuth(provider="google", provider_id="123", email="ana@example.test")
    )
    de_microsoft = await repositorio.upsert(
        IdentidadOAuth(
            provider="microsoft", provider_id="123", email="ana@example.test"
        )
    )
    await sesion_rw.commit()

    assert de_microsoft.id != de_google.id

    total = await sesion_rw.scalar(select(func.count()).select_from(UsuarioModelo))
    assert total == 2
