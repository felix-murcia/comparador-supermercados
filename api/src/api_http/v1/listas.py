"""Endpoints de listas de la compra (`/v1/listas`).

Solo el propietario puede ver ni modificar sus listas; el borrado de una lista
arrastra sus items por la FK `ON DELETE CASCADE`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRW
from src.api_http.errores import ErrorAPI
from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.dominio.listas.entidades import ItemLista, Lista
from src.dominio.usuarios.entidades import Usuario
from src.dominio.usuarios.errores import UsuarioNoAutorizadoError

router = APIRouter(prefix="/v1/listas", tags=["listas"])


class ListaRequest(BaseModel):
    """Nombre de la lista."""

    nombre: str = Field(min_length=1, max_length=120)


class ItemResponse(BaseModel):
    """Producto dentro de la lista."""

    id: UUID
    producto_id: UUID
    cantidad: int
    cadena_compra_id: UUID | None
    precio_snapshot: Decimal | None
    creado_en: datetime


class ListaResponse(BaseModel):
    """Lista de la compra."""

    id: UUID
    nombre: str
    creado_en: datetime
    items: list[ItemResponse] = Field(default_factory=list)

    @classmethod
    def desde(cls, lista: Lista, items: list[ItemLista] | None = None) -> ListaResponse:
        return cls(
            id=lista.id,
            nombre=lista.nombre,
            creado_en=lista.creado_en,
            items=[
                ItemResponse(
                    id=item.id,
                    producto_id=item.producto_id,
                    cantidad=item.cantidad,
                    cadena_compra_id=item.cadena_compra_id,
                    precio_snapshot=item.precio_snapshot,
                    creado_en=item.creado_en,
                )
                for item in (items or [])
            ],
        )


async def _usuario_para_escritura(
    identidad: Identidad,
    repositorio: SQLAlchemyRepositorioUsuarios,
) -> Usuario:
    """Perfil del usuario, creándolo si es su primera acción (upsert)."""
    return await ObtenerPerfil(repositorio).ejecutar(identidad)


async def _usuario_para_lectura(
    identidad: Identidad,
    repositorio: SQLAlchemyRepositorioUsuarios,
) -> Usuario | None:
    """Perfil del usuario; `None` si todavía no existe."""
    return await repositorio.obtener_por_provider(
        identidad.provider, identidad.provider_id
    )


async def _lista_del_usuario(
    repositorio: SQLAlchemyRepositorioListas,
    lista_id: UUID,
    usuario_id: UUID,
) -> Lista:
    lista = await repositorio.obtener(lista_id)
    if lista is None:
        raise ErrorAPI(404, "LISTA_NO_ENCONTRADA", "La lista no existe")
    if lista.usuario_id != usuario_id:
        raise UsuarioNoAutorizadoError("La lista pertenece a otro usuario")
    return lista


@router.post("", response_model=ListaResponse, status_code=status.HTTP_201_CREATED)
async def crear_lista(
    body: ListaRequest,
    identidad: Identidad,
    sesion: SessionRW,
) -> ListaResponse:
    """Crea una lista para el usuario autenticado."""
    usuario = await _usuario_para_escritura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    lista = await SQLAlchemyRepositorioListas(sesion).crear(usuario.id, body.nombre)
    return ListaResponse.desde(lista)


@router.get("", response_model=list[ListaResponse])
async def listar_listas(
    identidad: Identidad,
    sesion: SessionRW,
) -> list[ListaResponse]:
    """Listas del usuario autenticado."""
    usuario = await _usuario_para_lectura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    if usuario is None:
        return []
    listas = await SQLAlchemyRepositorioListas(sesion).listar_por_usuario(usuario.id)
    return [ListaResponse.desde(lista) for lista in listas]


@router.get("/{lista_id}", response_model=ListaResponse)
async def obtener_lista(
    lista_id: UUID,
    identidad: Identidad,
    sesion: SessionRW,
) -> ListaResponse:
    """Detalle de una lista con sus items."""
    usuario = await _usuario_para_lectura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    if usuario is None:
        raise UsuarioNoAutorizadoError("El usuario no tiene perfil")
    repositorio = SQLAlchemyRepositorioListas(sesion)
    lista = await _lista_del_usuario(repositorio, lista_id, usuario.id)
    items = await repositorio.obtener_items(lista.id)
    return ListaResponse.desde(lista, items)


@router.patch("/{lista_id}", response_model=ListaResponse)
async def renombrar_lista(
    lista_id: UUID,
    body: ListaRequest,
    identidad: Identidad,
    sesion: SessionRW,
) -> ListaResponse:
    """Cambia el nombre de una lista."""
    usuario = await _usuario_para_escritura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    repositorio = SQLAlchemyRepositorioListas(sesion)
    await _lista_del_usuario(repositorio, lista_id, usuario.id)
    lista = await repositorio.renombrar(lista_id, body.nombre)
    if lista is None:
        raise ErrorAPI(404, "LISTA_NO_ENCONTRADA", "La lista no existe")
    return ListaResponse.desde(lista)


@router.delete("/{lista_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_lista(
    lista_id: UUID,
    identidad: Identidad,
    sesion: SessionRW,
) -> Response:
    """Borra una lista y sus items."""
    usuario = await _usuario_para_escritura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    repositorio = SQLAlchemyRepositorioListas(sesion)
    await _lista_del_usuario(repositorio, lista_id, usuario.id)
    await repositorio.eliminar(lista_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
