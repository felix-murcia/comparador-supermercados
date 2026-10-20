"""Integración del worker de ingesta contra Postgres real."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.adaptadores.persistencia.cola_busquedas import PostgresColaJobs
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.aplicacion.ingesta.buscar_producto import ResultadoBusqueda
from src.dominio.busquedas.entidades import BusquedaNueva
from src.dominio.precios.entidades import PrecioNuevo
from src.worker import _cachear_resultados, procesar_siguiente_job

pytestmark = pytest.mark.asyncio


class CacheEnMemoria:
    """Caché falsa que guarda lo que se le pasa, sin serializar a JSON."""

    def __init__(self) -> None:
        self.valores: dict[str, object] = {}

    async def get(self, key: str) -> object | None:
        return self.valores.get(key)

    async def set(self, key: str, value: object, ttl: int) -> None:
        self.valores[key] = value

    async def invalidar_prefijo(self, prefijo: str) -> None:
        for clave in list(self.valores):
            if clave.startswith(prefijo):
                del self.valores[clave]


async def test_devuelve_false_si_no_hay_jobs(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)

    assert await PostgresColaJobs(sesion_rw).contar_pendientes() == 0
    assert await procesar_siguiente_job(sessionmaker, buscar=_buscar_fake()) is False


async def test_procesa_el_job_y_lo_deja_completado(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)
    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)
    busqueda = await repositorio.crear(
        BusquedaNueva(
            query="leche entera",
            cadenas=("dia", "carrefour"),
            cache_key="v1:worker",
        )
    )
    await sesion_rw.commit()

    llamadas: list[tuple[str, str]] = []

    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:
        llamadas.append((query, cadena))
        return ResultadoBusqueda(estado="verificado", precio_id=uuid4())

    procesado = await procesar_siguiente_job(sessionmaker, buscar=buscar)

    assert procesado is True
    assert llamadas == [("leche entera", "dia"), ("leche entera", "carrefour")]

    job = await SQLAlchemyRepositorioBusquedas(sesion_rw).obtener(busqueda.id)
    assert job is not None
    assert job.estado == "completada"
    assert job.progreso == 100
    assert job.completado_en is not None


async def test_no_procesa_el_mismo_job_dos_veces(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)
    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)
    await repositorio.crear(
        BusquedaNueva(query="leche entera", cadenas=("dia",), cache_key="v1:worker-2")
    )
    await sesion_rw.commit()

    llamadas: list[str] = []

    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:
        llamadas.append(cadena)
        return ResultadoBusqueda(estado="verificado", precio_id=uuid4())

    primero = await procesar_siguiente_job(sessionmaker, buscar=buscar)
    segundo = await procesar_siguiente_job(sessionmaker, buscar=buscar)

    assert primero is True
    assert segundo is False
    assert llamadas == ["dia"]


def _buscar_fake():  # type: ignore[no-untyped-def]
    async def buscar(query: str, cadena: str) -> ResultadoBusqueda:
        return ResultadoBusqueda(estado="verificado", precio_id=uuid4())

    return buscar


async def test_cachea_el_resultado_para_que_la_siguiente_vez_sea_acierto(
    motor_rw: AsyncEngine,
    sesion_rw: AsyncSession,
    cadena_dia: UUID,
    producto_base: UUID,
    producto_cadena_base: UUID,
) -> None:
    """El resultado de la búsqueda se guarda con la clave del job.

    Si el valor cacheado no fuera un dict serializable (por ejemplo, una
    lista de coroutines sin await), la escritura falla y la siguiente
    búsqueda vuelve a ir al modelo.
    """
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)

    await SQLAlchemyRepositorioPrecios(sesion_rw).insertar(
        PrecioNuevo(
            producto_cadena_id=producto_cadena_base,
            importe_eur=Decimal("1.20"),
            url_fuente="https://dia.test/leche",
            fecha_consulta=datetime.now(UTC),
        )
    )
    await sesion_rw.commit()

    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)
    busqueda = await repositorio.crear(
        BusquedaNueva(
            query="leche entera",
            cadenas=("dia",),
            cache_key="v1:test-cache",
        )
    )
    await sesion_rw.commit()

    cache = CacheEnMemoria()
    await _cachear_resultados(sessionmaker, busqueda, cache)  # type: ignore[arg-type]

    guardado = cache.valores.get("v1:test-cache")
    assert guardado is not None, "el resultado no se cacheó"
    assert isinstance(guardado, dict)
    resultados = guardado["resultados"]
    assert isinstance(resultados, list)
    assert resultados, "debería cachear al menos un resultado"
    for resultado in resultados:
        assert isinstance(resultado, dict), "cada resultado debe ser un dict"
        assert isinstance(resultado["nombre"], str)
        assert isinstance(resultado["precio_eur"], str)
