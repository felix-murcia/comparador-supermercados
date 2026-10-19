"""Integración de `GET /v1/busquedas/{id}` contra Postgres real."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any
from datetime import UTC, datetime
from uuid import UUID, uuid4

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.dominio.busquedas.entidades import BusquedaNueva
from src.dominio.usuarios.entidades import IdentidadOAuth
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


def _token(provider_id: str) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    return pyjwt.encode(
        {
            "sub": f"authjs:google:{provider_id}",
            "email": f"{provider_id}@example.test",
            "name": "Ana",
            "provider": "google",
            "provider_id": provider_id,
            "iat": ahora,
            "exp": ahora + 300,
        },
        _SECRETO,
        algorithm="HS256",
    )


async def _lsn(sesion: AsyncSession) -> Any:
    lsn = await sesion.scalar(text("SELECT pg_current_wal_lsn()"))
    assert lsn is not None
    return lsn


async def _esperar_replica(
    sesion_ro: AsyncSession, lsn: str, intentos: int = 100
) -> None:
    import asyncio

    for _ in range(intentos):
        replicado = await sesion_ro.scalar(
            text("SELECT pg_last_wal_replay_lsn() >= CAST(:lsn AS pg_lsn)"),
            {"lsn": lsn},
        )
        if replicado:
            return
        await asyncio.sleep(0.1)
    raise AssertionError("La réplica no alcanzó el LSN de la escritura a tiempo")


@pytest_asyncio.fixture
async def cliente() -> AsyncIterator[AsyncClient]:
    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente


async def _crear_usuario(
    sesion: AsyncSession, sesion_ro: AsyncSession, provider_id: str
) -> UUID:
    usuario = await SQLAlchemyRepositorioUsuarios(sesion).upsert(
        IdentidadOAuth(
            provider="google",
            provider_id=provider_id,
            email=f"{provider_id}@example.test",
            nombre="Ana",
        )
    )
    await sesion.commit()
    lsn = await sesion.scalar(text("SELECT pg_current_wal_lsn()"))
    assert lsn is not None
    await _esperar_replica(sesion_ro, lsn)
    return usuario.id


async def test_devuelve_el_estado_del_job(
    cliente: AsyncClient, sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    provider_id = f"estado-{uuid4().hex[:8]}"
    usuario_id = await _crear_usuario(sesion_rw, sesion_ro, provider_id)
    job = await SQLAlchemyRepositorioBusquedas(sesion_rw).crear(
        BusquedaNueva(
            query="leche",
            cadenas=("dia",),
            cache_key="v1:estado",
            usuario_id=usuario_id,
        )
    )
    await sesion_rw.commit()

    respuesta = await cliente.get(
        f"/v1/busquedas/{job.id}",
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["progreso"] == 0
    assert cuerpo["resultados_parciales"] == []
    assert cuerpo["completado_en"] is None


async def test_refleja_la_transicion_de_estados(
    cliente: AsyncClient, sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    provider_id = f"transicion-{uuid4().hex[:8]}"
    usuario_id = await _crear_usuario(sesion_rw, sesion_ro, provider_id)
    repositorio = SQLAlchemyRepositorioBusquedas(sesion_rw)
    job = await repositorio.crear(
        BusquedaNueva(
            query="leche",
            cadenas=("dia",),
            cache_key="v1:transicion",
            usuario_id=usuario_id,
        )
    )
    await sesion_rw.commit()

    await repositorio.actualizar_estado(job.id, "en_progreso", 50)
    await sesion_rw.commit()
    await _esperar_replica(sesion_ro, await _lsn(sesion_rw))

    en_progreso = await cliente.get(
        f"/v1/busquedas/{job.id}",
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )
    assert en_progreso.status_code == 200
    assert en_progreso.json()["estado"] == "en_progreso"
    assert en_progreso.json()["progreso"] == 50

    await repositorio.actualizar_estado(
        job.id, "completada", 100, completado_en=datetime.now(UTC)
    )
    await sesion_rw.commit()
    await _esperar_replica(sesion_ro, await _lsn(sesion_rw))

    completada = await cliente.get(
        f"/v1/busquedas/{job.id}",
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )
    assert completada.status_code == 200
    assert completada.json()["estado"] == "completada"
    assert completada.json()["progreso"] == 100
    assert completada.json()["completado_en"] is not None


async def test_otro_usuario_no_puede_ver_el_job(
    cliente: AsyncClient, sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    duena_id = f"dueno-{uuid4().hex[:8]}"
    intruso_id = f"intruso-{uuid4().hex[:8]}"
    usuario_id = await _crear_usuario(sesion_rw, sesion_ro, duena_id)
    await _crear_usuario(sesion_rw, sesion_ro, intruso_id)
    job = await SQLAlchemyRepositorioBusquedas(sesion_rw).crear(
        BusquedaNueva(
            query="leche",
            cadenas=("dia",),
            cache_key="v1:dueno",
            usuario_id=usuario_id,
        )
    )
    await sesion_rw.commit()
    await _esperar_replica(sesion_ro, await _lsn(sesion_rw))

    respuesta = await cliente.get(
        f"/v1/busquedas/{job.id}",
        headers={"Authorization": f"Bearer {_token(intruso_id)}"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "BUSQUEDA_NO_AUTORIZADA"


async def test_job_inexistente_devuelve_404(
    cliente: AsyncClient, sesion_rw: AsyncSession, sesion_ro: AsyncSession
) -> None:
    provider_id = f"inexistente-{uuid4().hex[:8]}"
    await _crear_usuario(sesion_rw, sesion_ro, provider_id)

    respuesta = await cliente.get(
        f"/v1/busquedas/{uuid4()}",
        headers={"Authorization": f"Bearer {_token(provider_id)}"},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "BUSQUEDA_NO_ENCONTRADA"


async def test_sin_jwt_devuelve_401(cliente: AsyncClient) -> None:
    respuesta = await cliente.get(f"/v1/busquedas/{uuid4()}")

    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "NO_AUTENTICADO"
