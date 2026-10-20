"""Tests del endpoint interno de métricas y de la lista blanca de admin."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import jwt as pyjwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.repositorio_metricas import (
    SQLAlchemyRepositorioMetricas,
)
from src.dominio.ingesta.entidades import MetricaIngesta
from src.dominio.usuarios.admin import es_admin
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


def _token(email: str) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    return pyjwt.encode(
        {
            "sub": f"authjs:google:{email}",
            "email": email,
            "name": "Admin",
            "provider": "google",
            "provider_id": email,
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


async def test_la_lista_blanca_reconoce_el_email() -> None:
    assert es_admin("Admin@Ejemplo.com", "otro@ejemplo.com, admin@ejemplo.com")
    assert not es_admin("admin@ejemplo.com", "")
    assert not es_admin("ajeno@ejemplo.com", "admin@ejemplo.com")


async def test_sin_ser_admin_responde_403(cliente: AsyncClient) -> None:
    respuesta = await cliente.get(
        "/v1/admin/metricas",
        headers={"Authorization": f"Bearer {_token('ajeno@ejemplo.com')}"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "NO_AUTORIZADO"


async def test_el_admin_ve_el_resumen(
    cliente: AsyncClient, sesion_rw: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "src.api_http.v1.admin.settings.admin_emails", "admin@ejemplo.com"
    )
    repositorio = SQLAlchemyRepositorioMetricas(sesion_rw)
    await repositorio.registrar(
        MetricaIngesta(cadena="dia", estado="verificado", motivo=None)
    )
    await repositorio.registrar(
        MetricaIngesta(cadena="dia", estado="sospechoso", motivo="desviacion_precio")
    )
    await sesion_rw.commit()

    respuesta = await cliente.get(
        "/v1/admin/metricas",
        headers={"Authorization": f"Bearer {_token('admin@ejemplo.com')}"},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 2
    assert cuerpo["verificado"] == 1
    assert cuerpo["sospechoso"] == 1
    assert cuerpo["motivos"] == [{"motivo": "desviacion_precio", "total": 1}]
    assert len(cuerpo["por_dia"]) == 1
    assert "email" not in respuesta.text
