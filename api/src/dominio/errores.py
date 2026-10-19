"""Errores de dominio compartidos por los casos de uso."""

from __future__ import annotations


class ErrorDominio(Exception):
    """Error de negocio con un código estable para la API."""


class RateLimitError(ErrorDominio):
    """Se superó el límite de peticiones en la ventana de tiempo."""

    def __init__(self, limite: int, ventana_segundos: int = 60) -> None:
        self.limite = limite
        self.ventana_segundos = ventana_segundos
        super().__init__(
            f"Se superó el límite de {limite} peticiones en {ventana_segundos} s"
        )
