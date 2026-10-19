"""Integración del endpoint interno de métricas de ingesta."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_metricas import (
    SQLAlchemyRepositorioMetricas,
)
from src.dominio.ingesta.entidades import MetricaIngesta
from src.main import app

_URL_RW = os.getenv("DATABASE_URL_RW")
_SECRETO = os.getenv("NEXTAUTH_SECRET")

if not _URL_RW or not _SECRETO:
    pytest.skip(
        "Requiere DATABASE_URL_RW y NEXTAUTH_SECRET para la integración",
        allow_module_level=True,
    )

assert _SECRETO is not None

pytestmark = pytest.mark.asyncio


def _token() -> str:
    ahora = int(datetime.now(UTC).timestamp())
    return pyjwt.encode(
        {
            "sub": "authjs:google:123",
            "email": "ana@example.test",
            "provider": "google",
            "provider_id": "123",
            "iat": ahora,
            "exp": ahora + 300,
        },
        _SECRETO,
        algorithm="HS256",
    )


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


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


async def test_requiere_sesion(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/v1/_metrics/ingesta")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"


async def test_devuelve_el_resumen_de_la_ingesta(
    cliente: AsyncClient, sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    repositorio = SQLAlchemyRepositorioMetricas(sesion_rw)
    await repositorio.registrar(MetricaIngesta(cadena="dia", estado="verificado"))
    await repositorio.registrar(
        MetricaIngesta(cadena="dia", estado="sospechoso", motivo="desviacion_precio")
    )
    await sesion_rw.commit()

    lsn = await sesion_rw.scalar(text("SELECT pg_current_wal_lsn()"))
    assert lsn is not None
    await _esperar_replica(sesion_ro, lsn)

    respuesta = await cliente.get(
        "/v1/_metrics/ingesta", headers={"Authorization": f"Bearer {_token()}"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 2
    assert cuerpo["verificado"] == 1
    assert cuerpo["sospechoso"] == 1
    assert cuerpo["rechazado"] == 0
    assert cuerpo["porcentaje_verificado"] == 50.0
    assert cuerpo["motivos"] == [{"motivo": "desviacion_precio", "total": 1}]
