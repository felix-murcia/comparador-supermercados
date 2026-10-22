"""Tests del cálculo de ahorro de una lista (A + C, `ADR-008`)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.dominio.listas.ahorro import (
    Equivalente,
    ItemConPrecios,
    calcular_ahorro,
)


def _item(
    nombre: str,
    precios: dict[str, str],
    cantidad: int = 1,
    cadena_compra: str | None = None,
    precio_compra: str | None = None,
    nombre_base: str | None = None,
    equivalentes: dict[str, Equivalente] | None = None,
) -> ItemConPrecios:
    return ItemConPrecios(
        producto_id=uuid4(),
        nombre=nombre,
        cantidad=cantidad,
        precios={cadena: Decimal(precio) for cadena, precio in precios.items()},
        cadena_compra=cadena_compra,
        precio_compra=Decimal(precio_compra) if precio_compra else None,
        nombre_base=nombre_base or nombre,
        equivalentes=equivalentes or {},
    )


def test_calcula_el_porcentaje_a_entre_cadenas() -> None:
    items = [
        _item(
            "Leche",
            {"dia": "1.00", "carrefour": "2.00"},
            cadena_compra="dia",
            precio_compra="1.00",
        ),
        _item(
            "Pan",
            {"dia": "1.00", "carrefour": "2.00"},
            cadena_compra="dia",
            precio_compra="1.00",
        ),
    ]

    resumen = calcular_ahorro(items, ["dia", "carrefour"])

    assert resumen.coste_total == Decimal("2.00")
    costes = {coste.cadena: coste for coste in resumen.por_cadena}
    assert costes["dia"].coste == Decimal("2.00")
    assert costes["carrefour"].coste == Decimal("4.00")
    assert costes["dia"].porcentaje_a == Decimal("0.5000")
    assert costes["carrefour"].porcentaje_a == Decimal("0.0000")


def test_calcula_el_porcentaje_c_entre_la_cesta_mixta_y_la_optima() -> None:
    items = [
        _item(
            "Leche",
            {"dia": "1.00", "carrefour": "2.00"},
            cadena_compra="carrefour",
            precio_compra="2.00",
        ),
    ]

    resumen = calcular_ahorro(items, ["dia", "carrefour"])

    assert resumen.coste_optimo == Decimal("1.00")
    assert resumen.coste_mixta_real == Decimal("2.00")
    assert resumen.porcentaje_c == Decimal("0.5000")


def test_excluye_los_productos_no_disponibles_en_una_cadena() -> None:
    items = [
        _item("Leche", {"dia": "1.00", "carrefour": "2.00"}),
        _item("Aguacate", {"carrefour": "3.00"}),
    ]

    resumen = calcular_ahorro(items, ["dia", "carrefour"])

    costes = {coste.cadena: coste for coste in resumen.por_cadena}
    assert costes["dia"].coste == Decimal("1.00")
    assert costes["dia"].productos_no_disponibles == ("Aguacate",)
    assert costes["carrefour"].coste == Decimal("5.00")
    assert any("Aguacate" in aviso for aviso in resumen.avisos)


def test_excluye_los_productos_que_no_estan_en_ninguna_cadena() -> None:
    items = [
        _item("Leche", {"dia": "1.00"}),
        _item("Producto fantasma", {}),
    ]

    resumen = calcular_ahorro(items, ["dia", "carrefour"])

    assert resumen.coste_total == Decimal("0.00")
    assert any("fantasma" in aviso for aviso in resumen.avisos)
    assert resumen.porcentaje_c is None


def test_con_una_sola_cadena_el_porcentaje_a_no_aplica() -> None:
    items = [_item("Leche", {"dia": "1.00"}, cadena_compra="dia", precio_compra="1.00")]

    resumen = calcular_ahorro(items, ["dia"])

    assert resumen.por_cadena[0].porcentaje_a is None
    assert resumen.porcentaje_c == Decimal("0.0000")


def test_con_coste_mixta_real_cero_el_porcentaje_c_no_aplica() -> None:
    items = [_item("Leche", {"dia": "1.00"})]

    resumen = calcular_ahorro(items, ["dia", "carrefour"])

    assert resumen.coste_mixta_real == Decimal("0.00")
    assert resumen.porcentaje_c is None


def test_una_lista_vacia_da_costes_a_cero() -> None:
    resumen = calcular_ahorro([], ["dia", "carrefour"])

    assert resumen.coste_total == Decimal("0.00")
    assert resumen.coste_optimo == Decimal("0.00")
    assert resumen.coste_mixta_real == Decimal("0.00")
    assert resumen.porcentaje_c is None
    assert all(coste.porcentaje_a is None for coste in resumen.por_cadena)
    assert resumen.avisos == ()


def test_el_precio_de_compra_prevalece_sobre_el_actual() -> None:
    """Si el producto ya no está en la cadena de compra, se usa el precio actual."""
    items = [
        _item(
            "Leche",
            {"dia": "1.00"},
            cadena_compra="dia",
            precio_compra=None,
        )
    ]

    resumen = calcular_ahorro(items, ["dia"])

    assert resumen.coste_mixta_real == Decimal("1.00")


@pytest.mark.parametrize("cantidad", [1, 3])
def test_la_cantidad_multiplica_el_coste(cantidad: int) -> None:
    items = [
        _item(
            "Leche",
            {"dia": "1.00"},
            cantidad=cantidad,
            cadena_compra="dia",
            precio_compra="1.00",
        )
    ]

    resumen = calcular_ahorro(items, ["dia"])

    assert resumen.coste_total == Decimal(cantidad)


def test_compara_con_el_equivalente_cuando_el_producto_no_esta_en_la_cadena() -> None:
    """El artículo de DIA no está en Carrefour, pero su equivalente sí.

    Sin equivalente, la comparación entre cadenas no significaría nada: se
    compararía el precio de un producto con la ausencia de precio.
    """
    item = _item(
        "Leche desnatada Dia Láctea 1 L",
        {"dia": "1.29"},
        cadena_compra="dia",
        nombre_base="leche desnatada 1 l",
        equivalentes={
            "carrefour": Equivalente(
                nombre="Leche desnatada brik 1 l.",
                precio=Decimal("0.79"),
                marca="SIMPL",
            )
        },
    )

    resumen = calcular_ahorro([item], ["dia", "carrefour"])

    costes = {coste.cadena: coste for coste in resumen.por_cadena}
    assert costes["dia"].coste == Decimal("1.29")
    assert costes["carrefour"].coste == Decimal("0.79")
    assert costes["carrefour"].productos_no_disponibles == ()
    # El óptimo ahora es el equivalente más barato.
    assert resumen.coste_optimo == Decimal("0.79")
    # Y el aviso dice con qué se ha comparado.
    assert resumen.avisos == (
        (
            "En «carrefour», «leche desnatada 1 l» se ha comparado con "
            "«Leche desnatada brik 1 l.» (SIMPL)"
        ),
    )


def test_sin_equivalente_el_aviso_usa_el_nombre_sin_marca() -> None:
    """Cuando no hay equivalente, el aviso nombra la necesidad de compra."""
    item = _item(
        "Leche desnatada Dia Láctea 1 L",
        {"dia": "1.29"},
        nombre_base="leche desnatada 1 l",
    )

    resumen = calcular_ahorro([item], ["dia", "carrefour"])

    assert resumen.avisos == ("En «carrefour» no hay precio para: leche desnatada 1 l",)
    costes = {coste.cadena: coste for coste in resumen.por_cadena}
    assert costes["carrefour"].coste == Decimal(0)


def test_el_equivalente_no_sustituye_al_producto_exacto() -> None:
    """Si el producto está en la cadena, manda su precio exacto."""
    item = _item(
        "Leche desnatada",
        {"dia": "1.00", "carrefour": "1.20"},
        equivalentes={
            "carrefour": Equivalente(
                nombre="Leche desnatada Puleva", precio=Decimal("0.70"), marca="Puleva"
            )
        },
    )

    resumen = calcular_ahorro([item], ["dia", "carrefour"])

    costes = {coste.cadena: coste for coste in resumen.por_cadena}
    assert costes["carrefour"].coste == Decimal("1.20")
