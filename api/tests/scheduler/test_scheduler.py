"""Integración del scheduler de ingesta diaria."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.adaptadores.persistencia.cola_busquedas import PostgresColaJobs
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.dominio.busquedas.reglas import calcular_cache_key
from src.dominio.listas.reglas import PREFIJO_RESUMEN
from src.dominio.productos.entidades import ProductoNuevo
from src.scheduler import (
    HORA_INGESTA,
    MINUTO_INGESTA,
    PREFIJO_CACHE,
    ZONA_HORARIA,
    construir_scheduler,
    encolar_ingesta,
    esperar_cola_vacia,
    ingesta_diaria,
)

pytestmark = pytest.mark.asyncio


class CacheFake:
    def __init__(self) -> None:
        self.invalidados: list[str] = []

    async def get(self, key: str) -> dict[str, Any] | None:
        return None

    async def set(self, key: str, value: dict[str, Any], ttl: int) -> None:
        return None

    async def invalidar_prefijo(self, prefijo: str) -> None:
        self.invalidados.append(prefijo)


async def _crear_producto_con_cadena(
    sesion: AsyncSession, cadena_id: UUID, nombre: str = "Leche entera"
) -> None:
    producto = await SQLAlchemyRepositorioProductos(sesion).crear(
        ProductoNuevo(nombre=nombre, marca="Pascual", litros_o_kg=Decimal(1))
    )
    await SQLAlchemyRepositorioProductosCadenas(sesion).crear(
        producto_id=producto.id,
        cadena_id=cadena_id,
        url_producto="https://dia.test/leche-entera",
        nombre_en_cadena=nombre,
    )
    await sesion.commit()


async def test_encola_un_job_por_producto_activo(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    await _crear_producto_con_cadena(sesion_rw, cadena_dia)
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)

    encolados = await encolar_ingesta(sessionmaker)

    assert encolados == 1
    job = await SQLAlchemyRepositorioBusquedas(sesion_rw).obtener_por_cache_key(
        calcular_cache_key("Leche entera", ("dia",))
    )
    assert job is not None
    assert job.query == "Leche entera"
    assert job.cadenas == ("dia",)
    assert job.estado == "pendiente"


async def test_no_encola_jobs_sin_productos(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)

    assert await PostgresColaJobs(sesion_rw).contar_pendientes() == 0
    assert await encolar_ingesta(sessionmaker) == 0


async def test_la_ingesta_diaria_invalida_la_cache(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession, cadena_dia: UUID
) -> None:
    await _crear_producto_con_cadena(sesion_rw, cadena_dia)
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)
    cache = CacheFake()

    await ingesta_diaria(sessionmaker, cache, espera_maxima=0.1)

    # La ingesta cambia los precios: caducan las búsquedas y los resúmenes.
    assert cache.invalidados == [PREFIJO_CACHE, PREFIJO_RESUMEN]


async def test_esperar_cola_vacia_detecta_el_fin(
    motor_rw: AsyncEngine, sesion_rw: AsyncSession
) -> None:
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)

    assert await PostgresColaJobs(sesion_rw).contar_pendientes() == 0
    assert await esperar_cola_vacia(sessionmaker, espera_maxima=1.0) is True


async def test_la_ingesta_esta_programada_a_las_tres(motor_rw: AsyncEngine) -> None:
    sessionmaker = async_sessionmaker(motor_rw, expire_on_commit=False)
    scheduler = construir_scheduler(sessionmaker, CacheFake())

    trabajo = scheduler.get_job("ingesta_diaria")

    assert trabajo is not None
    assert isinstance(trabajo.trigger, CronTrigger)
    campos = {campo.name: str(campo) for campo in trabajo.trigger.fields}
    assert campos["hour"] == str(HORA_INGESTA)
    assert campos["minute"] == str(MINUTO_INGESTA)
    assert str(trabajo.trigger.timezone) == ZONA_HORARIA
