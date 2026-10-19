"""Tests de los clientes de LLM (con `httpx.MockTransport`, sin red)."""

from __future__ import annotations

import httpx
import pytest

from src.adaptadores.ingesta.cliente_llm import (
    ClienteAnthropic,
    ClienteOpenAICompatible,
    crear_cliente_llm,
)
from src.adaptadores.ingesta.errores import ErrorClienteLLM
from src.puertos.llm import ClienteLLM


def _cliente(
    manejador: httpx.AsyncBaseTransport,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=manejador)


def _respuesta(codigo: int, cuerpo: object) -> httpx.MockTransport:
    return httpx.MockTransport(
        lambda _request: httpx.Response(codigo, json=cuerpo)  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_openai_devuelve_el_contenido_del_mensaje() -> None:
    transporte = _respuesta(
        200, {"choices": [{"message": {"content": '{"encontrado": false}'}}]}
    )
    cliente = ClienteOpenAICompatible(
        cliente_http=_cliente(transporte),
        base_url="https://api.openai.com/v1",
        api_key="clave",
        modelo="gpt-4o-mini",
    )

    assert await cliente.completar("prompt") == '{"encontrado": false}'


@pytest.mark.asyncio
async def test_openai_marca_transitorio_los_5xx() -> None:
    cliente = ClienteOpenAICompatible(
        cliente_http=_cliente(_respuesta(503, {"error": "no disponible"})),
        base_url="https://api.openai.com/v1",
        api_key="clave",
        modelo="gpt-4o-mini",
    )

    with pytest.raises(ErrorClienteLLM) as excinfo:
        await cliente.completar("prompt")

    assert excinfo.value.transitorio is True


@pytest.mark.asyncio
async def test_openai_no_reintenta_los_4xx() -> None:
    cliente = ClienteOpenAICompatible(
        cliente_http=_cliente(_respuesta(401, {"error": "clave invalida"})),
        base_url="https://api.openai.com/v1",
        api_key="clave",
        modelo="gpt-4o-mini",
    )

    with pytest.raises(ErrorClienteLLM) as excinfo:
        await cliente.completar("prompt")

    assert excinfo.value.transitorio is False


@pytest.mark.asyncio
async def test_openai_avisa_si_la_respuesta_esta_malformada() -> None:
    cliente = ClienteOpenAICompatible(
        cliente_http=_cliente(_respuesta(200, {"choices": []})),
        base_url="https://api.openai.com/v1",
        api_key="clave",
        modelo="gpt-4o-mini",
    )

    with pytest.raises(ErrorClienteLLM) as excinfo:
        await cliente.completar("prompt")

    assert excinfo.value.transitorio is False


@pytest.mark.asyncio
async def test_anthropic_devuelve_el_texto_del_bloque() -> None:
    transporte = _respuesta(
        200, {"content": [{"type": "text", "text": '{"ok": true}'}]}
    )
    cliente = ClienteAnthropic(
        cliente_http=_cliente(transporte),
        base_url="https://api.anthropic.com/v1",
        api_key="clave",
        modelo="claude-sonnet-4-5",
    )

    assert await cliente.completar("prompt") == '{"ok": true}'


@pytest.mark.asyncio
async def test_anthropic_marca_transitorio_los_5xx() -> None:
    cliente = ClienteAnthropic(
        cliente_http=_cliente(_respuesta(500, {"error": "boom"})),
        base_url="https://api.anthropic.com/v1",
        api_key="clave",
        modelo="claude-sonnet-4-5",
    )

    with pytest.raises(ErrorClienteLLM) as excinfo:
        await cliente.completar("prompt")

    assert excinfo.value.transitorio is True


def test_la_fabrica_elige_cliente_segun_el_proveedor() -> None:
    cliente_http = _cliente(_respuesta(200, {}))

    openai = crear_cliente_llm(
        proveedor="openai",
        api_key="clave",
        modelo="gpt-4o-mini",
        cliente_http=cliente_http,
    )
    anthropic = crear_cliente_llm(
        proveedor="anthropic",
        api_key="clave",
        modelo="claude-sonnet-4-5",
        cliente_http=cliente_http,
    )

    assert isinstance(openai, ClienteOpenAICompatible)
    assert isinstance(anthropic, ClienteAnthropic)
    assert isinstance(openai, ClienteLLM)


def test_la_fabrica_rechaza_proveedores_no_soportados() -> None:
    with pytest.raises(ValueError):
        crear_cliente_llm(
            proveedor="otro",
            api_key="clave",
            modelo="modelo",
            cliente_http=_cliente(_respuesta(200, {})),
        )


def test_la_fabrica_exige_api_key_y_modelo() -> None:
    cliente_http = _cliente(_respuesta(200, {}))

    with pytest.raises(ValueError):
        crear_cliente_llm(
            proveedor="openai", api_key="", modelo="modelo", cliente_http=cliente_http
        )
    with pytest.raises(ValueError):
        crear_cliente_llm(
            proveedor="openai", api_key="clave", modelo="", cliente_http=cliente_http
        )
