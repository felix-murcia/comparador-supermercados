"""Puerto de la cola de jobs de ingesta.

En el MVP la cola es la propia tabla `busquedas` (ADR-007): el worker la
reclama con `FOR UPDATE SKIP LOCKED`, de modo que dos workers nunca procesan
el mismo job.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dominio.busquedas.entidades import Busqueda


@runtime_checkable
class ColaJobs(Protocol):
    """Reclama jobs pendientes para procesarlos sin duplicar trabajo."""

    async def reclamar(self, timeout_minutos: int) -> Busqueda | None: ...
