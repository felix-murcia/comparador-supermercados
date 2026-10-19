"""Integración de la cola de jobs (`busquedas` + SKIP LOCKED)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.adaptadores.persistencia.cola_busquedas import PostgresColaJobs
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.dominio.busquedas.entidades import BusquedaNueva
from src.puertos.cola import ColaJobs

pytestmark = pytest.mark.asyncio


async def _crear_job(sesion: AsyncSession, cache_key: str) -> str:
    repositorio = SQLAlchemyRepositorioBusquedas(sesion)
    busqueda = await repositorio.crear(
        BusquedaNueva(
            query="leche entera",
            cadenas=("dia",),
            cache_key=cache_key,
        )
    )
    await sesion.commit()
    return str(busqueda.id)


async def test_la_cola_cumple_el_protocolo(sesion_rw: AsyncSession) -> None:
    assert isinstance(PostgresColaJobs(sesion_rw), ColaJobs)


async def test_reclama_un_job_pendiente(sesion_rw: AsyncSession) -> None:
    job_id = await _crear_job(sesion_rw, "v1:a")

    reclamada = await PostgresColaJobs(sesion_rw).reclamar(timeout_minutos=15)
    await sesion_rw.commit()

    assert reclamada is not None
    assert str(reclamada.id) == job_id
    assert reclamada.estado == "en_progreso"
    assert reclamada.progreso == 0


async def test_no_reclama_nada_si_la_cola_esta_vacia(sesion_rw: AsyncSession) -> None:
    assert await PostgresColaJobs(sesion_rw).reclamar(timeout_minutos=15) is None


async def test_otro_worker_no_reclama_el_mismo_job(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    await _crear_job(sesion_rw, "v1:unico")

    primero = await PostgresColaJobs(sesion_rw).reclamar(timeout_minutos=15)

    fabrica = async_sessionmaker(motor_rw, expire_on_commit=False)
    async with fabrica() as otra_sesion:
        segundo = await PostgresColaJobs(otra_sesion).reclamar(timeout_minutos=15)

    assert primero is not None
    assert segundo is None


async def test_dos_workers_toman_jobs_distintos(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    await _crear_job(sesion_rw, "v1:uno")
    await _crear_job(sesion_rw, "v1:dos")

    primero = await PostgresColaJobs(sesion_rw).reclamar(timeout_minutos=15)

    fabrica = async_sessionmaker(motor_rw, expire_on_commit=False)
    async with fabrica() as otra_sesion:
        segundo = await PostgresColaJobs(otra_sesion).reclamar(timeout_minutos=15)

    assert primero is not None
    assert segundo is not None
    assert primero.id != segundo.id


async def test_reclama_un_job_que_se_quedo_en_progreso(
    sesion_rw: AsyncSession,
) -> None:
    job_id = await _crear_job(sesion_rw, "v1:abandonado")
    await sesion_rw.execute(
        text(
            "UPDATE busquedas SET estado = 'en_progreso', "
            "creado_en = now() - interval '2 hours' WHERE id = :id"
        ),
        {"id": job_id},
    )
    await sesion_rw.commit()

    reclamada = await PostgresColaJobs(sesion_rw).reclamar(timeout_minutos=15)
    await sesion_rw.commit()

    assert reclamada is not None
    assert str(reclamada.id) == job_id
    assert reclamada.estado == "en_progreso"


async def test_no_reclama_un_job_en_progreso_reciente(
    sesion_rw: AsyncSession,
) -> None:
    job_id = await _crear_job(sesion_rw, "v1:reciente")
    await sesion_rw.execute(
        text("UPDATE busquedas SET estado = 'en_progreso' WHERE id = :id"),
        {"id": job_id},
    )
    await sesion_rw.commit()

    assert await PostgresColaJobs(sesion_rw).reclamar(timeout_minutos=15) is None
