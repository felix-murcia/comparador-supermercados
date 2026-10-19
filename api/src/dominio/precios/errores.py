"""Errores del dominio de precios."""

from __future__ import annotations


class PrecioInvalidoError(Exception):
    """El importe o el precio por litro/kg no son válidos."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(f"Precio inválido: {motivo}")
