"""Entidades y value objects del dominio de usuarios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

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


@dataclass(frozen=True)
class IdentidadOAuth:
    """Identidad verificada del proveedor OAuth (claims del token, ADR-012)."""

    provider: str
    provider_id: str
    email: str
    nombre: str | None = None
    avatar_url: str | None = None


@dataclass(frozen=True)
class Usuario:
    """Perfil persistido; el id interno es el que referencian listas y búsquedas."""

    id: UUID
    provider: str
    provider_id: str
    email: str
    nombre: str | None
    provincia: str | None
    avatar_url: str | None
    creado_en: datetime
