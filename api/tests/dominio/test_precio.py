from decimal import Decimal

import pytest

from src.dominio.precios.entidades import Precio
from src.dominio.precios.errores import PrecioInvalidoError


def test_precio_conserva_importe_y_por_litro() -> None:
    precio = Precio(Decimal("1.29"), Decimal("1.2900"))

    assert (precio.importe_eur, precio.por_litro_kg) == (
        Decimal("1.29"),
        Decimal("1.2900"),
    )


def test_precio_sin_por_litro_kg_es_valido() -> None:
    assert Precio(Decimal("1.29")).por_litro_kg is None


def test_precio_con_importe_negativo_lanza_error() -> None:
    with pytest.raises(PrecioInvalidoError, match="importe_eur"):
        Precio(Decimal("-0.01"))


def test_precio_con_por_litro_negativo_lanza_error() -> None:
    with pytest.raises(PrecioInvalidoError, match="por_litro_kg"):
        Precio(Decimal("1.29"), Decimal(-1))
