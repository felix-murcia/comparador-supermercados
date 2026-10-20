"""Scheduler de la ingesta diaria de precios.

Uso:
    python -m src.scheduler

Cada día a las 03:00 (Europe/Madrid) encola un job de búsqueda por cada
producto activo, espera a que el worker termine y entonces invalida la caché
de resultados para que la siguiente búsqueda use precios frescos.

Es un proceso aparte: la API no programa nada (ADR-010).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adaptadores.cache.redis_cache import get_cache
from src.adaptadores.persistencia.cola_busquedas import PostgresColaJobs
from src.adaptadores.persistencia.engines import dispose_engines, get_sessionmaker_rw
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.dominio.busquedas.entidades import BusquedaNueva
from src.dominio.busquedas.reglas import calcular_cache_key
from src.logging_config import configurar_logging
from src.puertos.cache import Cache

logger = logging.getLogger(__name__)

HORA_INGESTA = 3
MINUTO_INGESTA = 0
ZONA_HORARIA = "Europe/Madrid"
PREFIJO_CACHE = "v1:"
INTERVALO_ESPERA_SEGUNDOS = 15.0
ESPERA_MAXIMA_SEGUNDOS = 3600.0


async def encolar_ingesta(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> int:
    """Crea un job de búsqueda por cada producto activo; devuelve cuántos."""
    async with sessionmaker() as sesion:
        productos = await SQLAlchemyRepositorioProductos(sesion).listar_ingestables()
        busquedas = SQLAlchemyRepositorioBusquedas(sesion)
        for producto in productos:
            await busquedas.crear(
                BusquedaNueva(
                    query=producto.nombre,
                    cadenas=producto.cadenas,
                    cache_key=calcular_cache_key(producto.nombre, producto.cadenas),
                )
            )
        await sesion.commit()
        return len(productos)


async def esperar_cola_vacia(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    espera_maxima: float = ESPERA_MAXIMA_SEGUNDOS,
    intervalo: float = INTERVALO_ESPERA_SEGUNDOS,
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> bool:
    """Espera a que no queden jobs en curso; `False` si se agotó el tiempo."""
    limite = time.monotonic() + espera_maxima
    while time.monotonic() < limite:
        async with sessionmaker() as sesion:
            pendientes = await PostgresColaJobs(sesion).contar_pendientes()
        if pendientes == 0:
            return True
        logger.info("Ingesta en curso: %s jobs pendientes", pendientes)
        await dormir(intervalo)
    return False


async def ingesta_diaria(
    sessionmaker: async_sessionmaker[AsyncSession],
    cache: Cache,
    *,
    espera_maxima: float = ESPERA_MAXIMA_SEGUNDOS,
) -> None:
    """Encola la ingesta del día, espera a que termine e invalida la caché."""
    inicio = time.monotonic()
    logger.info("Iniciando ingesta diaria")

    encolados = await encolar_ingesta(sessionmaker)
    logger.info("Ingesta diaria: %s jobs encolados", encolados)

    completada = await esperar_cola_vacia(sessionmaker, espera_maxima=espera_maxima)
    await cache.invalidar_prefijo(PREFIJO_CACHE)

    logger.info(
        "Ingesta diaria terminada en %.1f s (cola vacía: %s)",
        time.monotonic() - inicio,
        completada,
    )


def construir_scheduler(
    sessionmaker: async_sessionmaker[AsyncSession],
    cache: Cache,
) -> AsyncIOScheduler:
    """Scheduler con la ingesta diaria programada a las 03:00 (Europe/Madrid)."""
    scheduler = AsyncIOScheduler(timezone=ZONA_HORARIA)

    async def _trabajo() -> None:
        await ingesta_diaria(sessionmaker, cache)

    scheduler.add_job(
        _trabajo,
        CronTrigger(
            hour=HORA_INGESTA,
            minute=MINUTO_INGESTA,
            timezone=ZONA_HORARIA,
        ),
        id="ingesta_diaria",
        replace_existing=True,
    )
    return scheduler


async def main() -> None:
    """Arranca el scheduler y espera hasta que se pare el proceso."""
    configurar_logging()
    sessionmaker = get_sessionmaker_rw()
    cache = get_cache()
    scheduler = construir_scheduler(sessionmaker, cache)
    scheduler.start()
    logger.info(
        "Scheduler arrancado: ingesta diaria a las %02d:%02d (%s)",
        HORA_INGESTA,
        MINUTO_INGESTA,
        ZONA_HORARIA,
    )

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        await cache.aclose()
        await dispose_engines()


if __name__ == "__main__":
    asyncio.run(main())
