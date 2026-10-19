"""Caso de uso: encolar una búsqueda de precios.

Aplica el límite de peticiones, calcula la clave de caché y, si no hay
acierto, encola el job que procesará el worker.
"""

from __future__ import annotations

import logging
from uuid import UUID

from src.dominio.busquedas.entidades import (
    BusquedaNueva,
    PeticionBusqueda,
    ResultadoCrearBusqueda,
)
from src.dominio.busquedas.reglas import calcular_cache_key
from src.puertos.cache import Cache
from src.puertos.limite import Limitador
from src.puertos.repositorios import RepositorioBusquedas

logger = logging.getLogger(__name__)

VENTANA_SEGUNDOS = 60
LIMITE_POR_DEFECTO = 10


class CrearBusqueda:
    """Devuelve el resultado en caché o encola una búsqueda nueva."""

    def __init__(
        self,
        *,
        repositorio_busquedas: RepositorioBusquedas,
        cache: Cache,
        limitador: Limitador,
        limite_por_minuto: int = LIMITE_POR_DEFECTO,
    ) -> None:
        self._repositorio_busquedas = repositorio_busquedas
        self._cache = cache
        self._limitador = limitador
        self._limite_por_minuto = limite_por_minuto

    async def ejecutar(
        self,
        peticion: PeticionBusqueda,
        usuario_id: UUID | None,
        clave_limite: str,
    ) -> ResultadoCrearBusqueda:
        """Comprueba el límite, la caché y encola el job si no hay acierto."""
        await self._limitador.comprobar(
            clave_limite, self._limite_por_minuto, VENTANA_SEGUNDOS
        )

        cache_key = calcular_cache_key(
            peticion.query,
            peticion.cadenas,
            peticion.orden,
            peticion.filtros,
            peticion.provincia,
        )

        cached = await self._cache.get(cache_key)
        if cached is not None:
            resultados = cached.get("resultados")
            return ResultadoCrearBusqueda(
                job_id=None,
                cache_hit=True,
                resultados=tuple(resultados) if isinstance(resultados, list) else (),
            )

        busqueda = await self._repositorio_busquedas.crear(
            BusquedaNueva(
                query=peticion.query,
                cadenas=peticion.cadenas,
                cache_key=cache_key,
                usuario_id=usuario_id,
                provincia=peticion.provincia,
            )
        )
        logger.info("Búsqueda encolada %s: %s", busqueda.id, peticion.query)
        return ResultadoCrearBusqueda(job_id=busqueda.id, cache_hit=False)
