"""Integración del worker de ingesta contra Postgres real."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.adaptadores.persistencia.cola_busquedas import PostgresColaJobs
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.aplicacion.ingesta.buscar_producto import ResultadoBusqueda
from src.dominio.busquedas.entidades import BusquedaNueva
from src.worker import procesar_siguiente_job

pytestmark = pytest.mark.asyncio


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
