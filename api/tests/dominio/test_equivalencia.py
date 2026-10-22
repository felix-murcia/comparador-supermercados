"""Tests de las reglas de equivalencia entre productos de distintas cadenas."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.dominio.productos.entidades import DescripcionProducto
from src.dominio.productos.reglas import (
    descripcion_base,
    es_equivalente,
    nombre_generico,
    similitud_base,
)


def _producto(
    nombre: str,
    marca: str | None = None,
    categoria: str | None = "lacteos",
    litros_o_kg: Decimal | None = Decimal(1),
    formato: str | None = None,
) -> DescripcionProducto:
    return DescripcionProducto(
        nombre=nombre,
        marca=marca,
        categoria=categoria,
        litros_o_kg=litros_o_kg,
        formato=formato,
    )


def test_la_descripcion_base_quita_la_marca_y_las_medidas() -> None:
    """«Leche desnatada Dia Láctea 1 L» describe leche desnatada."""
    assert (
        descripcion_base("Leche desnatada Dia Láctea 1 L", "Dia Láctea")
        == "desnatada leche"
    )
    assert (
        descripcion_base("Leche desnatada Hacendado", "Hacendado") == "desnatada leche"
    )


def test_la_descripcion_base_conserva_los_detalles_que_no_son_marca() -> None:
    """«brik» no es una marca: describe el envase, y se conserva."""
    assert (
        descripcion_base("Leche desnatada brik 1 l.", "SIMPL") == "brik desnatada leche"
    )


def test_la_similitud_ignora_los_detalles_de_envase() -> None:
    """«leche desnatada» y «leche desnatada brik» son la misma necesidad."""
    assert similitud_base("desnatada leche", "brik desnatada leche") == pytest.approx(
        2 / 3
    )


def test_la_similitud_separa_desnatada_de_semidesnatada() -> None:
    """No basta con que las cadenas se parezcan."""
    assert similitud_base("desnatada leche", "semidesnatada leche") < 0.6


def test_el_nombre_generico_no_tiene_la_marca_pero_su_el_formato() -> None:
    """El aviso nombra la necesidad, no el artículo de una marca."""
    assert (
        nombre_generico("Leche desnatada Dia Láctea 1 L", "Dia Láctea", "1L")
        == "leche desnatada 1 l"
    )
    assert (
        nombre_generico("Leche desnatada Hacendado", "Hacendado", "1L")
        == "leche desnatada 1 l"
    )


def test_un_producto_de_otra_marca_es_equivalente() -> None:
    """El equivalente de marca propia cubre la misma necesidad."""
    dia = _producto("Leche desnatada Dia Láctea 1 L", "Dia Láctea", formato="1L")
    assert es_equivalente(dia, _producto("Leche desnatada Hacendado", "Hacendado"))
    assert es_equivalente(dia, _producto("Leche desnatada brik 1 l.", "SIMPL"))
    assert es_equivalente(dia, _producto("Leche desnatada", "Puleva"))


def test_no_son_equivalentes_los_productos_distintos() -> None:
    """Ni otra leche, ni otro tamaño, ni otra categoría."""
    dia = _producto("Leche desnatada Dia Láctea 1 L", "Dia Láctea", formato="1L")

    assert not es_equivalente(dia, _producto("Leche semidesnatada 1 L", "Puleva"))
    assert not es_equivalente(dia, _producto("Leche entera 1 L", "Paseo"))
    assert not es_equivalente(
        dia, _producto("Leche desnatada 3 L", "Puleva", litros_o_kg=Decimal(3))
    )
    assert not es_equivalente(
        dia,
        _producto("Leche desnatada 1 L", "Puleva", categoria="desayuno"),
    )


def test_el_tamano_desconocido_impide_saber_si_son_equivalentes() -> None:
    """Sin tamaño no se puede afirmar que sean el mismo producto."""
    dia = _producto("Leche desnatada Dia Láctea 1 L", "Dia Láctea", formato="1L")
    assert not es_equivalente(
        dia, _producto("Leche desnatada", "Puleva", litros_o_kg=None)
    )


def test_un_nombre_vacio_no_es_equivalente() -> None:
    """Sin nombre no hay nada que comparar."""
    assert not es_equivalente(
        _producto("", "Puleva"), _producto("Leche desnatada", "Puleva")
    )
