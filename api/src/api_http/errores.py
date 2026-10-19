"""Errores HTTP con el formato `{code, message}` de `CONVENTIONS.md` §6.4."""

from __future__ import annotations

from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from src.dominio.errores import RateLimitError


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
