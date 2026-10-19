"""Puerto del verificador determinista de precios.

Verifica un candidato del productor sin usar LLM: fetch de `url_fuente`,
comprobación del precio en el HTML, coherencia €/L vs. formato y desviación
respecto al último precio conocido.

El candidato puede incluir `precio_eur_anterior` (lo añade el caso de uso
cuando conoce el último precio persistido) para la regla de desviación.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.dominio.precios.estados import EstadoPrecio
from src.puertos.productor import Candidato

# (estado, motivos) donde estado es uno de ESTADOS_PRECIO y motivos explica
# por qué se marcó como sospechoso o rechazado.
ResultadoVerificacion = tuple[EstadoPrecio, list[str]]


@runtime_checkable
class Verificador(Protocol):
    """Decide si un candidato es verificado, sospechoso o rechazado."""

    async def verificar(self, candidato: Candidato) -> ResultadoVerificacion: ...
