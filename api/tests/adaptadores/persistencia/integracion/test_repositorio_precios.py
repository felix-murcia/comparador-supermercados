from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.modelos import PrecioModelo
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.precios.estados import EstadoPrecio

pytestmark = pytest.mark.asyncio

AHORA = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


def _precio(
    producto_cadena_id: UUID,
    *,
    importe: str = "1.29",
    fecha: datetime = AHORA,
    estado: EstadoPrecio = "verificado",
) -> PrecioNuevo:
    return PrecioNuevo(
        producto_cadena_id=producto_cadena_id,
        importe_eur=Decimal(importe),
        url_fuente="https://dia.test/leche-entera",
        fecha_consulta=fecha,
        estado=estado,
        por_litro_kg=Decimal("1.2900"),
        disponible=True,
    )


async def test_insertar_precio_verificado(
    sesion_rw: AsyncSession, producto_cadena_base: UUID
) -> None:
    repositorio = SQLAlchemyRepositorioPrecios(sesion_rw)

    registrado = await repositorio.insertar(_precio(producto_cadena_base))

    assert registrado.estado == "verificado"
    assert registrado.ambito == "nacional"
    assert registrado.por_litro_kg == Decimal("1.2900")
    assert await repositorio.ultimo_verificado(producto_cadena_base) == registrado
    assert await repositorio.ultimo_verificado(uuid4()) is None


async def test_ultimo_verificado_ignora_estados_no_verificados(
    sesion_rw: AsyncSession, producto_cadena_base: UUID
) -> None:
    repositorio = SQLAlchemyRepositorioPrecios(sesion_rw)
    verificado = await repositorio.insertar(_precio(producto_cadena_base))
    await repositorio.insertar(
        _precio(
            producto_cadena_base,
            estado="sospechoso",
            fecha=AHORA + timedelta(hours=1),
        )
    )

    ultimo = await repositorio.ultimo_verificado(producto_cadena_base)

    assert ultimo is not None
    assert ultimo.id == verificado.id


async def test_historico_devuelve_mas_reciente_primero(
    sesion_rw: AsyncSession, producto_cadena_base: UUID
) -> None:
    repositorio = SQLAlchemyRepositorioPrecios(sesion_rw)
    antiguo = await repositorio.insertar(_precio(producto_cadena_base, importe="1.19"))
    reciente = await repositorio.insertar(
        _precio(
            producto_cadena_base,
            importe="1.39",
            fecha=AHORA + timedelta(days=1),
        )
    )

    historico = await repositorio.historico(producto_cadena_base)
    vacio = await repositorio.historico(uuid4())

    assert [precio.id for precio in historico] == [reciente.id, antiguo.id]
    assert vacio == []


async def test_precios_solo_admiten_insert(
    sesion_rw: AsyncSession, producto_cadena_base: UUID
) -> None:
    repositorio = SQLAlchemyRepositorioPrecios(sesion_rw)
    registrado = await repositorio.insertar(_precio(producto_cadena_base))

    with pytest.raises(DBAPIError):
        await sesion_rw.execute(
            update(PrecioModelo)
            .where(PrecioModelo.id == registrado.id)
            .values(precio_eur=Decimal("9.99"))
        )

    await sesion_rw.rollback()
