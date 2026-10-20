"""Configuración del logging para los procesos que no usan uvicorn.

La API hereda la configuración de uvicorn, pero el worker y el scheduler se
ejecutan como scripts (`python -m src.worker`): sin configurar el logging,
sus mensajes INFO no aparecen en ningún sitio y solo se ven los WARNING que
Python emite por su cuenta. Eso hace imposible seguir la ingesta desde los
logs (por ejemplo, comprobar si un resultado se ha cacheado).
"""

from __future__ import annotations

import logging
import sys

from src.config import settings


def configurar_logging() -> None:
    """Deja el logging en stdout con el nivel y el formato de la configuración."""
    nivel = settings.log_level.upper()
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # httpx y urllib3 son muy verbosos en DEBUG y no aportan nada aquí.
    logging.getLogger("httpx").setLevel(max(logging.INFO, logging.WARNING))
    logging.getLogger("httpcore").setLevel(max(logging.INFO, logging.WARNING))
