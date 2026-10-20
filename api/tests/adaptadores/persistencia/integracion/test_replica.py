"""Integración de la réplica de Postgres (streaming replication).

Verifica que una escritura en el primario llega a la réplica con un lag
inferior a un segundo.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_URL_RO = "DATABASE_URL_RO"
_LAG_MAXIMO_SEGUNDOS = 1.0

pytestmark = pytest.mark.asyncio


async def test_la_replica_esta_en_streaming(sesion_rw: AsyncSession) -> None:
    en_replica = await sesion_rw.scalar(text("SELECT pg_is_in_recovery()"))
    if en_replica:
        pytest.skip("DATABASE_URL_RO apunta al primario; no hay réplica que comprobar")

    filas = (
        await sesion_rw.execute(
            text(
                "SELECT state, sync_state FROM pg_stat_replication "
                "WHERE application_name IS NOT NULL OR state = 'streaming'"
            )
        )
    ).all()

    assert filas, "No hay ninguna réplica en streaming"
    for estado, sync_state in filas:
        assert estado == "streaming"
        assert sync_state in ("async", "sync", "quorum")


async def test_una_escritura_llega_a_la_replica_con_lag_menor_de_un_segundo(
    sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    en_replica = await sesion_ro.scalar(text("SELECT pg_is_in_recovery()"))
    if not en_replica:
        pytest.skip("DATABASE_URL_RO no apunta a una réplica")

    inicio = time.monotonic()
    await sesion_rw.execute(
        text(
            "INSERT INTO productos (nombre, marca) "
            "VALUES ('Producto de prueba de réplica', 'Prueba')"
        )
    )
    await sesion_rw.commit()

    visible = False
    while time.monotonic() - inicio < _LAG_MAXIMO_SEGUNDOS:
        total = await sesion_ro.scalar(
            text("SELECT count(*) FROM productos WHERE nombre = :nombre"),
            {"nombre": "Producto de prueba de réplica"},
        )
        if total:
            visible = True
            break
        await asyncio.sleep(0.05)

    lag = time.monotonic() - inicio
    assert visible, f"La réplica no vio la escritura en {_LAG_MAXIMO_SEGUNDOS} s"
    assert lag < _LAG_MAXIMO_SEGUNDOS
