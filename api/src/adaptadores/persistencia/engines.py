"""Engines SQLAlchemy para el primario (RW) y la réplica (RO).

Los engines se crean de forma perezosa para que importar la aplicación no
requiera que las variables de entorno estén completas. La readiness sigue
siendo la responsable de reportar dependencias ausentes.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

logger = logging.getLogger(__name__)

_POOL_RECYCLE_SEGUNDOS = 1800


def _crear_engine(url: SecretStr, nombre_variable: str) -> AsyncEngine:
    valor = url.get_secret_value()
    if not valor:
        raise RuntimeError(f"{nombre_variable} no está configurada")

    return create_async_engine(
        valor,
        pool_pre_ping=True,
        pool_recycle=_POOL_RECYCLE_SEGUNDOS,
    )


@lru_cache(maxsize=1)
def get_engine_rw() -> AsyncEngine:
    """Engine del primario; solo para escrituras y migraciones."""
    return _crear_engine(settings.database_url_rw, "DATABASE_URL_RW")


@lru_cache(maxsize=1)
def get_engine_ro() -> AsyncEngine:
    """Engine de la réplica; para lecturas de la API pública."""
    return _crear_engine(settings.database_url_ro, "DATABASE_URL_RO")


@lru_cache(maxsize=1)
def get_sessionmaker_rw() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine_rw(),
        expire_on_commit=False,
        autoflush=False,
    )


@lru_cache(maxsize=1)
def get_sessionmaker_ro() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine_ro(),
        expire_on_commit=False,
        autoflush=False,
    )


def _reset_engines_for_tests() -> None:
    """Limpia las cachés sin tocar conexiones; solo para tests unitarios."""
    get_sessionmaker_ro.cache_clear()
    get_sessionmaker_rw.cache_clear()
    get_engine_ro.cache_clear()
    get_engine_rw.cache_clear()


async def dispose_engines() -> None:
    """Cierra los pools creados durante la vida del proceso."""
    get_sessionmaker_ro.cache_clear()
    get_sessionmaker_rw.cache_clear()

    for get_engine in (get_engine_ro, get_engine_rw):
        if not get_engine.cache_info().currsize:
            continue
        engine = get_engine()
        try:
            await engine.dispose()
        except Exception as exc:  # noqa: BLE001 - cierre best-effort
            logger.warning("Engine dispose failed: %s", type(exc).__name__)
        finally:
            get_engine.cache_clear()
