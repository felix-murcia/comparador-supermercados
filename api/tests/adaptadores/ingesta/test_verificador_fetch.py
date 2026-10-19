"""Tests del verificador determinista con HTML cacheado en `tests/fixtures/`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from src.adaptadores.ingesta.verificador_fetch import (
    MOTIVO_DESVIACION,
    MOTIVO_FETCH_ERROR,
    MOTIVO_NO_ENCONTRADO,
    MOTIVO_PRECIO_AUSENTE,
    MOTIVO_UNIDAD_INCOHERENTE,
    MOTIVO_URL_INVALIDA,
    TIMEOUT_SEGUNDOS,
    USER_AGENT,
    FetchVerificador,
)
from src.puertos.verificador import Verificador

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

CANDIDATO: dict[str, Any] = {
    "encontrado": True,
    "nombre": "Leche entera",
    "marca": "Pascual",
    "categoria": "lacteos",
    "formato": "1L",
    "litros_o_kg": 1.0,
    "ean": "8412345678901",
    "precio_eur": 1.29,
    "url_fuente": "https://www.dia.test/leche-entera",
    "nombre_en_cadena": "Leche entera Pascual 1L",
    "confianza": 0.9,
}


def _html(nombre: str) -> str:
    return (_FIXTURES / nombre).read_text(encoding="utf-8")


def _transporte(html: str, *, estado: int = 200) -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda _request: httpx.Response(
            estado, text=html, headers={"content-type": "text/html; charset=utf-8"}
        )
    )


def _verificador(html: str, *, estado: int = 200) -> FetchVerificador:
    cliente = httpx.AsyncClient(transport=_transporte(html, estado=estado))
    return FetchVerificador(cliente)


def test_el_verificador_cumple_el_protocolo() -> None:
    cliente = httpx.AsyncClient(
        transport=_transporte(_html("producto_con_precio.html"))
    )

    assert isinstance(FetchVerificador(cliente), Verificador)


@pytest.mark.asyncio
async def test_verifica_si_el_precio_esta_en_el_html() -> None:
    verificador = _verificador(_html("producto_con_precio.html"))

    estado, motivos = await verificador.verificar(CANDIDATO)

    assert estado == "verificado"
    assert motivos == []


@pytest.mark.asyncio
async def test_tolera_el_precio_con_punto_decimal() -> None:
    verificador = _verificador(_html("producto_precio_con_punto.html"))

    estado, motivos = await verificador.verificar(CANDIDATO)

    assert estado == "verificado"
    assert motivos == []


@pytest.mark.asyncio
async def test_rechaza_si_el_precio_no_esta_en_el_html() -> None:
    verificador = _verificador(_html("producto_sin_precio.html"))

    estado, motivos = await verificador.verificar(CANDIDATO)

    assert estado == "rechazado"
    assert motivos == [MOTIVO_PRECIO_AUSENTE]


@pytest.mark.asyncio
async def test_rechaza_si_la_ficha_responde_error_http() -> None:
    verificador = _verificador(_html("producto_con_precio.html"), estado=500)

    estado, motivos = await verificador.verificar(CANDIDATO)

    assert estado == "rechazado"
    assert motivos == [MOTIVO_FETCH_ERROR]


@pytest.mark.asyncio
async def test_rechaza_si_el_fetch_falla() -> None:
    def falla(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red", request=_request)

    cliente = httpx.AsyncClient(transport=httpx.MockTransport(falla))
    verificador = FetchVerificador(cliente)

    estado, motivos = await verificador.verificar(CANDIDATO)

    assert estado == "rechazado"
    assert motivos == [MOTIVO_FETCH_ERROR]


@pytest.mark.asyncio
async def test_rechaza_sin_descargar_si_el_producto_no_se_encontro() -> None:
    peticiones: list[httpx.Request] = []

    def registra(request: httpx.Request) -> httpx.Response:
        peticiones.append(request)
        return httpx.Response(200, text=_html("producto_con_precio.html"))

    cliente = httpx.AsyncClient(transport=httpx.MockTransport(registra))
    verificador = FetchVerificador(cliente)

    estado, motivos = await verificador.verificar(
        {"encontrado": False, "motivo_si_no_encontrado": "agente_no_encontro"}
    )

    assert estado == "rechazado"
    assert motivos == [MOTIVO_NO_ENCONTRADO]
    assert peticiones == []


@pytest.mark.asyncio
async def test_rechaza_si_la_url_no_es_valida() -> None:
    verificador = _verificador(_html("producto_con_precio.html"))

    estado, motivos = await verificador.verificar(
        {**CANDIDATO, "url_fuente": "no-es-una-url"}
    )

    assert estado == "rechazado"
    assert motivos == [MOTIVO_URL_INVALIDA]


@pytest.mark.asyncio
async def test_sospecha_si_el_precio_por_unidad_no_es_coherente() -> None:
    verificador = _verificador(_html("producto_precio_incoherente.html"))

    estado, motivos = await verificador.verificar(
        {**CANDIDATO, "precio_eur": 6.49, "formato": "pack 3L", "litros_o_kg": 3.0}
    )

    assert estado == "sospechoso"
    assert motivos == [MOTIVO_UNIDAD_INCOHERENTE]


@pytest.mark.asyncio
async def test_sospecha_si_la_desviacion_supera_el_30_por_ciento() -> None:
    verificador = _verificador(_html("producto_con_precio.html"))

    estado, motivos = await verificador.verificar(
        {**CANDIDATO, "precio_eur_anterior": 0.80}
    )

    assert estado == "sospechoso"
    assert motivos == [MOTIVO_DESVIACION]


@pytest.mark.asyncio
async def test_no_sospecha_si_la_desviacion_es_pequena() -> None:
    verificador = _verificador(_html("producto_con_precio.html"))

    estado, motivos = await verificador.verificar(
        {**CANDIDATO, "precio_eur_anterior": 1.25}
    )

    assert estado == "verificado"
    assert motivos == []


@pytest.mark.asyncio
async def test_envia_user_agent_de_navegador_y_timeout_de_10s() -> None:
    peticiones: list[httpx.Request] = []

    def registra(request: httpx.Request) -> httpx.Response:
        peticiones.append(request)
        return httpx.Response(200, text=_html("producto_con_precio.html"))

    cliente = httpx.AsyncClient(transport=httpx.MockTransport(registra))
    verificador = FetchVerificador(cliente)

    await verificador.verificar(CANDIDATO)

    assert USER_AGENT.startswith("Mozilla/5.0")
    assert TIMEOUT_SEGUNDOS == 10.0
    assert peticiones[0].headers["user-agent"] == USER_AGENT
    assert peticiones[0].extensions["timeout"]["read"] == 10.0
