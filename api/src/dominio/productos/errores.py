"""Errores del dominio de productos."""

from __future__ import annotations


class FormatoInvalidoError(Exception):
    """El formato no tiene una cantidad o unidad admitidas."""

    def __init__(self, valor: object) -> None:
        self.valor = valor
        super().__init__(f"Formato inválido: {valor!r}")
