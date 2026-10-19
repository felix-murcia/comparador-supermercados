"""Reglas puras de búsqueda."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from src.dominio.normalizacion import normalizar_texto

PREFIJO_CACHE = "v1:"


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
    partes = [
        normalizar_texto(query),
        ",".join(sorted(normalizar_texto(cadena) for cadena in cadenas)),
        normalizar_texto(orden),
        _filtros_canonicos(filtros),
        normalizar_texto(provincia) if provincia else "",
    ]
    huella = hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()
    return f"{PREFIJO_CACHE}{huella}"
