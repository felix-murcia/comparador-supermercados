"""Caso de uso: perfil del usuario autenticado."""

from __future__ import annotations

from src.dominio.usuarios.entidades import IdentidadOAuth, Usuario
from src.puertos.repositorios import RepositorioUsuarios


class ObtenerPerfil:
    """Devuelve el perfil; el primer login crea la fila (upsert por proveedor)."""

    def __init__(self, repositorio: RepositorioUsuarios) -> None:
        self._repositorio = repositorio

    async def ejecutar(self, identidad: IdentidadOAuth) -> Usuario:
        return await self._repositorio.upsert(identidad)
