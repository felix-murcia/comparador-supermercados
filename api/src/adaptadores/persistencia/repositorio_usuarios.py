"""Implementación SQLAlchemy de `RepositorioUsuarios`."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import usuario_desde_modelo
from src.adaptadores.persistencia.modelos import UsuarioModelo
from src.dominio.usuarios.entidades import IdentidadOAuth, Usuario


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
