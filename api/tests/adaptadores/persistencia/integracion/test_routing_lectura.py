from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.dominio.productos.entidades import ProductoNuevo

pytestmark = pytest.mark.asyncio


async def _esperar_replica(
    sesion_ro: AsyncSession, lsn: str, intentos: int = 50
) -> None:
    for _ in range(intentos):
        replicado = await sesion_ro.scalar(
            text("SELECT pg_last_wal_replay_lsn() >= CAST(:lsn AS pg_lsn)"),
            {"lsn": lsn},
        )
        if replicado:
            return
        await asyncio.sleep(0.1)
    raise AssertionError("La réplica no alcanzó el LSN de la escritura a tiempo")


async def test_la_replica_sirve_las_lecturas_tras_confirmar(
    sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    repositorio_rw = SQLAlchemyRepositorioProductos(sesion_rw)

    creado = await repositorio_rw.crear(ProductoNuevo(nombre="Agua mineral 1.5L"))
    await sesion_rw.commit()

    if not await sesion_ro.scalar(text("SELECT pg_is_in_recovery()")):
        pytest.skip("DATABASE_URL_RO apunta al primario; no hay réplica que probar")

    lsn = await sesion_rw.scalar(text("SELECT pg_current_wal_lsn()"))
    assert lsn is not None
    await _esperar_replica(sesion_ro, lsn)

    repositorio_ro = SQLAlchemyRepositorioProductos(sesion_ro)
    assert await repositorio_ro.obtener(creado.id) == creado
