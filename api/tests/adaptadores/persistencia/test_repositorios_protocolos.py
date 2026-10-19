from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.puertos.repositorios import (
    RepositorioBusquedas,
    RepositorioListas,
    RepositorioPrecios,
    RepositorioProductos,
)


def test_los_adaptadores_cumplen_los_protocolos() -> None:
    sesion = cast(AsyncSession, object())

    assert isinstance(SQLAlchemyRepositorioProductos(sesion), RepositorioProductos)
    assert isinstance(SQLAlchemyRepositorioPrecios(sesion), RepositorioPrecios)
    assert isinstance(SQLAlchemyRepositorioListas(sesion), RepositorioListas)
    assert isinstance(SQLAlchemyRepositorioBusquedas(sesion), RepositorioBusquedas)
