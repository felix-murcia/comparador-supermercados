"""Entidades de métricas de ingesta."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from src.dominio.precios.estados import EstadoPrecio


@dataclass(frozen=True)
class MetricaIngesta:
    """Una ingesta registrada: estado del precio y motivo, si lo hubo."""

    cadena: str
    estado: EstadoPrecio
    producto_cadena_id: UUID | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class MetricasIngesta:
    """Resumen de la ingesta: reparto por estado y motivos más frecuentes."""

    total: int
    verificado: int
    sospechoso: int
    rechazado: int
    motivos: tuple[tuple[str, int], ...] = ()

    def porcentaje(self, cantidad: int) -> float:
        """Porcentaje de un estado sobre el total (0 si no hay datos)."""
        if self.total == 0:
            return 0.0
        return float(
            (Decimal(cantidad) * Decimal(100) / Decimal(self.total)).quantize(
                Decimal("0.01")
            )
        )

    @property
    def porcentaje_verificado(self) -> float:
        return self.porcentaje(self.verificado)

    @property
    def porcentaje_sospechoso(self) -> float:
        return self.porcentaje(self.sospechoso)

    @property
    def porcentaje_rechazado(self) -> float:
        return self.porcentaje(self.rechazado)


@dataclass(frozen=True)
class MetricaDia:
    """Reparto por estado de la ingesta en un día."""

    dia: date
    verificado: int
    sospechoso: int
    rechazado: int
