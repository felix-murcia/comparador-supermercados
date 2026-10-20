import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.adaptadores.cache.redis_limitador import dispose_limitador
from src.adaptadores.persistencia.engines import dispose_engines
from src.adaptadores.persistencia.sticky import dispose_sticky_reads
from src.api_http.errores import (
    ErrorAPI,
    manejador_error_api,
    manejador_error_inesperado,
    manejador_no_autorizado,
    manejador_producto_no_encontrado,
    manejador_provincia_invalida,
    manejador_rate_limit,
)
from src.api_http.v1.busquedas import router as busquedas_router
from src.api_http.v1.comparar import router as comparar_router
from src.api_http.v1.me import router as me_router
from src.api_http.v1.metricas import router as metricas_router
from src.api_http.v1.productos import router as productos_router
from src.config import settings
from src.dominio.errores import RateLimitError
from src.dominio.productos.errores import ProductoNoEncontradoError
from src.dominio.usuarios.errores import (
    ProvinciaInvalidaError,
    UsuarioNoAutorizadoError,
)

CHECK_TIMEOUT_SEGUNDOS = 2.0

logger = logging.getLogger(__name__)


def _iniciar_sentry() -> None:
    """Activa Sentry si hay DSN configurado."""
    if not settings.sentry_dsn.get_secret_value():
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.app_env,
        traces_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    _iniciar_sentry()
    yield
    await dispose_sticky_reads()
    await dispose_engines()
    await dispose_limitador()


app = FastAPI(title="Comparador de Precios API", lifespan=lifespan)
app.add_exception_handler(ErrorAPI, manejador_error_api)
app.add_exception_handler(RateLimitError, manejador_rate_limit)
app.add_exception_handler(ProductoNoEncontradoError, manejador_producto_no_encontrado)
app.add_exception_handler(UsuarioNoAutorizadoError, manejador_no_autorizado)
app.add_exception_handler(ProvinciaInvalidaError, manejador_provincia_invalida)
app.add_exception_handler(Exception, manejador_error_inesperado)
app.include_router(me_router)
app.include_router(metricas_router)
app.include_router(comparar_router)
app.include_router(busquedas_router)
app.include_router(productos_router)


async def check_database(url: str) -> bool:
    """Comprueba una conexión de base de datos con un SELECT 1."""
    if not url:
        return False

    engine = None
    try:
        engine = create_async_engine(
            url, connect_args={"timeout": CHECK_TIMEOUT_SEGUNDOS}
        )
        async with asyncio.timeout(CHECK_TIMEOUT_SEGUNDOS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - cualquier fallo implica no readiness
        # La readiness solo expone el estado, nunca el error ni la DSN.
        logger.warning("Database readiness check failed: %s", type(exc).__name__)
        return False
    finally:
        if engine is not None:
            try:
                await engine.dispose()
            except Exception as exc:  # noqa: BLE001 - cierre best-effort
                logger.warning("Database engine dispose failed: %s", type(exc).__name__)


async def check_redis(url: str) -> bool:
    """Comprueba la conexión con Redis mediante PING."""
    if not url:
        return False

    client = None
    try:
        client = Redis.from_url(
            url,
            socket_connect_timeout=CHECK_TIMEOUT_SEGUNDOS,
            socket_timeout=CHECK_TIMEOUT_SEGUNDOS,
        )
        async with asyncio.timeout(CHECK_TIMEOUT_SEGUNDOS):
            return bool(await client.ping())
    except Exception as exc:  # noqa: BLE001 - cualquier fallo implica no readiness
        logger.warning("Redis readiness check failed: %s", type(exc).__name__)
        return False
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception as exc:  # noqa: BLE001 - cierre best-effort
                logger.warning("Redis client close failed: %s", type(exc).__name__)


async def check_dependencies() -> dict[str, bool]:
    """Comprueba en paralelo las dependencias críticas de la API."""
    names = ("database_rw", "database_ro", "redis")
    results = await asyncio.gather(
        check_database(settings.database_url_rw.get_secret_value()),
        check_database(settings.database_url_ro.get_secret_value()),
        check_redis(settings.redis_url),
        return_exceptions=True,
    )
    return {name: result is True for name, result in zip(names, results, strict=True)}


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready() -> JSONResponse:
    checks = await check_dependencies()
    ready = all(checks.values())
    status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if ready else "not_ready",
            "checks": {name: "ok" if ok else "error" for name, ok in checks.items()},
        },
    )
