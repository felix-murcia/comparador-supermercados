"""Tests de contrato de los puertos de ingesta y caché.

Los helpers `assert_contrato_*` validan los invariantes que deberá cumplir
cualquier adaptador real (LLM, fetch+reglas, Redis) en la Épica 3.
"""

from __future__ import annotations

import pytest

from src.dominio.precios.estados import ESTADOS_PRECIO
from src.puertos.cache import Cache, ValorCache
from src.puertos.productor import Candidato, Productor
from src.puertos.verificador import ResultadoVerificacion, Verificador

CANDIDATO_VALIDO: Candidato = {
    "encontrado": True,
    "precio_eur": 1.29,
    "url_fuente": "https://example.test/leche",
    "formato": "1L",
    "confianza": 0.9,
}


class ProductorFake:
    def __init__(self, candidato: Candidato | None = None) -> None:
        self._candidato = dict(candidato or CANDIDATO_VALIDO)
        self.llamadas: list[tuple[str, str]] = []

    async def producir(self, query: str, cadena: str) -> Candidato:
        self.llamadas.append((query, cadena))
        return dict(self._candidato)


class VerificadorFake:
    def __init__(self, resultado: ResultadoVerificacion) -> None:
        self._resultado = resultado
        self.verificados: list[Candidato] = []

    async def verificar(self, candidato: Candidato) -> ResultadoVerificacion:
        self.verificados.append(candidato)
        return self._resultado


class CacheFake:
    def __init__(self) -> None:
        self.valores: dict[str, ValorCache] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> ValorCache | None:
        return self.valores.get(key)

    async def set(self, key: str, value: ValorCache, ttl: int) -> None:
        self.valores[key] = value
        self.ttls[key] = ttl

    async def invalidar_prefijo(self, prefijo: str) -> None:
        for key in [clave for clave in self.valores if clave.startswith(prefijo)]:
            del self.valores[key]
            self.ttls.pop(key, None)


async def assert_contrato_productor(productor: Productor) -> Candidato:
    candidato = await productor.producir("leche entera", "dia")
    assert isinstance(candidato, dict)
    if candidato.get("encontrado"):
        assert candidato.get("url_fuente"), (
            "url_fuente es obligatoria si encontrado=true"
        )
        assert isinstance(candidato.get("precio_eur"), (int, float))
    return candidato


async def assert_contrato_verificador(
    verificador: Verificador, candidato: Candidato
) -> tuple[str, list[str]]:
    resultado = await verificador.verificar(candidato)
    assert resultado.estado in ESTADOS_PRECIO
    assert isinstance(resultado.motivos, list)
    assert all(isinstance(motivo, str) for motivo in resultado.motivos)
    return resultado.estado, resultado.motivos


async def assert_contrato_cache(cache: Cache) -> None:
    assert await cache.get("v1:inexistente") is None

    valor: ValorCache = {"resultados": [{"producto": "leche", "precio_eur": 1.29}]}
    await cache.set("v1:test", valor, ttl=60)
    assert await cache.get("v1:test") == valor

    await cache.set("v1:otro", valor, ttl=60)
    await cache.invalidar_prefijo("v1:test")

    assert await cache.get("v1:test") is None
    assert await cache.get("v1:otro") == valor


def test_los_fakes_cumplen_los_protocolos() -> None:
    assert isinstance(ProductorFake(), Productor)
    assert isinstance(
        VerificadorFake(ResultadoVerificacion("verificado", [])), Verificador
    )
    assert isinstance(CacheFake(), Cache)


def test_estados_precio_coinciden_con_el_esquema() -> None:
    assert ESTADOS_PRECIO == ("verificado", "sospechoso", "rechazado")


@pytest.mark.asyncio
async def test_contrato_productor() -> None:
    productor = ProductorFake()

    candidato = await assert_contrato_productor(productor)

    assert candidato == CANDIDATO_VALIDO
    assert productor.llamadas == [("leche entera", "dia")]


@pytest.mark.asyncio
async def test_contrato_productor_no_encontrado() -> None:
    productor = ProductorFake(
        {"encontrado": False, "motivo_si_no_encontrado": "sin stock"}
    )

    candidato = await assert_contrato_productor(productor)

    assert candidato["encontrado"] is False


@pytest.mark.asyncio
async def test_contrato_verificador() -> None:
    verificador = VerificadorFake(
        ResultadoVerificacion("sospechoso", ["precio no aparece en el HTML"])
    )

    estado, motivos = await assert_contrato_verificador(verificador, CANDIDATO_VALIDO)

    assert estado == "sospechoso"
    assert motivos == ["precio no aparece en el HTML"]
    assert verificador.verificados == [CANDIDATO_VALIDO]


@pytest.mark.asyncio
async def test_contrato_cache() -> None:
    cache = CacheFake()

    await assert_contrato_cache(cache)


@pytest.mark.asyncio
async def test_cache_fake_guarda_ttl() -> None:
    cache = CacheFake()

    await cache.set("v1:test", {"a": 1}, ttl=120)

    assert cache.ttls == {"v1:test": 120}
