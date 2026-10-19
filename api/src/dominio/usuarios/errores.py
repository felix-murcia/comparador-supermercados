"""Errores del dominio de usuarios."""

from __future__ import annotations


class ProvinciaInvalidaError(Exception):
    """La provincia está vacía o no es válida."""

    def __init__(self, valor: object) -> None:
        self.valor = valor
        super().__init__(f"Provincia inválida: {valor!r}")


class UsuarioNoAutorizadoError(Exception):
    """El usuario no tiene permiso para la operación solicitada."""

    def __init__(self, motivo: str = "operación no permitida") -> None:
        self.motivo = motivo
        super().__init__(motivo)
