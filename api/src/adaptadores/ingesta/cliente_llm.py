"""Clientes de LLM con búsqueda web.

- `ClienteOpenAICompatible`: API de chat completions de OpenAI y compatibles
  (xAI).
- `ClienteAnthropic`: API de mensajes de Anthropic.

Ambos implementan el puerto `ClienteLLM` y comparten el tratamiento de errores
HTTP: los 5xx y los fallos de red son transitorios, el resto no.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.adaptadores.ingesta.errores import ErrorClienteLLM
from src.adaptadores.ingesta.prompts import PROMPT_SISTEMA
from src.puertos.llm import ClienteLLM

logger = logging.getLogger(__name__)

BASE_URLS_POR_DEFECTO = {
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


async def _enviar(
    cliente_http: httpx.AsyncClient,
    url: str,
    cuerpo: dict[str, Any],
    cabeceras: dict[str, str],
) -> dict[str, Any]:
    """POST con mapeo de errores HTTP a `ErrorClienteLLM`."""
    try:
        respuesta = await cliente_http.post(url, json=cuerpo, headers=cabeceras)
    except httpx.HTTPError as error:
        raise ErrorClienteLLM(
            f"fallo de red con el proveedor de LLM: {type(error).__name__}",
            transitorio=True,
        ) from error

    if respuesta.status_code >= 500:
        raise ErrorClienteLLM(
            f"error del proveedor de LLM: HTTP {respuesta.status_code}",
            transitorio=True,
        )
    if respuesta.status_code >= 400:
        raise ErrorClienteLLM(
            f"error del proveedor de LLM: HTTP {respuesta.status_code}",
            transitorio=False,
        )

    try:
        datos = respuesta.json()
    except ValueError as error:
        raise ErrorClienteLLM(
            "respuesta no JSON del proveedor de LLM", transitorio=False
        ) from error
    if not isinstance(datos, dict):
        raise ErrorClienteLLM(
            "respuesta no JSON del proveedor de LLM", transitorio=False
        )
    return datos


def _texto_de_bloques(datos: dict[str, Any]) -> str:
    try:
        bloques = datos["content"]
        texto = bloques[0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise ErrorClienteLLM(
            "respuesta malformada del proveedor de LLM", transitorio=False
        ) from error
    if not isinstance(texto, str):
        raise ErrorClienteLLM(
            "respuesta malformada del proveedor de LLM", transitorio=False
        )
    return texto


class ClienteOpenAICompatible:
    """Chat completions con la API de OpenAI y compatibles (xAI, OpenRouter)."""

    def __init__(
        self,
        *,
        cliente_http: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        modelo: str,
    ) -> None:
        self._cliente_http = cliente_http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._modelo = modelo

    def _cabeceras(self) -> dict[str, str]:
        cabeceras = {"Authorization": f"Bearer {self._api_key}"}
        if "openrouter.ai" in self._base_url:
            # OpenRouter recomienda identificar la aplicación.
            cabeceras["HTTP-Referer"] = "https://demo.sagarebel.com"
            cabeceras["X-Title"] = "Comparador de Precios"
        return cabeceras

    async def completar(self, prompt: str) -> str:
        cuerpo: dict[str, Any] = {
            "model": self._modelo,
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        datos = await _enviar(
            self._cliente_http,
            f"{self._base_url}/chat/completions",
            cuerpo,
            self._cabeceras(),
        )
        try:
            contenido = datos["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ErrorClienteLLM(
                "respuesta malformada del proveedor de LLM", transitorio=False
            ) from error
        if not isinstance(contenido, str):
            raise ErrorClienteLLM(
                "respuesta malformada del proveedor de LLM", transitorio=False
            )
        return contenido


class ClienteAnthropic:
    """API de mensajes de Anthropic."""

    def __init__(
        self,
        *,
        cliente_http: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        modelo: str,
    ) -> None:
        self._cliente_http = cliente_http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._modelo = modelo

    async def completar(self, prompt: str) -> str:
        cuerpo: dict[str, Any] = {
            "model": self._modelo,
            "max_tokens": 1024,
            "system": PROMPT_SISTEMA,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        datos = await _enviar(
            self._cliente_http,
            f"{self._base_url}/messages",
            cuerpo,
            {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        return _texto_de_bloques(datos)


def crear_cliente_llm(
    *,
    proveedor: str,
    api_key: str,
    modelo: str,
    cliente_http: httpx.AsyncClient,
    base_url: str | None = None,
) -> ClienteLLM:
    """Construye el cliente del proveedor configurado.

    `base_url` permite apuntar a un proxy o a otro servicio compatible.
    """
    if not api_key:
        raise ValueError("Falta la API key del LLM (LLM_API_KEY)")
    if not modelo:
        raise ValueError("Falta el modelo del LLM (LLM_MODEL)")

    url = base_url or BASE_URLS_POR_DEFECTO.get(proveedor)
    if not url:
        raise ValueError(f"Proveedor de LLM no soportado: {proveedor}")

    if proveedor == "anthropic":
        return ClienteAnthropic(
            cliente_http=cliente_http, base_url=url, api_key=api_key, modelo=modelo
        )
    return ClienteOpenAICompatible(
        cliente_http=cliente_http, base_url=url, api_key=api_key, modelo=modelo
    )
