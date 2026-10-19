import pytest

from src.dominio.usuarios.entidades import Provincia
from src.dominio.usuarios.errores import ProvinciaInvalidaError


def test_provincia_recorta_espacios_alrededor() -> None:
    assert Provincia("  Madrid  ").nombre == "Madrid"


def test_provincia_conserva_el_nombre_limpio() -> None:
    assert Provincia("A Coruña").nombre == "A Coruña"


def test_provincia_vacia_lanza_error() -> None:
    with pytest.raises(ProvinciaInvalidaError, match="Provincia inválida"):
        Provincia("   ")
