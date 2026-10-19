from decimal import Decimal

from src.dominio.precios.reglas import calcular_precio_por_litro


def test_calcular_precio_por_litro_redondea_a_4_decimales() -> None:
    assert calcular_precio_por_litro(Decimal(10), Decimal(3)) == Decimal("3.3333")


def test_calcular_precio_por_litro_con_litros_cero_devuelve_none() -> None:
    assert calcular_precio_por_litro(Decimal("4.45"), Decimal(0)) is None


def test_calcular_precio_por_litro_con_litros_negativos_devuelve_none() -> None:
    assert calcular_precio_por_litro(Decimal("4.45"), Decimal(-1)) is None
