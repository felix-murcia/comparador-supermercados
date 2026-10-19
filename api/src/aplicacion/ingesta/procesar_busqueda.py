"""Caso de uso: procesar un job de búsqueda.

Recorre las cadenas del job, lanza el pipeline de precio para cada una y va
actualizando el progreso (0-100) hasta cerrar el job como `completada` o
`fallida`.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from src.aplicacion.ingesta.buscar_producto import ResultadoBusqueda
from src.dominio.busquedas.entidades import Busqueda
from src.dominio.busquedas.estados import EstadoBusqueda
from src.dominio.ingesta.entidades import MetricaIngesta
from src.dominio.precios.estados import EstadoPrecio
from src.puertos.repositorios import RepositorioBusquedas, RepositorioMetricas

logger = logging.getLogger(__name__)

BuscarPrecio = Callable[[str, str], Awaitable[ResultadoBusqueda]]

MOTIVO_ERROR_WORKER = "error_worker"


class ProcesarBusqueda:
    """Ejecuta las cadenas de un job y actualiza su estado y su progreso."""

    def __init__(
        self,
        *,
        buscar: BuscarPrecio,
        repositorio_busquedas: RepositorioBusquedas,
        repositorio_metricas: RepositorioMetricas,
    ) -> None:
        self._buscar = buscar
        self._repositorio_busquedas = repositorio_busquedas
        self._repositorio_metricas = repositorio_metricas

    async def ejecutar(self, busqueda: Busqueda) -> EstadoBusqueda:
        """Procesa el job y devuelve su estado final."""
        cadenas = busqueda.cadenas
        total = max(len(cadenas), 1)
        guardados = 0

        for indice, cadena in enumerate(cadenas, start=1):
            if await self._procesar_cadena(busqueda.query, cadena):
                guardados += 1
            await self._repositorio_busquedas.actualizar_estado(
                busqueda.id, "en_progreso", int(indice * 100 / total)
            )

        estado: EstadoBusqueda = "completada" if guardados else "fallida"
        await self._repositorio_busquedas.actualizar_estado(
            busqueda.id, estado, 100, completado_en=datetime.now(UTC)
        )
        return estado

    async def _procesar_cadena(self, query: str, cadena: str) -> bool:
        try:
            resultado = await self._buscar(query, cadena)
        except Exception as error:  # noqa: BLE001 - una cadena no tumba el job
            logger.warning(
                "Fallo al procesar %s en %s: %s", query, cadena, type(error).__name__
            )
            await self._registrar(cadena, "rechazado", None, (MOTIVO_ERROR_WORKER,))
            return False

        await self._registrar(
            cadena,
            resultado.estado,
            resultado.producto_cadena_id,
            resultado.motivos,
        )
        if not resultado.guardado:
            logger.info(
                "Sin precio para %s en %s (%s)",
                query,
                cadena,
                ", ".join(resultado.motivos) or "sin motivos",
            )
        return resultado.guardado

    async def _registrar(
        self,
        cadena: str,
        estado: EstadoPrecio,
        producto_cadena_id: UUID | None,
        motivos: tuple[str, ...],
    ) -> None:
        await self._repositorio_metricas.registrar(
            MetricaIngesta(
                cadena=cadena,
                estado=estado,
                producto_cadena_id=producto_cadena_id,
                motivo=motivos[0] if motivos else None,
            )
        )
