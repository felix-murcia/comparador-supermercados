"""Entidades y value objects del dominio de usuarios."""

from __future__ import annotations

from dataclasses import dataclass

from src.dominio.usuarios.errores import ProvinciaInvalidaError


@dataclass(frozen=True)
class Provincia:
    """Provincia del usuario para resolver precios por ubicación."""

    nombre: str

    def __post_init__(self) -> None:
        limpio = self.nombre.strip()
        if not limpio:
            raise ProvinciaInvalidaError(self.nombre)
        object.__setattr__(self, "nombre", limpio)
