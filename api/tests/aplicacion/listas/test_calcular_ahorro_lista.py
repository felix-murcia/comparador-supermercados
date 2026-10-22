"""Integración del caso de uso `CalcularAhorroLista` contra Postgres real."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

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
    sesion_rw: AsyncSession,
    cadena_dia: UUID,
    cadena_carrefour: UUID,
    usuario: UUID,
) -> None:
    cadenas = SQLAlchemyRepositorioCadenas(sesion_rw)
    dia = await cadenas.obtener_por_id(cadena_dia)
    assert dia is not None
    carrefour = await cadenas.obtener_por_id(cadena_carrefour)
    assert carrefour is not None

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
    lista = await listas.crear(usuario, "Compra")
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


async def test_compara_con_el_equivalente_de_otra_cadena(
    sesion_rw: AsyncSession,
    cadena_dia: UUID,
    cadena_carrefour: UUID,
    usuario: UUID,
) -> None:
    """Un producto de marca propia se compara con su equivalente de la otra.

    El artículo que la persona compró en DIA no lo vende Carrefour, pero
    allí está su equivalente de marca propia. La comparación debe usar ese
    precio, no dar el producto por ausente.
    """
    cadenas = SQLAlchemyRepositorioCadenas(sesion_rw)
    dia = await cadenas.obtener_por_id(cadena_dia)
    assert dia is not None
    carrefour = await cadenas.obtener_por_id(cadena_carrefour)
    assert carrefour is not None

    productos = SQLAlchemyRepositorioProductos(sesion_rw)
    mappings = SQLAlchemyRepositorioProductosCadenas(sesion_rw)

    leche_dia = await productos.crear(
        ProductoNuevo(
            nombre="Leche desnatada Dia Láctea 1 L",
            marca="Dia Láctea",
            categoria="lacteos",
            formato="1L",
            litros_o_kg=Decimal(1),
        )
    )
    leche_carrefour = await productos.crear(
        ProductoNuevo(
            nombre="Leche desnatada brik 1 l.",
            marca="SIMPL",
            categoria="lacteos",
            formato="1L",
            litros_o_kg=Decimal(1),
        )
    )
    await sesion_rw.commit()

    await mappings.crear(
        producto_id=leche_dia.id,
        cadena_id=dia.id,
        url_producto="https://ejemplo.test/dia",
        nombre_en_cadena="Leche desnatada Dia Láctea 1 L",
    )
    await mappings.crear(
        producto_id=leche_carrefour.id,
        cadena_id=carrefour.id,
        url_producto="https://ejemplo.test/carrefour",
        nombre_en_cadena="Leche desnatada brik 1 l.",
    )
    await sesion_rw.commit()

    await _precio(sesion_rw, leche_dia.id, dia.id, "1.29")
    await _precio(sesion_rw, leche_carrefour.id, carrefour.id, "0.79")

    listas = SQLAlchemyRepositorioListas(sesion_rw)
    lista = await listas.crear(usuario, "Compra")
    await listas.agregar_item(
        ItemListaNuevo(
            lista_id=lista.id,
            producto_id=leche_dia.id,
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
    assert costes["dia"].coste == Decimal("1.29")
    assert costes["carrefour"].coste == Decimal("0.79")
    assert costes["carrefour"].productos_no_disponibles == ()
    assert resumen.coste_optimo == Decimal("0.79")
    assert any(
        "se ha comparado con" in aviso and "Leche desnatada brik 1 l." in aviso
        for aviso in resumen.avisos
    )
    assert not any("no hay precio para" in aviso for aviso in resumen.avisos)
