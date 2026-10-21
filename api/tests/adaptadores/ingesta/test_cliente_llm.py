"""Tests de los clientes de LLM (con `httpx.MockTransport`, sin red)."""

from __future__ import annotations

import json

import httpx
import pytest

from src.adaptadores.ingesta.cliente_llm import (
    ClienteAnthropic,
    ClienteOpenAICompatible,
    crear_cliente_llm,
)
from src.adaptadores.ingesta.errores import ErrorClienteLLM
from src.adaptadores.ingesta.prompts import PROMPT_SISTEMA
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


def test_avisa_si_el_modelo_no_trae_busqueda_web(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sin búsqueda web el productor se inventa las URLs de las fichas."""
    with caplog.at_level("WARNING", logger="src.adaptadores.ingesta.cliente_llm"):
        crear_cliente_llm(
            proveedor="openrouter",
            api_key="clave",
            modelo="openai/gpt-4o-mini",
            cliente_http=_cliente(_respuesta(200, {})),
        )

    assert any("búsqueda web" in registro.message for registro in caplog.records)


def test_no_avisa_si_el_modelo_lleva_busqueda_web(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING", logger="src.adaptadores.ingesta.cliente_llm"):
        crear_cliente_llm(
            proveedor="openrouter",
            api_key="clave",
            modelo="openai/gpt-4o-mini:online",
            cliente_http=_cliente(_respuesta(200, {})),
        )

    assert not [
        registro for registro in caplog.records if "búsqueda web" in registro.message
    ]


@pytest.mark.asyncio
async def test_openrouter_envia_el_motor_de_busqueda_configurado() -> None:
    """El motor de búsqueda se manda en `plugins` si está configurado.

    La búsqueda web se cobra aparte aunque el modelo sea gratuito (0,005 $
    con "parallel", 0,007 $ con el motor por defecto), así que conviene
    poder fijar el motor más barato.
    """
    capturado: dict[str, object] = {}

    async def _captura(peticion: httpx.Request) -> httpx.Response:
        capturado["cuerpo"] = json.loads(peticion.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"encontrado": false}'}}]}
        )

    cliente = ClienteOpenAICompatible(
        cliente_http=httpx.AsyncClient(transport=httpx.MockTransport(_captura)),
        base_url="https://openrouter.ai/api/v1",
        api_key="clave",
        modelo="nvidia/nemotron-3.5-super-vl:free:online",
        motor_busqueda="parallel",
    )

    await cliente.completar("prompt")

    assert capturado["cuerpo"] == {
        "model": "nvidia/nemotron-3.5-super-vl:free:online",
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": "prompt"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "plugins": [{"id": "web", "engine": "parallel"}],
    }


@pytest.mark.asyncio
async def test_sin_motor_de_busqueda_no_manda_plugins() -> None:
    """Sin motor configurado, el proveedor usa el suyo por defecto."""
    capturado: dict[str, object] = {}

    async def _captura(peticion: httpx.Request) -> httpx.Response:
        capturado["cuerpo"] = json.loads(peticion.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"encontrado": false}'}}]}
        )

    cliente = ClienteOpenAICompatible(
        cliente_http=httpx.AsyncClient(transport=httpx.MockTransport(_captura)),
        base_url="https://openrouter.ai/api/v1",
        api_key="clave",
        modelo="nvidia/nemotron-3.5-super-vl:free:online",
    )

    await cliente.completar("prompt")

    cuerpo = capturado["cuerpo"]
    assert isinstance(cuerpo, dict)
    assert "plugins" not in cuerpo
