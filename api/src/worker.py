"""Worker de ingesta: procesa los jobs de búsqueda de la cola de Postgres.

Uso:
    python -m src.worker

El worker hace polling de la cola (`busquedas` con `FOR UPDATE SKIP LOCKED`,
ADR-007), ejecuta el pipeline de precio por cada cadena del job y actualiza
el estado y el progreso. Si el worker cae, el job vuelve a la cola pasado el
timeout y otro worker lo retoma.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adaptadores.ingesta.cliente_llm import crear_cliente_llm
from src.adaptadores.ingesta.llm_productor import LLMProductor
from src.adaptadores.ingesta.verificador_fetch import FetchVerificador
from src.adaptadores.persistencia.cola_busquedas import PostgresColaJobs
from src.adaptadores.persistencia.engines import dispose_engines, get_sessionmaker_rw
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_cadenas import (
    SQLAlchemyRepositorioCadenas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.aplicacion.ingesta.buscar_producto import BuscarProducto, ResultadoBusqueda
from src.aplicacion.ingesta.procesar_busqueda import BuscarPrecio, ProcesarBusqueda
from src.config import settings

logger = logging.getLogger(__name__)

INTERVALO_SEGUNDOS = 5.0
TIMEOUT_JOB_MINUTOS = 15

_cliente_http: httpx.AsyncClient | None = None


def _cliente() -> httpx.AsyncClient:
    """Cliente HTTP compartido por el productor y el verificador."""
    global _cliente_http
    if _cliente_http is None:
        _cliente_http = httpx.AsyncClient(timeout=settings.llm_timeout_segundos)
    return _cliente_http


def _productor() -> LLMProductor:
    cliente_llm = crear_cliente_llm(
        proveedor=settings.llm_provider,
        api_key=settings.llm_api_key.get_secret_value(),
        modelo=settings.llm_model,
        cliente_http=_cliente(),
        base_url=settings.llm_base_url or None,
    )
    return LLMProductor(cliente_llm)


def _verificador() -> FetchVerificador:
    return FetchVerificador(_cliente())


async def _buscar_con_pipeline(query: str, cadena: str) -> ResultadoBusqueda:
    """Ejecuta el pipeline de precio en una sesión de escritura propia."""
    async with get_sessionmaker_rw()() as sesion:
        caso = BuscarProducto(
            productor=_productor(),
            verificador=_verificador(),
            repositorio_cadenas=SQLAlchemyRepositorioCadenas(sesion),
            repositorio_productos=SQLAlchemyRepositorioProductos(sesion),
            repositorio_productos_cadenas=SQLAlchemyRepositorioProductosCadenas(sesion),
            repositorio_precios=SQLAlchemyRepositorioPrecios(sesion),
        )
        resultado = await caso.ejecutar(query, cadena)
        await sesion.commit()
        return resultado


async def procesar_siguiente_job(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    buscar: BuscarPrecio | None = None,
    timeout_minutos: int = TIMEOUT_JOB_MINUTOS,
) -> bool:
    """Reclama un job de la cola y lo procesa; `False` si la cola está vacía."""
    pipeline: Callable[[str, str], Awaitable[ResultadoBusqueda]] = (
        buscar or _buscar_con_pipeline
    )

    async with sessionmaker() as sesion:
        busqueda = await PostgresColaJobs(sesion).reclamar(
            timeout_minutos=timeout_minutos
        )
        if busqueda is None:
            await sesion.rollback()
            return False
        await sesion.commit()

    logger.info("Job %s encolado: %s", busqueda.id, busqueda.query)

    async with sessionmaker() as sesion:
        caso = ProcesarBusqueda(
            buscar=pipeline,
            repositorio_busquedas=SQLAlchemyRepositorioBusquedas(sesion),
        )
        estado = await caso.ejecutar(busqueda)
        await sesion.commit()

    logger.info("Job %s finalizado con estado %s", busqueda.id, estado)
    return True


async def _cerrar() -> None:
    global _cliente_http
    if _cliente_http is not None:
        await _cliente_http.aclose()
        _cliente_http = None
    await dispose_engines()


async def main() -> None:
    """Bucle del worker: reclama y procesa jobs hasta que se pare."""
    logger.info("Worker de ingesta arrancado")
    sessionmaker = get_sessionmaker_rw()
    try:
        while True:
            if not await procesar_siguiente_job(sessionmaker):
                await asyncio.sleep(INTERVALO_SEGUNDOS)
    finally:
        await _cerrar()


if __name__ == "__main__":
    asyncio.run(main())
