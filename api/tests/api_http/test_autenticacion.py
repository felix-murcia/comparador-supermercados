"""Tests del parseo y validación del JWT de sesión compartido con Auth.js.

Contrato definido en ADR-012: JWS HS256 firmado con `NEXTAUTH_SECRET`.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime

import jwt as pyjwt
import pytest
from pydantic import SecretStr
from starlette.requests import Request

from src.api_http import autenticacion
from src.api_http.errores import ErrorAPI

_SECRETO = "secreto-de-prueba-unit-tests-32-bytes"


def _token(**sobrescritos: object) -> str:
    ahora = int(datetime.now(UTC).timestamp())
    claims: dict[str, object] = {
        "sub": "authjs:google:123",
        "email": "ana@example.test",
        "name": "Ana",
        "picture": "https://avatars.test/ana.png",
        "provider": "google",
        "provider_id": "123",
        "iat": ahora,
        "exp": ahora + 300,
    }
    claims.update(sobrescritos)
    return pyjwt.encode(claims, _SECRETO, algorithm="HS256")


def _token_sin_firma() -> str:
    def _b64(datos: dict[str, object]) -> str:
        crudo = json.dumps(datos).encode()
        return base64.urlsafe_b64encode(crudo).rstrip(b"=").decode()

    ahora = int(datetime.now(UTC).timestamp())
    cabecera = _b64({"alg": "none", "typ": "JWT"})
    carga = _b64(
        {
            "provider": "google",
            "provider_id": "123",
            "email": "ana@example.test",
            "exp": ahora + 300,
        }
    )
    return f"{cabecera}.{carga}."


def _request(cabecera: str | None) -> Request:
    headers = [] if cabecera is None else [(b"authorization", cabecera.encode())]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/me",
            "raw_path": b"/v1/me",
            "query_string": b"",
            "headers": headers,
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 123),
        }
    )


def test_validar_token_ok() -> None:
    identidad = autenticacion.validar_token(_token(), _SECRETO)

    assert identidad.provider == "google"
    assert identidad.provider_id == "123"
    assert identidad.email == "ana@example.test"
    assert identidad.nombre == "Ana"
    assert identidad.avatar_url == "https://avatars.test/ana.png"


def test_validar_token_caducado_falla() -> None:
    token = _token(exp=int(datetime.now(UTC).timestamp()) - 1)

    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.validar_token(token, _SECRETO)

    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "NO_AUTENTICADO"


def test_validar_token_con_firma_invalida_falla() -> None:
    token = pyjwt.encode({"provider": "google"}, "otro-secreto-de-prueba-unit-32-bytes", algorithm="HS256")

    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.validar_token(token, _SECRETO)

    assert excinfo.value.status_code == 401


def test_validar_token_sin_algoritmo_permitido_falla() -> None:
    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.validar_token(_token_sin_firma(), _SECRETO)

    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "NO_AUTENTICADO"


@pytest.mark.parametrize("claim", ["provider", "provider_id", "email"])
def test_validar_token_sin_claims_obligatorios_falla(claim: str) -> None:
    token = _token(**{claim: ""})

    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.validar_token(token, _SECRETO)

    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "NO_AUTENTICADO"


def test_validar_token_sin_expiracion_falla() -> None:
    ahora = int(datetime.now(UTC).timestamp())
    token = pyjwt.encode(
        {
            "provider": "google",
            "provider_id": "123",
            "email": "ana@example.test",
            "iat": ahora,
        },
        _SECRETO,
        algorithm="HS256",
    )

    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.validar_token(token, _SECRETO)

    assert excinfo.value.status_code == 401


def test_token_bearer_sin_cabecera_falla() -> None:
    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.token_bearer(_request(None))

    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "NO_AUTENTICADO"


def test_token_bearer_con_formato_incorrecto_falla() -> None:
    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.token_bearer(_request("Token abc"))

    assert excinfo.value.status_code == 401


def test_token_bearer_vacio_falla() -> None:
    with pytest.raises(ErrorAPI) as excinfo:
        autenticacion.token_bearer(_request("Bearer   "))

    assert excinfo.value.status_code == 401


def test_token_bearer_ok() -> None:
    token = _token()

    assert autenticacion.token_bearer(_request(f"Bearer {token}")) == token


@pytest.mark.asyncio
async def test_obtener_identidad_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autenticacion.settings, "nextauth_secret", SecretStr(_SECRETO))

    identidad = await autenticacion.obtener_identidad(_request(f"Bearer {_token()}"))

    assert identidad.provider_id == "123"
    assert identidad.email == "ana@example.test"


@pytest.mark.asyncio
async def test_obtener_identidad_sin_secreto_configurado_falla(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autenticacion.settings, "nextauth_secret", SecretStr(""))

    with pytest.raises(ErrorAPI) as excinfo:
        await autenticacion.obtener_identidad(_request(f"Bearer {_token()}"))

    assert excinfo.value.status_code == 500
    assert excinfo.value.code == "AUTH_NO_CONFIGURADA"
