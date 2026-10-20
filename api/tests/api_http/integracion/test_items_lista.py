"""Integración de los items de lista contra Postgres real."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.productos.entidades import ProductoNuevo
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


async def _producto_con_precio(
    sesion: AsyncSession, cadena_id: UUID
) -> tuple[str, str]:
    """Crea un producto con precio en DIA.

    Devuelve el id del producto y el id de la cadena donde se compra.
    """
    producto = await SQLAlchemyRepositorioProductos(sesion).crear(
        ProductoNuevo(nombre="Leche entera", marca="Pascual")
    )
    producto_cadena_id = await SQLAlchemyRepositorioProductosCadenas(sesion).crear(
        producto_id=producto.id,
        cadena_id=cadena_id,
        url_producto="https://dia.test/leche",
        nombre_en_cadena="Leche entera 1L",
    )
    await SQLAlchemyRepositorioPrecios(sesion).insertar(
        PrecioNuevo(
            producto_cadena_id=producto_cadena_id,
            importe_eur=Decimal("1.19"),
            url_fuente="https://dia.test/leche",
            fecha_consulta=datetime.now(UTC),
        )
    )
    await sesion.commit()
    return str(producto.id), str(cadena_id)


async def test_añade_un_item_con_el_precio_del_momento(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id = f"items-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, cadena_id = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]

    respuesta = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cadena_compra_id": cadena_id, "cantidad": 2},
        headers=cabeceras,
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["producto_id"] == producto_id
    assert cuerpo["cantidad"] == 2
    assert cuerpo["cadena_compra_id"] == cadena_id
    assert cuerpo["precio_snapshot"] == "1.19"

    detalle = await cliente.get(f"/v1/listas/{lista_id}", headers=cabeceras)
    assert detalle.status_code == 200
    items = detalle.json()["items"]
    assert len(items) == 1
    assert items[0]["producto_nombre"] == "Leche entera"
    assert items[0]["producto_marca"] == "Pascual"


async def test_cambia_la_cantidad(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id = f"cantidad-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, cadena_id = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]
    item = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cadena_compra_id": cadena_id},
        headers=cabeceras,
    )

    respuesta = await cliente.patch(
        f"/v1/listas/{lista_id}/items/{item.json()['id']}",
        json={"cantidad": 5},
        headers=cabeceras,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["cantidad"] == 5


async def test_quita_un_item(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id = f"quitar-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, cadena_id = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]
    item = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cadena_compra_id": cadena_id},
        headers=cabeceras,
    )

    borrado = await cliente.delete(
        f"/v1/listas/{lista_id}/items/{item.json()['id']}", headers=cabeceras
    )

    assert borrado.status_code == 204
    detalle = await cliente.get(f"/v1/listas/{lista_id}", headers=cabeceras)
    assert detalle.json()["items"] == []


async def test_rechaza_un_producto_inexistente(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id = f"inexistente-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]

    respuesta = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": str(uuid4())},
        headers=cabeceras,
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "PRODUCTO_NO_ENCONTRADO"


async def test_rechaza_una_cantidad_invalida(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id = f"cantidad-invalida-{uuid4().hex[:8]}"
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    producto_id, _ = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas", json={"nombre": "Compra"}, headers=cabeceras
    )
    lista_id = creada.json()["id"]

    respuesta = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cantidad": 0},
        headers=cabeceras,
    )

    assert respuesta.status_code == 422


async def test_otro_usuario_no_puede_tocar_los_items(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    dueno = f"dueno-{uuid4().hex[:8]}"
    intruso = f"intruso-{uuid4().hex[:8]}"
    producto_id, cadena_id = await _producto_con_precio(sesion_rw, cadena_dia)

    creada = await cliente.post(
        "/v1/listas",
        json={"nombre": "Privada"},
        headers={"Authorization": f"Bearer {_token(dueno)}"},
    )
    lista_id = creada.json()["id"]
    item = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id, "cadena_compra_id": cadena_id},
        headers={"Authorization": f"Bearer {_token(dueno)}"},
    )
    cabeceras = {"Authorization": f"Bearer {_token(intruso)}"}

    anadido = await cliente.post(
        f"/v1/listas/{lista_id}/items",
        json={"producto_id": producto_id},
        headers=cabeceras,
    )
    actualizado = await cliente.patch(
        f"/v1/listas/{lista_id}/items/{item.json()['id']}",
        json={"cantidad": 9},
        headers=cabeceras,
    )
    borrado = await cliente.delete(
        f"/v1/listas/{lista_id}/items/{item.json()['id']}", headers=cabeceras
    )

    assert anadido.status_code == 403
    assert actualizado.status_code == 403
    assert borrado.status_code == 403
