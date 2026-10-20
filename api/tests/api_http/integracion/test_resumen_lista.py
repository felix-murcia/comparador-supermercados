"""Integración de `GET /v1/listas/{id}/resumen` contra Postgres real."""

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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_cadenas import (
    SQLAlchemyRepositorioCadenas,
)
from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.dominio.listas.entidades import ItemListaNuevo
from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.productos.entidades import ProductoNuevo
from src.main import app

_URL_RW = os.getenv("DATABASE_URL_RW")
_REDIS_URL = os.getenv("REDIS_URL")
_SECRETO = os.getenv("NEXTAUTH_SECRET")

if not _URL_RW or not _REDIS_URL or not _SECRETO:
    pytest.skip(
        "Requiere DATABASE_URL_RW, REDIS_URL y NEXTAUTH_SECRET para la integración",
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


async def _lista_con_precios(
    sesion: AsyncSession, cadena_dia: UUID
) -> tuple[str, str, UUID]:
    """Crea la lista de un usuario con un producto comprado en DIA."""
    from src.adaptadores.persistencia.repositorio_usuarios import (
        SQLAlchemyRepositorioUsuarios,
    )
    from src.dominio.usuarios.entidades import IdentidadOAuth

    provider_id = f"resumen-{uuid4().hex[:8]}"
    usuario = await SQLAlchemyRepositorioUsuarios(sesion).upsert(
        IdentidadOAuth(
            provider="google",
            provider_id=provider_id,
            email=f"{provider_id}@example.test",
            nombre="Ana",
        )
    )
    await sesion.commit()

    cadenas = SQLAlchemyRepositorioCadenas(sesion)
    dia = await cadenas.obtener_por_id(cadena_dia)
    assert dia is not None
    carrefour = await cadenas.obtener_por_slug("carrefour")
    if carrefour is None:
        # La base de datos de tests no siempre tiene las tres cadenas.
        await sesion.execute(
            text(
                "INSERT INTO cadenas (slug, nombre, logo_svg) "
                "VALUES ('carrefour', 'Carrefour', '<svg></svg>') "
                "ON CONFLICT (slug) DO NOTHING"
            )
        )
        await sesion.commit()
        carrefour = await cadenas.obtener_por_slug("carrefour")
    assert carrefour is not None

    producto = await SQLAlchemyRepositorioProductos(sesion).crear(
        ProductoNuevo(nombre="Leche entera", marca="Pascual")
    )
    await sesion.commit()

    mappings = SQLAlchemyRepositorioProductosCadenas(sesion)
    precios = SQLAlchemyRepositorioPrecios(sesion)
    for cadena, importe in ((dia, "1.00"), (carrefour, "2.00")):
        producto_cadena = await mappings.crear(
            producto_id=producto.id,
            cadena_id=cadena.id,
            url_producto="https://ejemplo.test/leche",
            nombre_en_cadena="Leche entera 1L",
        )
        await precios.insertar(
            PrecioNuevo(
                producto_cadena_id=producto_cadena,
                importe_eur=Decimal(importe),
                url_fuente="https://ejemplo.test/leche",
                fecha_consulta=datetime.now(UTC),
            )
        )
    await sesion.commit()

    listas = SQLAlchemyRepositorioListas(sesion)
    lista = await listas.crear(usuario.id, "Compra")
    await listas.agregar_item(
        ItemListaNuevo(
            lista_id=lista.id,
            producto_id=producto.id,
            cantidad=1,
            cadena_compra_id=dia.id,
        )
    )
    await sesion.commit()

    return provider_id, str(lista.id), dia.id


async def test_devuelve_el_resumen_de_la_lista(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id, lista_id, _ = await _lista_con_precios(sesion_rw, cadena_dia)
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}

    respuesta = await cliente.get(
        f"/v1/listas/{lista_id}/resumen",
        params={"cadenas": ["dia", "carrefour"]},
        headers=cabeceras,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert set(cuerpo) == {
        "coste_total",
        "por_cadena",
        "porcentaje_c",
        "coste_optimo",
        "coste_mixta_real",
        "avisos",
    }
    costes = {coste["cadena"]: coste for coste in cuerpo["por_cadena"]}
    assert costes["dia"]["coste"] == "1.00"
    assert costes["carrefour"]["coste"] == "2.00"
    assert float(costes["dia"]["porcentaje_a"]) == 0.5
    assert cuerpo["coste_total"] == "1.00"
    assert cuerpo["porcentaje_c"] == "0.0000"
    assert cuerpo["avisos"] == []


async def test_el_resumen_se_cachea(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    provider_id, lista_id, _ = await _lista_con_precios(sesion_rw, cadena_dia)
    cabeceras = {"Authorization": f"Bearer {_token(provider_id)}"}
    parametros = {"cadenas": ["dia", "carrefour"]}

    primera = await cliente.get(
        f"/v1/listas/{lista_id}/resumen", params=parametros, headers=cabeceras
    )
    segunda = await cliente.get(
        f"/v1/listas/{lista_id}/resumen", params=parametros, headers=cabeceras
    )

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert primera.json() == segunda.json()


async def test_otra_usuario_no_puede_ver_el_resumen(
    cliente: AsyncClient, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    _, lista_id, _ = await _lista_con_precios(sesion_rw, cadena_dia)

    respuesta = await cliente.get(
        f"/v1/listas/{lista_id}/resumen",
        headers={"Authorization": f"Bearer {_token(f'intruso-{uuid4().hex[:8]}')}"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "NO_AUTORIZADO"


async def test_sin_jwt_devuelve_401(cliente: AsyncClient) -> None:
    respuesta = await cliente.get(f"/v1/listas/{uuid4()}/resumen")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"
