"""Endpoint `POST /v1/busquedas`.

Calcula la clave de caché de la búsqueda: si el resultado está en caché se
devuelve al momento; si no, se encola el job que procesará el worker.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from src.adaptadores.cache.redis_cache import get_cache
from src.adaptadores.cache.redis_limitador import get_limitador
from src.adaptadores.persistencia.repositorio_busquedas import (
    SQLAlchemyRepositorioBusquedas,
)
from src.adaptadores.persistencia.repositorio_precios import (
    SQLAlchemyRepositorioPrecios,
)
from src.adaptadores.persistencia.repositorio_usuarios import (
    SQLAlchemyRepositorioUsuarios,
)
from src.api_http.autenticacion import Identidad
from src.api_http.dependencias import SessionRO, SessionRW
from src.api_http.errores import ErrorAPI
from src.aplicacion.busquedas.crear_busqueda import CrearBusqueda
from src.aplicacion.usuarios.obtener_perfil import ObtenerPerfil
from src.config import settings
from src.dominio.busquedas.entidades import PeticionBusqueda
from src.dominio.busquedas.estados import EstadoBusqueda
from src.dominio.precios.entidades import FiltrosComparacion, ResultadoComparacion
from src.dominio.precios.estados import ORDEN_POR_DEFECTO, Orden
from src.dominio.usuarios.errores import UsuarioNoAutorizadoError

router = APIRouter(prefix="/v1", tags=["búsquedas"])

RESULTADOS_PARCIALES_MAX = 50


def _resultado_json(resultado: ResultadoComparacion) -> dict[str, Any]:
    """Resultado en forma JSON (precios como texto para no perder precisión)."""
    return {
        "posicion": resultado.posicion,
        "producto_id": str(resultado.producto_id),
        "producto_cadena_id": str(resultado.producto_cadena_id),
        "nombre": resultado.nombre,
        "marca": resultado.marca,
        "formato": resultado.formato,
        "categoria": resultado.categoria,
        "ean": resultado.ean,
        "cadena": resultado.cadena,
        "precio_eur": str(resultado.precio_eur),
        "precio_por_litro_kg": (
            str(resultado.precio_por_litro_kg)
            if resultado.precio_por_litro_kg is not None
            else None
        ),
        "ambito": resultado.ambito,
        "provincia": resultado.provincia,
    }


class BusquedaRequest(BaseModel):
    """Body de una búsqueda de precios."""

    query: str = Field(min_length=1)
    cadenas: list[str] = Field(default_factory=list)
    orden: Orden = ORDEN_POR_DEFECTO
    filtros: dict[str, str] = Field(default_factory=dict)
    provincia: str | None = None


class BusquedaResponse(BaseModel):
    """Acierto de caché o job encolado."""

    job_id: UUID | None
    cache_hit: bool
    resultados: list[dict[str, Any]] = Field(default_factory=list)


class EstadoBusquedaResponse(BaseModel):
    """Estado de un job de búsqueda y los resultados parciales."""

    estado: EstadoBusqueda
    progreso: int
    resultados_parciales: list[dict[str, Any]] = Field(default_factory=list)
    completado_en: datetime | None = None


async def get_crear_busqueda(sesion: SessionRW) -> CrearBusqueda:
    """Caso de uso con la caché, el limitador y el repositorio de búsquedas."""
    return CrearBusqueda(
        repositorio_busquedas=SQLAlchemyRepositorioBusquedas(sesion),
        cache=get_cache(),
        limitador=get_limitador(),
        limite_por_minuto=settings.rate_limit_busquedas_por_minuto,
    )


@router.post("/busquedas", response_model=BusquedaResponse)
async def crear_busqueda(
    request: Request,
    body: BusquedaRequest,
    identidad: Identidad,
    sesion: SessionRW,
    caso: Annotated[CrearBusqueda, Depends(get_crear_busqueda)],
) -> BusquedaResponse:
    """Encola la búsqueda o devuelve el resultado cacheado."""
    usuario = await ObtenerPerfil(SQLAlchemyRepositorioUsuarios(sesion)).ejecutar(
        identidad
    )
    # Marca el sticky read: el polling siguiente lee del primario y ve el job.
    request.state.usuario_id = str(usuario.id)

    resultado = await caso.ejecutar(
        PeticionBusqueda(
            query=body.query,
            cadenas=tuple(body.cadenas),
            orden=body.orden,
            filtros=body.filtros,
            provincia=body.provincia,
        ),
        usuario.id,
        f"{usuario.provider}:{usuario.provider_id}",
    )

    return BusquedaResponse(
        job_id=resultado.job_id,
        cache_hit=resultado.cache_hit,
        resultados=list(resultado.resultados),
    )


@router.get("/busquedas/{busqueda_id}", response_model=EstadoBusquedaResponse)
async def estado_busqueda(
    busqueda_id: UUID,
    identidad: Identidad,
    sesion: SessionRO,
) -> EstadoBusquedaResponse:
    """Estado y progreso del job; solo su propietario puede consultarlo."""
    usuario = await SQLAlchemyRepositorioUsuarios(sesion).obtener_por_provider(
        identidad.provider, identidad.provider_id
    )
    if usuario is None:
        raise UsuarioNoAutorizadoError("El job no pertenece a este usuario")

    job = await SQLAlchemyRepositorioBusquedas(sesion).obtener(busqueda_id)
    if job is None:
        raise ErrorAPI(404, "BUSQUEDA_NO_ENCONTRADA", "El job no existe")
    if job.usuario_id != usuario.id:
        raise UsuarioNoAutorizadoError("El job no pertenece a este usuario")

    resultados = await SQLAlchemyRepositorioPrecios(sesion).buscar_comparativa(
        FiltrosComparacion(
            query=job.query,
            cadenas=job.cadenas,
            provincia=job.provincia,
            limite=RESULTADOS_PARCIALES_MAX,
        )
    )

    return EstadoBusquedaResponse(
        estado=job.estado,
        progreso=job.progreso,
        resultados_parciales=[_resultado_json(r) for r in resultados],
        completado_en=job.completado_en,
    )
