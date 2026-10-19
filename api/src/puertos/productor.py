"""Puerto del productor de precios.

El productor propone un candidato (típicamente un LLM con búsqueda web); nunca
es la fuente de verdad. La verificación determinista llega después.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# JSON estricto devuelto por el productor: precio_eur, url_fuente, formato,
# confianza y motivo_si_no_encontrado, entre otros.
Candidato = dict[str, Any]


@runtime_checkable
class Productor(Protocol):
    """Propone un candidato de precio para (query, cadena)."""

    async def producir(self, query: str, cadena: str) -> Candidato: ...
