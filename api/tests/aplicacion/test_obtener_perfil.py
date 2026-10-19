"""Tests del caso de uso `ObtenerPerfil` con un repositorio falso."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.dominio.usuarios.entidades import IdentidadOAuth, Usuario
from src.puertos.repositorios import RepositorioUsuarios


class RepositorioUsuariosFake:
    """Implementa el puerto de usuarios sin tocar la base de datos."""

    def __init__(self) -> None:
        self.identidades: list[IdentidadOAuth] = []

    async def upsert(self, identidad: IdentidadOAuth) -> Usuario:
        self.identidades.append(identidad)
        return Usuario(
            id=uuid4(),
            provider=identidad.provider,
            provider_id=identidad.provider_id,
            email=identidad.email,
            nombre=identidad.nombre,
            provincia=None,
            avatar_url=identidad.avatar_url,
            creado_en=datetime.now(UTC),
        )

    async def obtener_por_provider(
        self, provider: str, provider_id: str
    ) -> Usuario | None:
        return None


def test_el_fake_cumple_el_protocolo() -> None:
    assert isinstance(RepositorioUsuariosFake(), RepositorioUsuarios)


@pytest.mark.asyncio
async def test_obtener_perfil_delega_en_el_repositorio() -> None:
    repositorio = RepositorioUsuariosFake()
    identidad = IdentidadOAuth(
        provider="google",
        provider_id="123",
        email="ana@example.test",
        nombre="Ana",
    )

    usuario = await ObtenerPerfil(repositorio).ejecutar(identidad)

    assert repositorio.identidades == [identidad]
    assert usuario.provider == "google"
    assert usuario.provider_id == "123"
    assert usuario.email == "ana@example.test"
    assert usuario.nombre == "Ana"
