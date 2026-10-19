"""Errores del dominio de precios."""

from __future__ import annotations


class PrecioInvalidoError(Exception):
    """El importe o el precio por litro/kg no son válidos."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(f"Precio inválido: {motivo}")


class ErrorProductor(Exception):
    """El productor no pudo devolver un candidato válido.

    `reintentable` indica si tiene sentido reintentar la pasada completa
    (por ejemplo, tras agotar los reintentos por error transitorio).
    """

    def __init__(self, motivo: str, *, reintentable: bool = False) -> None:
        self.motivo = motivo
        self.reintentable = reintentable
        super().__init__(f"Error del productor: {motivo}")
