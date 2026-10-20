"""Integración de `PATCH /v1/me` contra Postgres real."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.dominio.usuarios.entidades import IdentidadOAuth
from src.main import app

_URL_RW = os.getenv("DATABASE_URL_RW")
_SECRETO = os.getenv("NEXTAUTH_SECRET")

if not _URL_RW or not _SECRETO:
    pytest.skip(
        "Requiere DATABASE_URL_RW y NEXTAUTH_SECRET para la integración",
        allow_module_level=True,
    )

assert _SECRETO is not None

pytestmark = pytest.mark.asyncio


def _token(provider_id: str) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    return pyjwt.encode(
        {
            "sub": f"authjs:google:{provider_id}",
            "email": f"{provider_id}@example.test",
            "name": "Ana",
            "provider": "google",
            "provider_id": provider_id,
            "iat": ahora,
            "exp": ahora + 300,
        },
        _SECRETO,
        algorithm="HS256",
    )


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


async def _crear_usuario(sesion: AsyncSession, provider_id: str) -> str:
    usuario = await SQLAlchemyRepositorioUsuarios(sesion).upsert(
        IdentidadOAuth(
            provider="google",
            provider_id=provider_id,
            email=f"{provider_id}@example.test",
            nombre="Ana",
        )
    )
    await sesion.commit()
    return str(usuario.id)


async def test_actualiza_nombre_y_provincia(
    cliente: AsyncClient, sesion_rw: AsyncSession
) -> None:
    provider_id = f"perfil-{uuid4().hex[:8]}"
    await _crear_usuario(sesion_rw, provider_id)

    respuesta = await cliente.patch(
        "/v1/me",
        json={"nombre": "Ana Actualizada", "provincia": "madrid"},
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Ana Actualizada"
    assert cuerpo["provincia"] == "Madrid"

    usuario = await SQLAlchemyRepositorioUsuarios(sesion_rw).obtener_por_provider(
        "google", provider_id
    )
    assert usuario is not None
    assert usuario.provincia == "Madrid"


async def test_rechaza_una_provincia_invalida(
    cliente: AsyncClient, sesion_rw: AsyncSession
) -> None:
    provider_id = f"invalida-{uuid4().hex[:8]}"
    await _crear_usuario(sesion_rw, provider_id)

    respuesta = await cliente.patch(
        "/v1/me",
        json={"provincia": "Atlántida"},
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "PROVINCIA_INVALIDA"


async def test_sin_jwt_devuelve_401(cliente: AsyncClient) -> None:
    respuesta = await cliente.patch("/v1/me", json={"nombre": "Sin sesión"})

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_lista_las_provincias(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/v1/provincias")

    assert respuesta.status_code == 200
    provincias = respuesta.json()["provincias"]
    assert len(provincias) == 52
    assert "Madrid" in provincias
