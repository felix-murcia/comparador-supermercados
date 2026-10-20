"""Endpoints de perfil: `GET /v1/me` y `PATCH /v1/me`."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.adaptadores.cache.redis_cache import get_cache
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRW
from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.dominio.usuarios.entidades import Usuario
from src.dominio.usuarios.provincias import PROVINCIAS, validar_provincia

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["usuarios"])

PREFIJO_CACHE = "v1:"


class PerfilResponse(BaseModel):
    """Perfil público del usuario."""

    id: UUID
    email: str
    nombre: str | None
    provincia: str | None
    avatar_url: str | None

    @classmethod
    def desde(cls, usuario: Usuario) -> PerfilResponse:
        return cls(
            id=usuario.id,
            email=usuario.email,
            nombre=usuario.nombre,
            provincia=usuario.provincia,
            avatar_url=usuario.avatar_url,
        )


class ActualizarPerfilRequest(BaseModel):
    """Datos que se pueden cambiar del perfil."""

    nombre: str | None = None
    provincia: str | None = None


class ProvinciasResponse(BaseModel):
    """Catálogo de provincias españolas."""

    provincias: list[str]


@router.get("/me", response_model=PerfilResponse)
async def leer_perfil(
    request: Request,
    identidad: Identidad,
    sesion: SessionRW,
) -> PerfilResponse:
    usuario = await ObtenerPerfil(SQLAlchemyRepositorioUsuarios(sesion)).ejecutar(
        identidad
    )
    request.state.usuario_id = str(usuario.id)
    return PerfilResponse.desde(usuario)


@router.patch("/me", response_model=PerfilResponse)
async def actualizar_perfil(
    request: Request,
    body: ActualizarPerfilRequest,
    identidad: Identidad,
    sesion: SessionRW,
) -> PerfilResponse:
    """Actualiza nombre y provincia; la provincia se valida contra el catálogo."""
    repositorio = SQLAlchemyRepositorioUsuarios(sesion)
    usuario = await ObtenerPerfil(repositorio).ejecutar(identidad)

    provincia = (
        validar_provincia(body.provincia).nombre if body.provincia is not None else None
    )

    actualizado = await repositorio.actualizar(usuario.id, body.nombre, provincia)
    request.state.usuario_id = str(actualizado.id)

    if provincia is not None and provincia != usuario.provincia:
        await _invalidar_cache()

    return PerfilResponse.desde(actualizado)


async def _invalidar_cache() -> None:
    """Los resultados cacheados dependen de la provincia; se limpian."""
    try:
        cache = get_cache()
    except RuntimeError:
        logger.info("Sin Redis configurado: no se invalida la caché")
        return
    await cache.invalidar_prefijo(PREFIJO_CACHE)


@router.get("/provincias", response_model=ProvinciasResponse)
async def listar_provincias() -> ProvinciasResponse:
    """Catálogo de provincias españolas para el formulario de perfil."""
    return ProvinciasResponse(provincias=list(PROVINCIAS))
