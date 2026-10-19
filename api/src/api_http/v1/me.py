"""Endpoint `GET /v1/me`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRW
from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.dominio.usuarios.entidades import Usuario

router = APIRouter(prefix="/v1", tags=["usuarios"])


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
