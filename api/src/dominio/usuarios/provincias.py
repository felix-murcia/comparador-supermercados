"""Provincias españolas y validación de la provincia del usuario."""

from __future__ import annotations

from src.dominio.normalizacion import normalizar_texto
from src.dominio.usuarios.entidades import Provincia
from src.dominio.usuarios.errores import ProvinciaInvalidaError

PROVINCIAS: tuple[str, ...] = (
    "A Coruña",
    "Álava",
    "Albacete",
    "Alicante",
    "Almería",
    "Asturias",
    "Ávila",
    "Badajoz",
    "Baleares",
    "Barcelona",
    "Burgos",
    "Cáceres",
    "Cádiz",
    "Castellón",
    "Ciudad Real",
    "Córdoba",
    "Cuenca",
    "Gipuzkoa",
    "Girona",
    "Granada",
    "Guadalajara",
    "Huelva",
    "Huesca",
    "Jaén",
    "La Rioja",
    "Las Palmas",
    "León",
    "Lleida",
    "Lugo",
    "Madrid",
    "Málaga",
    "Murcia",
    "Navarra",
    "Ourense",
    "Palencia",
    "Palmas",
    "Pontevedra",
    "Salamanca",
    "Santa Cruz de Tenerife",
    "Segovia",
    "Sevilla",
    "Soria",
    "Tarragona",
    "Teruel",
    "Toledo",
    "Valencia",
    "Valladolid",
    "Vizcaya",
    "Zamora",
    "Zaragoza",
    "Ceuta",
    "Melilla",
)

_POR_NOMBRE_NORMALIZADO = {normalizar_texto(nombre): nombre for nombre in PROVINCIAS}


def normalizar_provincia(nombre: str) -> str:
    """Nombre canónico de la provincia; cadena vacía si no existe."""
    return _POR_NOMBRE_NORMALIZADO.get(normalizar_texto(nombre), "")


def validar_provincia(nombre: str) -> Provincia:
    """Valida la provincia contra el catálogo español.

    Lanza `ProvinciaInvalidaError` si no existe (la comparación ignora
    mayúsculas, tildes y espacios).
    """
    canonica = normalizar_provincia(nombre)
    if not canonica:
        raise ProvinciaInvalidaError(nombre)
    return Provincia(canonica)
