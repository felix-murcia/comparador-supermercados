"""Reglas puras de búsqueda."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from src.dominio.normalizacion import normalizar_texto

PREFIJO_CACHE = "v1:"
PREFIJO_CACHE_COMPARACION = "v1:cmp:"


def _filtros_canonicos(filtros: Mapping[str, object] | None) -> str:
    """Serializa los filtros ordenados por clave, ignorando los vacíos."""
    if not filtros:
        return ""

    partes: list[str] = []
    for clave in sorted(filtros):
        valor = filtros[clave]
        if valor is None or valor == "":
            continue
        partes.append(f"{normalizar_texto(clave)}={normalizar_texto(str(valor))}")
    return "&".join(partes)


def _clave(
    prefijo: str,
    query: str,
    cadenas: Sequence[str],
    orden: str,
    filtros: Mapping[str, object] | None,
    provincia: str | None,
) -> str:
    partes = [
        normalizar_texto(query),
        ",".join(sorted(normalizar_texto(cadena) for cadena in cadenas)),
        normalizar_texto(orden),
        _filtros_canonicos(filtros),
        normalizar_texto(provincia) if provincia else "",
    ]
    huella = hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()
    return f"{prefijo}{huella}"


def calcular_cache_key(
    query: str,
    cadenas: Sequence[str],
    orden: str = "",
    filtros: Mapping[str, object] | None = None,
    provincia: str | None = None,
) -> str:
    """Clave de caché: prefijo de versión + SHA-256 de la búsqueda normalizada.

    Dos búsquedas equivalentes (mismo producto escrito de otra forma, mismo
    conjunto de cadenas en distinto orden) producen la misma clave; cualquier
    diferencia relevante (provincia, orden, filtros) produce otra.
    """
    return _clave(PREFIJO_CACHE, query, cadenas, orden, filtros, provincia)


def calcular_cache_key_comparacion(
    query: str,
    cadenas: Sequence[str],
    orden: str = "",
    filtros: Mapping[str, object] | None = None,
    provincia: str | None = None,
) -> str:
    """Clave de caché de la comparativa.

    Usa un prefijo propio (`v1:cmp:`) para no chocar con la clave de la
    búsqueda, pero sigue bajo la versión `v1:`: así la invalidación tras la
    ingesta (`v1:`) limpia también las comparativas.
    """
    return _clave(PREFIJO_CACHE_COMPARACION, query, cadenas, orden, filtros, provincia)
