"""Tests del catálogo y la validación de provincias."""

from __future__ import annotations

import pytest

from src.dominio.usuarios.errores import ProvinciaInvalidaError
from src.dominio.usuarios.provincias import (
    PROVINCIAS,
    normalizar_provincia,
    validar_provincia,
)


def test_el_catalogo_tiene_las_52_provincias() -> None:
    assert len(PROVINCIAS) == 52
    assert "Madrid" in PROVINCIAS
    assert "Ceuta" in PROVINCIAS
    assert "Melilla" in PROVINCIAS


def test_normaliza_mayusculas_tildes_y_espacios() -> None:
    assert normalizar_provincia("madrid") == "Madrid"
    assert normalizar_provincia("A CORUÑA") == "A Coruña"
    assert normalizar_provincia("  valencia ") == "Valencia"


def test_normaliza_una_provincia_desconocida() -> None:
    assert normalizar_provincia("Atlántida") == ""


def test_valida_una_provincia_correcta() -> None:
    provincia = validar_provincia("a coruña")

    assert provincia.nombre == "A Coruña"


def test_rechaza_una_provincia_inexistente() -> None:
    with pytest.raises(ProvinciaInvalidaError):
        validar_provincia("Atlántida")


def test_rechaza_una_provincia_vacia() -> None:
    with pytest.raises(ProvinciaInvalidaError):
        validar_provincia("   ")
