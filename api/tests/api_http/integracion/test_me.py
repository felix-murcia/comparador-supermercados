"""Integración de `GET /v1/me` contra Postgres real (T1.3).

Requiere `DATABASE_URL_RW` y `NEXTAUTH_SECRET` (el mismo secreto que usa
Auth.js para firmar la sesión) y el esquema migrado.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import UsuarioModelo
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


def _token(**sobrescritos: object) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    claims: dict[str, object] = {
        "sub": "authjs:google:123",
        "email": "ana@example.test",
        "name": "Ana",
        "picture": "https://avatars.test/ana.png",
        "provider": "google",
        "provider_id": "123",
        "iat": ahora,
        "exp": ahora + 300,
    }
    claims.update(sobrescritos)
    return pyjwt.encode(claims, _SECRETO, algorithm="HS256")


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


async def test_get_me_crea_usuario_en_el_primer_login(
    cliente: AsyncClient, sesion_rw: AsyncSession
) -> None:
    respuesta = await cliente.get(
        "/v1/me", headers={"Authorization": f"Bearer {_token()}"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "ana@example.test"
    assert cuerpo["nombre"] == "Ana"
    assert cuerpo["avatar_url"] == "https://avatars.test/ana.png"

    modelo = await sesion_rw.scalar(
        select(UsuarioModelo).where(
            UsuarioModelo.provider == "google",
            UsuarioModelo.provider_id == "123",
        )
    )
    assert modelo is not None
    assert str(modelo.id) == cuerpo["id"]


async def test_get_me_hace_upsert_sin_duplicar_usuario(
    cliente: AsyncClient, sesion_rw: AsyncSession
) -> None:
    primera = await cliente.get(
        "/v1/me", headers={"Authorization": f"Bearer {_token()}"}
    )
    segunda = await cliente.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {_token(email='ana.nueva@example.test')}"},
    )

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    assert segunda.json()["email"] == "ana.nueva@example.test"

    total = await sesion_rw.scalar(select(func.count()).select_from(UsuarioModelo))
    assert total == 1


async def test_get_me_sin_token_devuelve_401(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/v1/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_get_me_con_firma_invalida_devuelve_401(
    cliente: AsyncClient,
) -> None:
    token = pyjwt.encode(
        {"provider": "google", "provider_id": "123", "exp": 9999999999},
        "otro-secreto-de-integracion-t13-32-bytes",
        algorithm="HS256",
    )

    respuesta = await cliente.get(
        "/v1/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"
