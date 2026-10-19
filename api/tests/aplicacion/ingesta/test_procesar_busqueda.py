"""Tests del caso de uso `ProcesarBusqueda` con dobles de los puertos."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from src.aplicacion.ingesta.buscar_producto import ResultadoBusqueda
from src.aplicacion.ingesta.procesar_busqueda import ProcesarBusqueda
from src.dominio.busquedas.entidades import Busqueda
from src.dominio.busquedas.estados import EstadoBusqueda


class BusquedasFake:
    def __init__(self) -> None:
        self.estados: list[tuple[Any, EstadoBusqueda, int]] = []

    async def crear(self, datos: Any) -> Busqueda:  # pragma: no cover - no se usa
        raise NotImplementedError

    async def obtener(self, busqueda_id: Any) -> Busqueda | None:  # pragma: no cover
        raise NotImplementedError

    async def obtener_por_cache_key(
        self, cache_key: str
    ) -> Busqueda | None:  # pragma: no cover - no se usa
        raise NotImplementedError

    async def actualizar_estado(
        self,
        busqueda_id: Any,
        estado: EstadoBusqueda,
        progreso: int,
        completado_en: datetime | None = None,
    ) -> Busqueda | None:
        self.estados.append((busqueda_id, estado, progreso))
        return None


def _busqueda(cadenas: tuple[str, ...] = ("dia", "carrefour")) -> Busqueda:
    return Busqueda(
        id=uuid4(),
        query="leche entera",
        cadenas=cadenas,
        estado="pendiente",
        progreso=0,
        cache_key="v1:abc",
        creado_en=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_actualiza_el_progreso_en_cada_cadena() -> None:
    repositorio = BusquedasFake()
    llamadas: list[tuple[str, str]] = []

    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:
        llamadas.append((query, cadena))
        return ResultadoBusqueda(estado="verificado", precio_id=uuid4())

    caso = ProcesarBusqueda(buscar=buscar, repositorio_busquedas=repositorio)
    busqueda = _busqueda()

    estado = await caso.ejecutar(busqueda)

    assert estado == "completada"
    assert llamadas == [("leche entera", "dia"), ("leche entera", "carrefour")]
    assert [progreso for _, _, progreso in repositorio.estados] == [50, 100, 100]
    assert repositorio.estados[-1][1] == "completada"


@pytest.mark.asyncio
async def test_finaliza_como_fallida_si_no_se_guarda_nada() -> None:
    repositorio = BusquedasFake()

    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:
        return ResultadoBusqueda(estado="rechazado", motivos=("agente_no_encontro",))

    caso = ProcesarBusqueda(buscar=buscar, repositorio_busquedas=repositorio)

    estado = await caso.ejecutar(_busqueda())

    assert estado == "fallida"
    assert repositorio.estados[-1][1] == "fallida"


@pytest.mark.asyncio
async def test_una_cadena_que_falla_no_tumba_el_job() -> None:
    repositorio = BusquedasFake()
    llamadas: list[str] = []

    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:
        llamadas.append(cadena)
        if cadena == "dia":
            raise RuntimeError("boom")
        return ResultadoBusqueda(estado="verificado", precio_id=uuid4())

    caso = ProcesarBusqueda(buscar=buscar, repositorio_busquedas=repositorio)

    estado = await caso.ejecutar(_busqueda())

    assert llamadas == ["dia", "carrefour"]
    assert estado == "completada"


@pytest.mark.asyncio
async def test_el_job_sin_cadenas_se_cierra_como_fallida() -> None:
    repositorio = BusquedasFake()

    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:  # pragma: no cover
        raise AssertionError("no debería buscar sin cadenas")

    caso = ProcesarBusqueda(buscar=buscar, repositorio_busquedas=repositorio)

    estado = await caso.ejecutar(_busqueda(cadenas=()))

    assert estado == "fallida"
    assert repositorio.estados[-1][2] == 100
