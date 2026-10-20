"""Lista blanca de administradores."""

from __future__ import annotations


def es_admin(email: str, lista: str) -> bool:
    """True si el email está en la lista blanca (separada por comas)."""
    permitidos = {
        permitted.strip().lower() for permitted in lista.split(",") if permitted.strip()
    }
    return email.strip().lower() in permitidos
