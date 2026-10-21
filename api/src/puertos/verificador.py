"""Puerto del verificador determinista de precios.

Verifica un candidato del productor sin usar LLM: fetch de `url_fuente`,
comprobación del precio en el HTML, coherencia €/L vs. formato y desviación
respecto al último precio conocido.

El candidato puede incluir `precio_eur_anterior` (lo añade el caso de uso
cuando conoce el último precio persistido) para la regla de desviación.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple, Protocol, runtime_checkable

from src.dominio.precios.estados import EstadoPrecio
from src.puertos.productor import Candidato


class ResultadoVerificacion(NamedTuple):
    """Resultado de verificar un candidato.

    `precio` y `nombre` son los datos confirmados en la página del retailer,
    que es la fuente de verdad: el LLM puede equivocarse (lee precios de
    otros artículos en los resultados de búsqueda), así que el verificador
    puede corregirlos. Son `None` si el candidato no llegó a verificarse.
    """

    estado: EstadoPrecio
    motivos: list[str]
    precio: Decimal | None = None
    nombre: str | None = None


@runtime_checkable
class Verificador(Protocol):
    """Decide si un candidato es verificado, sospechoso o rechazado."""

    async def verificar(self, candidato: Candidato) -> ResultadoVerificacion: ...
