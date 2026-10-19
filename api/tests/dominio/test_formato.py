from decimal import Decimal

import pytest

from src.dominio.productos.entidades import Formato
from src.dominio.productos.errores import FormatoInvalidoError


def test_formato_en_litros_devuelve_la_misma_cantidad() -> None:
    assert Formato(Decimal("1.5"), "L").a_litros_o_kg() == Decimal("1.5")


def test_formato_en_kg_devuelve_la_misma_cantidad() -> None:
    assert Formato(Decimal(2), "kg").a_litros_o_kg() == Decimal(2)


def test_formato_en_ml_convierte_a_litros() -> None:
    assert Formato(Decimal(750), "ml").a_litros_o_kg() == Decimal("0.75")


def test_formato_en_g_convierte_a_kg() -> None:
    assert Formato(Decimal(500), "g").a_litros_o_kg() == Decimal("0.5")


def test_formato_con_unidad_desconocida_lanza_error() -> None:
    with pytest.raises(FormatoInvalidoError, match="Formato inválido"):
        Formato(Decimal(1), "litros")


def test_formato_con_cantidad_negativa_lanza_error() -> None:
    with pytest.raises(FormatoInvalidoError):
        Formato(Decimal(-1), "L")
