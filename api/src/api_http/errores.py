"""Errores HTTP con el formato `{code, message}` de `CONVENTIONS.md` §6.4."""

from __future__ import annotations

import logging
from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from src.dominio.errores import RateLimitError
from src.dominio.productos.errores import ProductoNoEncontradoError
from src.dominio.usuarios.errores import (
    ProvinciaInvalidaError,
    UsuarioNoAutorizadoError,
)

logger = logging.getLogger(__name__)


class ErrorAPI(Exception):
    """Error de negocio con código estable; `message` puede cambiar."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def manejador_error_api(_: Request, exc: Exception) -> JSONResponse:
    error = cast(ErrorAPI, exc)
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message},
    )


def manejador_rate_limit(_: Request, exc: Exception) -> JSONResponse:
    error = cast(RateLimitError, exc)
    return JSONResponse(
        status_code=429,
        content={"code": "RATE_LIMIT", "message": str(error)},
    )


def manejador_producto_no_encontrado(_: Request, exc: Exception) -> JSONResponse:
    error = cast(ProductoNoEncontradoError, exc)
    return JSONResponse(
        status_code=404,
        content={"code": "PRODUCTO_NO_ENCONTRADO", "message": str(error)},
    )


def manejador_no_autorizado(_: Request, exc: Exception) -> JSONResponse:
    error = cast(UsuarioNoAutorizadoError, exc)
    return JSONResponse(
        status_code=403,
        content={"code": "NO_AUTORIZADO", "message": str(error)},
    )


def manejador_provincia_invalida(_: Request, exc: Exception) -> JSONResponse:
    error = cast(ProvinciaInvalidaError, exc)
    return JSONResponse(
        status_code=422,
        content={"code": "PROVINCIA_INVALIDA", "message": str(error)},
    )


def manejador_error_inesperado(_: Request, exc: Exception) -> JSONResponse:
    """500 sin traza al cliente; el error se registra y se envía a Sentry."""
    logger.exception("Error no controlado", exc_info=exc)
    _capturar_en_sentry(exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "ERROR_INTERNO",
            "message": "Se ha producido un error inesperado",
        },
    )


def _capturar_en_sentry(exc: Exception) -> None:
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:  # noqa: BLE001 - Sentry nunca debe romper la respuesta
        logger.debug("Sentry no disponible para capturar el error")
