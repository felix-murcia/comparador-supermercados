"""Normalización de texto compartida por el dominio."""

from __future__ import annotations

import unicodedata


def normalizar_texto(texto: str) -> str:
    """Minúsculas, sin tildes y sin espacios repetidos."""
    sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(caracter)
    )
    return " ".join(sin_acentos.split())
