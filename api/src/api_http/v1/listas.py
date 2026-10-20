"""Endpoints de listas de la compra (`/v1/listas`).

Solo el propietario puede ver ni modificar sus listas; el borrado de una lista
arrastra sus items por la FK `ON DELETE CASCADE`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel, Field

from src.adaptadores.cache.redis_cache import get_cache
from src.adaptadores.persistencia.repositorio_cadenas import (
    SQLAlchemyRepositorioCadenas,
)
from src.adaptadores.persistencia.repositorio_listas import (
    SQLAlchemyRepositorioListas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_productos import (
    SQLAlchemyRepositorioProductos,
)
from src.adaptadores.persistencia.repositorio_productos_cadenas import (
    SQLAlchemyRepositorioProductosCadenas,
)
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRO, SessionRW
from src.api_http.errores import ErrorAPI
from src.aplicacion.listas.calcular_ahorro_lista import CalcularAhorroLista
from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.dominio.listas.ahorro import ResumenAhorro
from src.dominio.listas.entidades import (
    ItemLista,
    ItemListaDetalle,
    ItemListaNuevo,
    Lista,
)
from src.dominio.productos.errores import ProductoNoEncontradoError
from src.dominio.usuarios.entidades import Usuario
from src.dominio.usuarios.errores import UsuarioNoAutorizadoError
from src.puertos.cache import Cache

router = APIRouter(prefix="/v1/listas", tags=["listas"])

TTL_RESUMEN_SEGUNDOS = 60
PREFIJO_RESUMEN = "v1:resumen"


class ResumenCadenaResponse(BaseModel):
    """Coste de la lista en una cadena y el % A frente a la más cara."""

    cadena: str
    coste: Decimal
    porcentaje_a: Decimal | None = None
    productos_no_disponibles: list[str] = Field(default_factory=list)


class ResumenListaResponse(BaseModel):
    """Resumen del ahorro de la lista."""

    coste_total: Decimal
    por_cadena: list[ResumenCadenaResponse] = Field(default_factory=list)
    porcentaje_c: Decimal | None = None
    coste_optimo: Decimal
    coste_mixta_real: Decimal
    avisos: list[str] = Field(default_factory=list)

    @classmethod
    def desde(cls, resumen: ResumenAhorro) -> ResumenListaResponse:
        return cls(
            coste_total=resumen.coste_total,
            por_cadena=[
                ResumenCadenaResponse(
                    cadena=coste.cadena,
                    coste=coste.coste,
                    porcentaje_a=coste.porcentaje_a,
                    productos_no_disponibles=list(coste.productos_no_disponibles),
                )
                for coste in resumen.por_cadena
            ],
            porcentaje_c=resumen.porcentaje_c,
            coste_optimo=resumen.coste_optimo,
            coste_mixta_real=resumen.coste_mixta_real,
            avisos=list(resumen.avisos),
        )


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
    producto_nombre: str | None = None
    producto_marca: str | None = None

    @classmethod
    def desde(cls, item: ItemLista) -> ItemResponse:
        return cls(
            id=item.id,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            cadena_compra_id=item.cadena_compra_id,
            precio_snapshot=item.precio_snapshot,
            creado_en=item.creado_en,
        )

    @classmethod
    def desde_detalle(cls, detalle: ItemListaDetalle) -> ItemResponse:
        return cls(
            id=detalle.item.id,
            producto_id=detalle.item.producto_id,
            cantidad=detalle.item.cantidad,
            cadena_compra_id=detalle.item.cadena_compra_id,
            precio_snapshot=detalle.item.precio_snapshot,
            creado_en=detalle.item.creado_en,
            producto_nombre=detalle.producto_nombre,
            producto_marca=detalle.producto_marca,
        )


class ItemRequest(BaseModel):
    """Producto que se añade a la lista."""

    producto_id: UUID
    cantidad: int = Field(default=1, ge=1, le=999)
    cadena_compra_id: UUID | None = None


class ActualizarItemRequest(BaseModel):
    """Nueva cantidad del item."""

    cantidad: int = Field(ge=1, le=999)


class ListaResponse(BaseModel):
    """Lista de la compra."""

    id: UUID
    nombre: str
    creado_en: datetime
    items: list[ItemResponse] = Field(default_factory=list)

    @classmethod
    def desde(
        cls, lista: Lista, items: list[ItemListaDetalle] | None = None
    ) -> ListaResponse:
        return cls(
            id=lista.id,
            nombre=lista.nombre,
            creado_en=lista.creado_en,
            items=[ItemResponse.desde_detalle(item) for item in (items or [])],
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
    items = await repositorio.obtener_items_detallados(lista.id)
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


@router.post(
    "/{lista_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_item(
    lista_id: UUID,
    body: ItemRequest,
    identidad: Identidad,
    sesion: SessionRW,
) -> ItemResponse:
    """Añade un producto a la lista y guarda el precio del momento."""
    usuario = await _usuario_para_escritura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    repositorio = SQLAlchemyRepositorioListas(sesion)
    lista = await _lista_del_usuario(repositorio, lista_id, usuario.id)

    producto = await SQLAlchemyRepositorioProductos(sesion).obtener(body.producto_id)
    if producto is None:
        raise ProductoNoEncontradoError(body.producto_id)

    precio = None
    if body.cadena_compra_id is not None:
        # `cadena_compra_id` es la cadena donde compra el usuario; el precio
        # del momento es el de ese producto en esa cadena.
        producto_cadena_id = await SQLAlchemyRepositorioProductosCadenas(
            sesion
        ).obtener_por_producto_y_cadena(producto.id, body.cadena_compra_id)
        if producto_cadena_id is not None:
            precio = await SQLAlchemyRepositorioPrecios(sesion).ultimo_verificado(
                producto_cadena_id
            )

    item = await repositorio.agregar_item(
        ItemListaNuevo(
            lista_id=lista.id,
            producto_id=producto.id,
            cantidad=body.cantidad,
            cadena_compra_id=body.cadena_compra_id,
            precio_snapshot=precio.importe_eur if precio is not None else None,
        )
    )
    return ItemResponse.desde(item)


@router.patch("/{lista_id}/items/{item_id}", response_model=ItemResponse)
async def actualizar_item(
    lista_id: UUID,
    item_id: UUID,
    body: ActualizarItemRequest,
    identidad: Identidad,
    sesion: SessionRW,
) -> ItemResponse:
    """Cambia la cantidad de un item de la lista."""
    usuario = await _usuario_para_escritura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    repositorio = SQLAlchemyRepositorioListas(sesion)
    lista = await _lista_del_usuario(repositorio, lista_id, usuario.id)

    item = await repositorio.obtener_item(item_id)
    if item is None or item.lista_id != lista.id:
        raise ErrorAPI(404, "ITEM_NO_ENCONTRADO", "El item no está en la lista")

    actualizado = await repositorio.actualizar_item(item_id, cantidad=body.cantidad)
    if actualizado is None:
        raise ErrorAPI(404, "ITEM_NO_ENCONTRADO", "El item no está en la lista")
    return ItemResponse.desde(actualizado)


@router.delete("/{lista_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_item(
    lista_id: UUID,
    item_id: UUID,
    identidad: Identidad,
    sesion: SessionRW,
) -> Response:
    """Quita un item de la lista."""
    usuario = await _usuario_para_escritura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    repositorio = SQLAlchemyRepositorioListas(sesion)
    lista = await _lista_del_usuario(repositorio, lista_id, usuario.id)

    item = await repositorio.obtener_item(item_id)
    if item is None or item.lista_id != lista.id:
        raise ErrorAPI(404, "ITEM_NO_ENCONTRADO", "El item no está en la lista")

    await repositorio.eliminar_item(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _cache_optional() -> Cache | None:
    """Caché de resúmenes; sin Redis el endpoint funciona igual."""
    try:
        return get_cache()
    except RuntimeError:
        return None


@router.get("/{lista_id}/resumen", response_model=ResumenListaResponse)
async def resumen_lista(
    lista_id: UUID,
    identidad: Identidad,
    sesion: SessionRO,
    cadenas: Annotated[
        list[str], Query(default_factory=list, description="Cadenas a comparar")
    ],
) -> ResumenListaResponse:
    """Coste total, % A por cadena, % C y avisos del ahorro de la lista."""
    usuario = await _usuario_para_lectura(
        identidad, SQLAlchemyRepositorioUsuarios(sesion)
    )
    if usuario is None:
        raise UsuarioNoAutorizadoError("El usuario no tiene perfil")

    repositorio = SQLAlchemyRepositorioListas(sesion)
    lista = await _lista_del_usuario(repositorio, lista_id, usuario.id)

    clave = f"{PREFIJO_RESUMEN}:{lista_id}:{','.join(sorted(cadenas))}"
    cache = _cache_optional()
    if cache is not None:
        cached = await cache.get(clave)
        if cached is not None:
            return ResumenListaResponse.model_validate(cached)

    caso = CalcularAhorroLista(
        repositorio_listas=repositorio,
        repositorio_precios=SQLAlchemyRepositorioPrecios(sesion),
        repositorio_cadenas=SQLAlchemyRepositorioCadenas(sesion),
    )
    resumen = await caso.ejecutar(lista.id, cadenas)
    respuesta = ResumenListaResponse.desde(resumen)

    if cache is not None:
        await cache.set(clave, respuesta.model_dump(mode="json"), TTL_RESUMEN_SEGUNDOS)

    return respuesta
