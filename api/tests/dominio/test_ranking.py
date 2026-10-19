"""Tests del ranking de resultados de comparación."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from src.dominio.precios.entidades import ResultadoComparacion
from src.dominio.precios.ranking import (
    ordenar_resultados,
    posicionar,
)


def _resultado(
    nombre: str,
    precio: str,
    por_litro: str | None = None,
    cadena: str = "dia",
) -> ResultadoComparacion:
    return ResultadoComparacion(
        producto_id=uuid4(),
        producto_cadena_id=uuid4(),
        nombre=nombre,
        cadena=cadena,
        precio_eur=Decimal(precio),
        precio_por_litro_kg=Decimal(por_litro) if por_litro else None,
    )


def test_ordena_por_precio_unitario() -> None:
    resultados = [
        _resultado("Leche", "1.50", "1.50"),
        _resultado("Agua", "0.50", "0.50"),
        _resultado("Pan", "1.00", "2.00"),
    ]

    ordenados = ordenar_resultados(resultados, "precio_unitario")

    assert [r.nombre for r in ordenados] == ["Agua", "Pan", "Leche"]


def test_ordena_por_precio_por_kilo_o_litro() -> None:
    resultados = [
        _resultado("Leche", "1.50", "1.50"),
        _resultado("Pan", "1.00", "2.00"),
    ]

    ordenados = ordenar_resultados(resultados, "precio_kg_l")

    assert [r.nombre for r in ordenados] == ["Leche", "Pan"]


def test_los_sin_precio_por_unidad_van_al_final() -> None:
    resultados = [
        _resultado("Desconocido", "1.00", None),
        _resultado("Leche", "1.50", "1.50"),
    ]

    ordenados = ordenar_resultados(resultados, "precio_kg_l")

    assert [r.nombre for r in ordenados] == ["Leche", "Desconocido"]


def test_el_desempate_es_por_nombre_y_cadena() -> None:
    resultados = [
        _resultado("Zanahoria", "1.00", "1.00", cadena="dia"),
        _resultado("Apio", "1.00", "1.00", cadena="carrefour"),
        _resultado("Apio", "1.00", "1.00", cadena="dia"),
    ]

    ordenados = ordenar_resultados(resultados, "precio_unitario")

    assert [(r.nombre, r.cadena) for r in ordenados] == [
        ("Apio", "carrefour"),
        ("Apio", "dia"),
        ("Zanahoria", "dia"),
    ]


def test_relevancia_respeta_el_orden_recibido() -> None:
    resultados = [
        _resultado("Leche", "1.50"),
        _resultado("Agua", "0.50"),
    ]

    ordenados = ordenar_resultados(resultados, "relevancia")

    assert [r.nombre for r in ordenados] == ["Leche", "Agua"]


def test_las_posiciones_siguen_al_desplazamiento() -> None:
    resultados = [
        _resultado("Leche", "1.50"),
        _resultado("Agua", "0.50"),
    ]

    posicionados = posicionar(resultados, "precio_unitario", offset=10)

    assert [(r.nombre, r.posicion) for r in posicionados] == [
        ("Agua", 11),
        ("Leche", 12),
    ]


def test_un_precio_cero_no_rompe_el_ranking() -> None:
    resultados = [_resultado("Gratis", "0.00"), _resultado("Leche", "1.50")]

    posicionados = posicionar(resultados)

    assert [r.nombre for r in posicionados] == ["Gratis", "Leche"]
    assert posicionados[0].posicion == 1
