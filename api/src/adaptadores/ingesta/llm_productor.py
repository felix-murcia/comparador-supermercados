"""Productor de precios basado en un LLM con búsqueda web.

El productor propone un candidato; nunca es la fuente de verdad. La
verificación determinista llega después (ver `Verificador`).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from src.adaptadores.ingesta.errores import ErrorClienteLLM
from src.adaptadores.ingesta.prompts import construir_prompt
from src.dominio.precios.errores import ErrorProductor
from src.puertos.llm import ClienteLLM
from src.puertos.productor import Candidato

logger = logging.getLogger(__name__)

INTENTOS_POR_DEFECTO = 3
RETROCESO_BASE_SEGUNDOS = 0.5

_CAMPOS_OBLIGATORIOS_SI_ENCONTRADO = ("nombre", "formato", "precio_eur", "url_fuente")


def _retroceso(intento: int) -> float:
    """Espera antes del siguiente intento: 0.5 s, 1 s, 2 s, ..."""
    return RETROCESO_BASE_SEGUNDOS * (2**intento)


def _validar_candidato(datos: dict[str, Any]) -> None:
    encontrado = datos.get("encontrado")
    if not isinstance(encontrado, bool):
        raise ErrorProductor(
            "falta el campo 'encontrado' o no es booleano", reintentable=False
        )

    if not encontrado:
        if not datos.get("motivo_si_no_encontrado"):
            raise ErrorProductor(
                "falta 'motivo_si_no_encontrado' cuando el producto no aparece",
                reintentable=False,
            )
        return

    faltantes = [
        campo
        for campo in _CAMPOS_OBLIGATORIOS_SI_ENCONTRADO
        if datos.get(campo) in (None, "")
    ]
    if faltantes:
        raise ErrorProductor(
            f"faltan campos obligatorios: {', '.join(faltantes)}", reintentable=False
        )

    precio = datos.get("precio_eur")
    if isinstance(precio, bool) or not isinstance(precio, (int, float)) or precio <= 0:
        raise ErrorProductor(
            "'precio_eur' debe ser un número mayor que 0", reintentable=False
        )

    url = datos.get("url_fuente")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ErrorProductor(
            "'url_fuente' debe ser una URL http(s)", reintentable=False
        )


def _parsear_candidato(respuesta: str) -> Candidato:
    try:
        datos = json.loads(respuesta)
    except json.JSONDecodeError as error:
        raise ErrorProductor(
            "el LLM no devolvió JSON válido", reintentable=False
        ) from error
    if not isinstance(datos, dict):
        raise ErrorProductor("el LLM no devolvió un objeto JSON", reintentable=False)
    _validar_candidato(datos)
    return datos


class LLMProductor:
    """Implementa el puerto `Productor` con un cliente de LLM."""

    def __init__(
        self,
        cliente: ClienteLLM,
        *,
        max_intentos: int = INTENTOS_POR_DEFECTO,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._cliente = cliente
        self._max_intentos = max(1, max_intentos)
        self._dormir = dormir

    async def producir(self, query: str, cadena: str) -> Candidato:
        prompt = construir_prompt(query, cadena)
        ultimo_error: ErrorClienteLLM | None = None

        for intento in range(self._max_intentos):
            try:
                respuesta = await self._cliente.completar(prompt)
            except ErrorClienteLLM as error:
                if not error.transitorio:
                    raise ErrorProductor(error.motivo, reintentable=False) from error
                ultimo_error = error
                logger.warning(
                    "Fallo transitorio del LLM (intento %s de %s): %s",
                    intento + 1,
                    self._max_intentos,
                    error.motivo,
                )
                if intento + 1 < self._max_intentos:
                    await self._dormir(_retroceso(intento))
                continue
            return _parsear_candidato(respuesta)

        motivo = ultimo_error.motivo if ultimo_error else "sin respuesta del LLM"
        raise ErrorProductor(motivo, reintentable=True)
