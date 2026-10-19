"""Autenticación stateless por JWT HS256 compartido con Auth.js (ADR-012)."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request

from src.api_http.errores import ErrorAPI
from src.config import settings
from src.dominio.usuarios.entidades import IdentidadOAuth

_ALGORITMO = "HS256"
_PREFIJO_BEARER = "Bearer "
_CLAIMS_TEXTO = ("provider", "provider_id", "email")


def token_bearer(request: Request) -> str:
    """Extrae el token del header `Authorization: Bearer <token>`."""
    cabecera = request.headers.get("Authorization", "")
    if not cabecera.startswith(_PREFIJO_BEARER):
        raise ErrorAPI(401, "NO_AUTENTICADO", "Falta el token Bearer")
    token = cabecera[len(_PREFIJO_BEARER) :].strip()
    if not token:
        raise ErrorAPI(401, "NO_AUTENTICADO", "Token vacío")
    return token


def _claim_texto(claims: dict[str, object], nombre: str) -> str:
    valor = claims.get(nombre)
    if not isinstance(valor, str) or not valor:
        raise ErrorAPI(401, "NO_AUTENTICADO", "Token sin claims obligatorios")
    return valor


def validar_token(token: str, secreto: str) -> IdentidadOAuth:
    """Verifica firma HS256 y caducidad; devuelve la identidad del token."""
    try:
        claims = jwt.decode(
            token,
            secreto,
            algorithms=[_ALGORITMO],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError:
        raise ErrorAPI(401, "NO_AUTENTICADO", "Token inválido o caducado") from None

    return IdentidadOAuth(
        provider=_claim_texto(claims, "provider"),
        provider_id=_claim_texto(claims, "provider_id"),
        email=_claim_texto(claims, "email"),
        nombre=claims.get("name") if isinstance(claims.get("name"), str) else None,
        avatar_url=(
            claims.get("picture") if isinstance(claims.get("picture"), str) else None
        ),
    )


async def obtener_identidad(request: Request) -> IdentidadOAuth:
    """Dependencia FastAPI: identidad verificada del usuario autenticado."""
    token = token_bearer(request)
    secreto = settings.nextauth_secret.get_secret_value()
    if not secreto:
        raise ErrorAPI(500, "AUTH_NO_CONFIGURADA", "NEXTAUTH_SECRET no configurada")
    return validar_token(token, secreto)


Identidad = Annotated[IdentidadOAuth, Depends(obtener_identidad)]
