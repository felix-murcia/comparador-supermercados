"""Integración del CRUD de listas contra Postgres real."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.dominio.listas.entidades import ItemListaNuevo
from src.dominio.productos.entidades import ProductoNuevo
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


async def test_crud_completo_de_listas(cliente: AsyncClient) -> None:
    provider_id = f"listas-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra semanal"}, headers=cabeceras
    )
    assert creada.status_code == 201
    lista_id = creada.json()["id"]
    assert creada.json()["nombre"] == "Compra semanal"

    listado = await cliente.get("/v1/listas", headers=cabeceras)
    assert listado.status_code == 200
    assert [item["id"] for item in listado.json()] == [lista_id]

    renombrada = await cliente.patch(
        f"/v1/listas/{lista_id}", json={"nombre": "Navidad"}, headers=cabeceras
    )
    assert renombrada.status_code == 200
    assert renombrada.json()["nombre"] == "Navidad"

    detalle = await cliente.get(f"/v1/listas/{lista_id}", headers=cabeceras)
    assert detalle.status_code == 200
    assert detalle.json()["items"] == []

    borrada = await cliente.delete(f"/v1/listas/{lista_id}", headers=cabeceras)
    assert borrada.status_code == 204

    ausente = await cliente.get(f"/v1/listas/{lista_id}", headers=cabeceras)
    assert ausente.status_code == 404
    assert ausente.json()["code"] == "LISTA_NO_ENCONTRADA"


async def test_el_detalle_incluye_los_items(
    cliente: AsyncClient, sesion_rw: AsyncSession
) -> None:
    provider_id = f"items-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    await _crear_usuario(sesion_rw, provider_id)

    producto = await SQLAlchemyRepositorioProductos(sesion_rw).crear(
        ProductoNuevo(nombre="Leche entera", marca="Pascual")
    )
    await sesion_rw.commit()

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Con items"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]

    await SQLAlchemyRepositorioListas(sesion_rw).agregar_item(
        ItemListaNuevo(lista_id=UUID(lista_id), producto_id=producto.id, cantidad=2)
    )
    await sesion_rw.commit()

    detalle = await cliente.get(f"/v1/listas/{lista_id}", headers=cabeceras)

    assert detalle.status_code == 200
    items = detalle.json()["items"]
    assert len(items) == 1
    assert items[0]["cantidad"] == 2
    assert items[0]["producto_id"] == str(producto.id)


async def test_otro_usuario_no_puede_acceder(cliente: AsyncClient) -> None:
    dueno = f"dueno-{uuid4().hex[:8]}"
    intruso = f"intruso-{uuid4().hex[:8]}"

    creada = await cliente.post(
        "/v1/listas",
        json={"nombre": "Privada"},
        headers={"Authorization": f"Bearer {_token(dueno)}"},
    )
    lista_id = creada.json()["id"]
    cabeceras = {"Authorization": f"Bearer {_token(intruso)}"}

    detalle = await cliente.get(f"/v1/listas/{lista_id}", headers=cabeceras)
    renombrada = await cliente.patch(
        f"/v1/listas/{lista_id}", json={"nombre": "Robada"}, headers=cabeceras
    )
    borrada = await cliente.delete(f"/v1/listas/{lista_id}", headers=cabeceras)

    assert detalle.status_code == 403
    assert detalle.json()["code"] == "NO_AUTORIZADO"
    assert renombrada.status_code == 403
    assert borrada.status_code == 403


async def test_las_listas_de_otro_usuario_no_aparecen(cliente: AsyncClient) -> None:
    dueno = f"dueno-{uuid4().hex[:8]}"
    intruso = f"intruso-{uuid4().hex[:8]}"

    await cliente.post(
        "/v1/listas",
        json={"nombre": "Solo mía"},
        headers={"Authorization": f"Bearer {_token(dueno)}"},
    )

    listado = await cliente.get(
        "/v1/listas", headers={"Authorization": f"Bearer {_token(intruso)}"}
    )

    assert listado.status_code == 200
    assert listado.json() == []


async def test_sin_jwt_devuelve_401(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/v1/listas")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"
