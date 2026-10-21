"""Tests de las reglas de formato y normalización de producto."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.dominio.productos.reglas import (
    familia_unidad,
    normalizar_nombre,
    parsear_formato,
)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Leche entera Pascual 1L", "leche entera pascual 1l"),
        ("Leche entera Pascual 1 L", "leche entera pascual 1l"),
        ("Leche Entera Pascual 1  L", "leche entera pascual 1l"),
        ("Yogur natural pack 4 uds", "yogur natural pack 4uds"),
        ("Aceite de oliva 1 L", "aceite de oliva 1l"),
        ("Harina de trigo 500 g", "harina de trigo 500g"),
        ("4x125 g", "4x125g"),
        ("4 x 125 g", "4x125g"),
    ],
)
def test_normalizar_nombre_unifica_la_forma_de_la_unidad(
    texto: str, esperado: str
) -> None:
    """La unidad se escribe con y sin espacio: es el mismo producto.

    Sin esta normalización, la ingesta creaba dos productos distintos para
    "Leche entera Pascual 1L" y "Leche entera Pascual 1 L", y el precio
    acababa solo en uno de ellos.
    """
    assert normalizar_nombre(texto) == esperado


def test_normalizar_nombre_no_toca_el_texto_sin_unidades() -> None:
    assert normalizar_nombre("Leche Desnatada") == "leche desnatada"


def test_normalizar_nombre_no_confunde_unidades_distintas() -> None:
    assert normalizar_nombre("Leche 1 L") != normalizar_nombre("Leche 1 kg")


@pytest.mark.parametrize(
    ("texto", "litros", "unidad"),
    [
        ("1L", Decimal(1), "L"),
        ("1 L", Decimal(1), "L"),
        ("500 g", Decimal(500), "g"),
        ("1,5 L", Decimal("1.5"), "L"),
        ("750ml", Decimal(750), "ml"),
    ],
)
def test_parsear_formato(texto: str, litros: Decimal, unidad: str) -> None:
    formato = parsear_formato(texto)
    assert formato is not None
    assert formato.litros_o_kg == litros
    assert formato.unidad == unidad


def test_familia_unidad() -> None:
    assert familia_unidad("L") == "l"
    assert familia_unidad("ml") == "l"
    assert familia_unidad("kg") == "kg"
    assert familia_unidad("g") == "kg"


@pytest.mark.asyncio
async def test_normalizar_nombre_coincide_con_sql(sesion_rw: AsyncSession) -> None:
    """La normalización de SQL y la del dominio deben dar lo mismo.

    La búsqueda por texto completo normaliza en la base de datos (función
    `nombre_buscable_normalizado`) y la ingesta normaliza en Python
    (`normalizar_nombre`). Si divergen, el producto se crea duplicado o la
    búsqueda no lo encuentra.
    """
    casos = [
        "Leche entera Pascual 1L",
        "Leche entera Pascual 1 L",
        "Aceite de oliva virgen extra",
        "Yogur natural pack de 4 uds",
        "4x125 g",
        "4 x 125 g",
        "Leche Dia Láctea 1 L",
    ]

    for caso in casos:
        en_sql = await sesion_rw.scalar(
            text("SELECT nombre_buscable_normalizado(:nombre)"), {"nombre": caso}
        )
        assert en_sql == normalizar_nombre(caso), caso
