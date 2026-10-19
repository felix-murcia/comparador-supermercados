"""Errores de los adaptadores de ingesta."""

from __future__ import annotations


class ErrorClienteLLM(Exception):
    """Fallo al hablar con el proveedor de LLM.

    `transitorio` distingue los errores reintentables (5xx, red) de los
    permanentes (credenciales, modelo inexistente).
    """

    def __init__(self, motivo: str, *, transitorio: bool) -> None:
        self.motivo = motivo
        self.transitorio = transitorio
        super().__init__(motivo)
