"""Implementación SQLAlchemy de `RepositorioUsuarios`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import usuario_desde_modelo
from src.adaptadores.persistencia.modelos import UsuarioModelo
from src.dominio.usuarios.entidades import IdentidadOAuth, Usuario
from src.dominio.usuarios.errores import UsuarioNoEncontradoError


class SQLAlchemyRepositorioUsuarios:
    """Upsert por (provider, provider_id); requiere sesión RW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, identidad: IdentidadOAuth) -> Usuario:
        stmt = (
            insert(UsuarioModelo)
            .values(
                provider=identidad.provider,
                provider_id=identidad.provider_id,
                email=identidad.email,
                nombre=identidad.nombre,
                avatar_url=identidad.avatar_url,
            )
            .on_conflict_do_update(
                index_elements=["provider", "provider_id"],
                set_={
                    "email": identidad.email,
                    "nombre": identidad.nombre,
                    "avatar_url": identidad.avatar_url,
                },
            )
            .returning(UsuarioModelo)
            .execution_options(populate_existing=True)
        )
        modelo = (await self._session.scalars(stmt)).one()
        return usuario_desde_modelo(modelo)

    async def obtener_por_provider(
        self, provider: str, provider_id: str
    ) -> Usuario | None:
        modelo = await self._session.scalar(
            select(UsuarioModelo)
            .where(
                UsuarioModelo.provider == provider,
                UsuarioModelo.provider_id == provider_id,
            )
            .limit(1)
        )
        if modelo is None:
            return None
        return usuario_desde_modelo(modelo)

    async def actualizar(
        self, usuario_id: UUID, nombre: str | None, provincia: str | None
    ) -> Usuario:
        modelo = await self._session.get(UsuarioModelo, usuario_id)
        if modelo is None:
            raise UsuarioNoEncontradoError(usuario_id)
        if nombre is not None:
            modelo.nombre = nombre
        if provincia is not None:
            modelo.provincia = provincia
        await self._session.flush()
        await self._session.refresh(modelo)
        return usuario_desde_modelo(modelo)
