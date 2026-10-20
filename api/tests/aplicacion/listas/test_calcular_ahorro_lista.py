"""Integración del caso de uso `CalcularAhorroLista` contra Postgres real."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
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
from src.aplicacion.listas.calcular_ahorro_lista import CalcularAhorroLista
from src.dominio.listas.entidades import ItemListaNuevo
from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.productos.entidades import ProductoNuevo

_URL_RW = os.getenv("DATABASE_URL_RW")

if not _URL_RW:
    pytest.skip("DATABASE_URL_RW no está configurada", allow_module_level=True)

pytestmark = pytest.mark.asyncio


async def _precio(
    sesion_rw: AsyncSession, producto_id: UUID, cadena_id: UUID, importe: str
) -> None:
    producto_cadena = await SQLAlchemyRepositorioProductosCadenas(
        sesion_rw
    ).obtener_por_producto_y_cadena(producto_id, cadena_id)
    assert producto_cadena is not None
    await SQLAlchemyRepositorioPrecios(sesion_rw).insertar(
        PrecioNuevo(
            producto_cadena_id=producto_cadena,
            importe_eur=Decimal(importe),
            url_fuente="https://ejemplo.test/producto",
            fecha_consulta=datetime.now(UTC),
        )
    )
    await sesion_rw.commit()


async def test_calcula_el_ahorro_de_la_lista(
    sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    cadenas = SQLAlchemyRepositorioCadenas(sesion_rw)
    dia = await cadenas.obtener_por_id(cadena_dia)
    assert dia is not None
    carrefour = await cadenas.obtener_por_slug("carrefour")
    if carrefour is None:
        pytest.skip("La cadena carrefour no existe en esta base de datos")

    productos = SQLAlchemyRepositorioProductos(sesion_rw)
    leche = await productos.crear(ProductoNuevo(nombre="Leche entera", marca="Pascual"))
    await sesion_rw.commit()

    mappings = SQLAlchemyRepositorioProductosCadenas(sesion_rw)
    for cadena in (dia, carrefour):
        await mappings.crear(
            producto_id=leche.id,
            cadena_id=cadena.id,
            url_producto="https://ejemplo.test/leche",
            nombre_en_cadena="Leche entera 1L",
        )
    await sesion_rw.commit()

    await _precio(sesion_rw, leche.id, dia.id, "1.00")
    await _precio(sesion_rw, leche.id, carrefour.id, "2.00")

    listas = SQLAlchemyRepositorioListas(sesion_rw)
    lista = await listas.crear(uuid4(), "Compra")
    await listas.agregar_item(
        ItemListaNuevo(
            lista_id=lista.id,
            producto_id=leche.id,
            cantidad=1,
            cadena_compra_id=dia.id,
        )
    )
    await sesion_rw.commit()

    caso = CalcularAhorroLista(
        repositorio_listas=listas,
        repositorio_precios=SQLAlchemyRepositorioPrecios(sesion_rw),
        repositorio_cadenas=cadenas,
    )

    resumen = await caso.ejecutar(lista.id, ["dia", "carrefour"])

    costes = {coste.cadena: coste for coste in resumen.por_cadena}
    assert costes["dia"].coste == Decimal("1.00")
    assert costes["carrefour"].coste == Decimal("2.00")
    assert costes["dia"].porcentaje_a == Decimal("0.5000")
    assert resumen.coste_mixta_real == Decimal("1.00")
    assert resumen.coste_optimo == Decimal("1.00")
    assert resumen.porcentaje_c == Decimal("0.0000")
