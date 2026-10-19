"""Tests de los manejadores globales de errores (T4.6)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api_http.errores import (
    ErrorAPI,
    manejador_error_api,
    manejador_error_inesperado,
    manejador_no_autorizado,
    manejador_producto_no_encontrado,
    manejador_rate_limit,
)
from src.dominio.errores import RateLimitError
from src.dominio.productos.errores import ProductoNoEncontradoError
from src.dominio.usuarios.errores import UsuarioNoAutorizadoError

app = FastAPI()
app.add_exception_handler(ErrorAPI, manejador_error_api)
app.add_exception_handler(RateLimitError, manejador_rate_limit)
app.add_exception_handler(ProductoNoEncontradoError, manejador_producto_no_encontrado)
app.add_exception_handler(UsuarioNoAutorizadoError, manejador_no_autorizado)
app.add_exception_handler(Exception, manejador_error_inesperado)

client = TestClient(app, raise_server_exceptions=False)


@app.get("/producto")
async def producto() -> None:
    raise ProductoNoEncontradoError("abc-123")


@app.get("/privado")
async def privado() -> None:
    raise UsuarioNoAutorizadoError("el job no pertenece a este usuario")


@app.get("/limite")
async def limite() -> None:
    raise RateLimitError(10, 60)


@app.get("/inesperado")
async def inesperado() -> None:
    raise RuntimeError("fallo interno con secretos")


def test_producto_no_encontrado_devuelve_404() -> None:
    respuesta = client.get("/producto")

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "PRODUCTO_NO_ENCONTRADO"


def test_usuario_no_autorizado_devuelve_403() -> None:
    respuesta = client.get("/privado")

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "NO_AUTORIZADO"


def test_rate_limit_devuelve_429() -> None:
    respuesta = client.get("/limite")

    assert respuesta.status_code == 429
    assert respuesta.json()["code"] == "RATE_LIMIT"


def test_error_inesperado_devuelve_500_sin_traza() -> None:
    respuesta = client.get("/inesperado")

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "ERROR_INTERNO"
    assert "secretos" not in respuesta.text
    assert "Traceback" not in respuesta.text


@pytest.mark.parametrize("codigo", ["PRODUCTO_NO_ENCONTRADO", "NO_AUTORIZADO"])
def test_los_errores_de_dominio_no_filtran_detalles(codigo: str) -> None:
    respuesta = client.get(
        "/producto" if codigo == "PRODUCTO_NO_ENCONTRADO" else "/privado"
    )

    assert respuesta.json()["code"] == codigo
    assert "Traceback" not in respuesta.text
