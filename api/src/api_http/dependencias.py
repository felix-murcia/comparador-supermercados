"""Dependencias HTTP de sesiones y routing RW/RO.

El middleware/dependencia de autenticación (T1.x) debe poblar
`request.state.usuario_id` para que el sticky post-escritura funcione.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.engines import (
    get_sessionmaker_ro,
    get_sessionmaker_rw,
)
from src.adaptadores.persistencia.sticky import get_sticky_reads

logger = logging.getLogger(__name__)

_METODOS_ESCRITURA = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_usuario_id(request: Request) -> str | None:
    """Usuario autenticado en esta petición, si lo hay."""
    usuario_id = getattr(request.state, "usuario_id", None)
    return str(usuario_id) if usuario_id is not None else None


async def _sticky_activo(usuario_id: str) -> bool:
    try:
        return await get_sticky_reads().activo(usuario_id)
    except Exception as exc:  # noqa: BLE001 - Redis no debe tumbar lecturas
        logger.warning("Sticky read check failed: %s", type(exc).__name__)
        return False


async def _debe_usar_rw(request: Request) -> bool:
    usuario_id = get_usuario_id(request)
    if usuario_id is None:
        return False
    return await _sticky_activo(usuario_id)


async def _marcar_sticky(usuario_id: str) -> None:
    try:
        await get_sticky_reads().marcar(usuario_id)
    except Exception as exc:  # noqa: BLE001 - la escritura ya se confirmó
        logger.warning("Sticky read mark failed: %s", type(exc).__name__)


async def get_session_ro(request: Request) -> AsyncIterator[AsyncSession]:
    """Sesión de lectura; usa RW si el usuario tiene sticky activo."""
    sessionmaker = get_sessionmaker_ro
    if await _debe_usar_rw(request):
        sessionmaker = get_sessionmaker_rw

    async with sessionmaker()() as session:
        yield session


async def get_session_rw(request: Request) -> AsyncIterator[AsyncSession]:
    """Sesión de escritura; confirma al terminar y marca el sticky."""
    usuario_id = get_usuario_id(request)

    async with get_sessionmaker_rw()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    if usuario_id is not None and request.method in _METODOS_ESCRITURA:
        await _marcar_sticky(usuario_id)


SessionRO = Annotated[AsyncSession, Depends(get_session_ro)]
SessionRW = Annotated[AsyncSession, Depends(get_session_rw)]
