"""Tests del productor de precios basado en LLM."""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.adaptadores.ingesta.errores import ErrorClienteLLM
from src.adaptadores.ingesta.llm_productor import LLMProductor
from src.dominio.precios.errores import ErrorProductor
from src.puertos.llm import ClienteLLM
from src.puertos.productor import Productor

CANDIDATO_VALIDO: dict[str, Any] = {
    "encontrado": True,
    "nombre": "Leche entera",
    "marca": "Pascual",
    "categoria": "lacteos",
    "formato": "1L",
    "litros_o_kg": 1.0,
    "ean": "8412345678901",
    "precio_eur": 1.29,
    "url_fuente": "https://www.dia.es/leche-entera",
    "nombre_en_cadena": "Leche entera Pascual 1L",
    "confianza": 0.9,
}


class ClienteFake:
    """Devuelve respuestas predefinidas; puede fallar con una excepción."""

    def __init__(self, respuestas: list[Any]) -> None:
        self.respuestas = list(respuestas)
        self.prompts: list[str] = []

    async def completar(self, prompt: str) -> str:
        self.prompts.append(prompt)
        siguiente = self.respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


class DormirFake:
    """Registra las esperas entre reintentos."""

    def __init__(self) -> None:
        self.segundos: list[float] = []

    async def __call__(self, segundos: float) -> None:
        self.segundos.append(segundos)


def test_el_cliente_fake_cumple_el_protocolo() -> None:
    assert isinstance(ClienteFake([]), ClienteLLM)
    assert isinstance(LLMProductor(ClienteFake([])), Productor)


@pytest.mark.asyncio
async def test_produce_el_candidato_devuelto_por_el_llm() -> None:
    cliente = ClienteFake([json.dumps(CANDIDATO_VALIDO)])

    candidato = await LLMProductor(cliente).producir("leche entera", "dia")

    assert candidato == CANDIDATO_VALIDO


@pytest.mark.asyncio
async def test_el_prompt_incluye_producto_y_cadena() -> None:
    cliente = ClienteFake([json.dumps(CANDIDATO_VALIDO)])

    await LLMProductor(cliente).producir("leche entera", "dia")

    assert "leche entera" in cliente.prompts[0]
    assert "dia" in cliente.prompts[0]


@pytest.mark.asyncio
async def test_candidato_no_encontrado_se_acepta() -> None:
    cliente = ClienteFake(
        [
            json.dumps(
                {"encontrado": False, "motivo_si_no_encontrado": "agente_no_encontro"}
            )
        ]
    )

    candidato = await LLMProductor(cliente).producir("quinoa", "dia")

    assert candidato["encontrado"] is False
    assert candidato["motivo_si_no_encontrado"] == "agente_no_encontro"


@pytest.mark.asyncio
async def test_texto_no_json_produce_error_controlado() -> None:
    cliente = ClienteFake(["Perdona, no puedo buscar eso ahora."])

    with pytest.raises(ErrorProductor) as excinfo:
        await LLMProductor(cliente).producir("leche entera", "dia")

    assert excinfo.value.reintentable is False
    assert "JSON" in excinfo.value.motivo


@pytest.mark.asyncio
async def test_json_que_no_es_objeto_produce_error_controlado() -> None:
    cliente = ClienteFake(["[1, 2, 3]"])

    with pytest.raises(ErrorProductor):
        await LLMProductor(cliente).producir("leche entera", "dia")


@pytest.mark.asyncio
async def test_acepta_json_envuelto_en_ruido() -> None:
    """El JSON puede venir rodeado de texto (razonamiento, cabecera del proveedor).

    Los modelos que razonan antes de responder lo envuelven así, y el parser
    no debe desperdiciar la respuesta por eso.
    """
    cliente = ClienteFake(
        [
            "He buscado la ficha.\n\n```json\n"
            + json.dumps(CANDIDATO_VALIDO)
            + "\n```\nEspero que sirva."
        ]
    )

    candidato = await LLMProductor(cliente).producir("leche entera", "dia")

    assert candidato["url_fuente"] == "https://www.dia.es/leche-entera"
    assert candidato["precio_eur"] == 1.29


@pytest.mark.asyncio
async def test_acepta_json_con_texto_antes() -> None:
    cliente = ClienteFake(["\n\n" + json.dumps(CANDIDATO_VALIDO)])

    candidato = await LLMProductor(cliente).producir("leche entera", "dia")

    assert candidato["nombre"] == "Leche entera"


@pytest.mark.asyncio
async def test_el_prompt_pide_un_producto_concreto_en_la_cadena() -> None:
    """El prompt debe pedir la ficha exacta, no una búsqueda vaga.

    Con una consulta ambigua ("pizza") el modelo se abstiene y responde
    "encontrado": false; pidiendo la ficha concreta responde con la URL.
    """
    cliente = ClienteFake([json.dumps(CANDIDATO_VALIDO)])

    await LLMProductor(cliente).producir("Pizza 4 quesos 390 g", "dia")

    prompt = cliente.prompts[0]
    assert "Pizza 4 quesos 390 g" in prompt
    assert "dia" in prompt
    assert "ficha de producto" in prompt


@pytest.mark.asyncio
async def test_faltan_campos_obligatorios_produce_error_controlado() -> None:
    incompleto = {**CANDIDATO_VALIDO}
    del incompleto["nombre"]
    cliente = ClienteFake([json.dumps(incompleto)])

    with pytest.raises(ErrorProductor) as excinfo:
        await LLMProductor(cliente).producir("leche entera", "dia")

    assert "nombre" in excinfo.value.motivo


@pytest.mark.asyncio
async def test_encontrado_sin_url_fuente_produce_error_controlado() -> None:
    sin_url = {**CANDIDATO_VALIDO, "url_fuente": ""}
    cliente = ClienteFake([json.dumps(sin_url)])

    with pytest.raises(ErrorProductor) as excinfo:
        await LLMProductor(cliente).producir("leche entera", "dia")

    assert "url_fuente" in excinfo.value.motivo


@pytest.mark.asyncio
async def test_precio_invalido_produce_error_controlado() -> None:
    cliente = ClienteFake([json.dumps({**CANDIDATO_VALIDO, "precio_eur": 0})])

    with pytest.raises(ErrorProductor):
        await LLMProductor(cliente).producir("leche entera", "dia")


@pytest.mark.asyncio
async def test_reintenta_ante_error_transitorio() -> None:
    cliente = ClienteFake(
        [
            ErrorClienteLLM("HTTP 503", transitorio=True),
            json.dumps(CANDIDATO_VALIDO),
        ]
    )
    dormir = DormirFake()

    candidato = await LLMProductor(cliente, dormir=dormir).producir("leche", "dia")

    assert candidato == CANDIDATO_VALIDO
    assert len(cliente.prompts) == 2
    assert dormir.segundos == [1.0]


@pytest.mark.asyncio
async def test_agotados_los_intentos_produce_error_reintentable() -> None:
    cliente = ClienteFake(
        [ErrorClienteLLM("HTTP 503", transitorio=True) for _ in range(3)]
    )
    dormir = DormirFake()

    with pytest.raises(ErrorProductor) as excinfo:
        await LLMProductor(cliente, dormir=dormir).producir("leche", "dia")

    assert excinfo.value.reintentable is True
    assert len(cliente.prompts) == 3
    assert dormir.segundos == [1.0, 2.0]


@pytest.mark.asyncio
async def test_no_reintenta_ante_error_no_transitorio() -> None:
    cliente = ClienteFake([ErrorClienteLLM("HTTP 401", transitorio=False)])
    dormir = DormirFake()

    with pytest.raises(ErrorProductor) as excinfo:
        await LLMProductor(cliente, dormir=dormir).producir("leche", "dia")

    assert excinfo.value.reintentable is False
    assert len(cliente.prompts) == 1
    assert dormir.segundos == []
