from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.api_http import dependencias


class _FakeSession:
    def __init__(self, nombre: str, llamadas: list[str]) -> None:
        self.nombre = nombre
        self.llamadas = llamadas

    async def commit(self) -> None:
        self.llamadas.append(f"{self.nombre}:commit")

    async def rollback(self) -> None:
        self.llamadas.append(f"{self.nombre}:rollback")

    async def close(self) -> None:
        self.llamadas.append(f"{self.nombre}:close")


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        await self._session.close()


class _FakeSessionMaker:
    def __init__(self, nombre: str, llamadas: list[str]) -> None:
        self._nombre = nombre
        self._llamadas = llamadas

    def __call__(self) -> _FakeSessionContext:
        return _FakeSessionContext(_FakeSession(self._nombre, self._llamadas))


class _FakeSticky:
    def __init__(self, activos: set[str] | None = None) -> None:
        self.activos = activos or set()
        self.marcados: list[str] = []

    async def activo(self, usuario_id: str) -> bool:
        return usuario_id in self.activos

    async def marcar(self, usuario_id: str) -> None:
        self.marcados.append(usuario_id)
        self.activos.add(usuario_id)


def _request(method: str, usuario_id: str | None = None) -> Request:
    request = Request(
        {
            "type": "http",
            "method": method,
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 123),
        }
    )
    if usuario_id is not None:
        request.state.usuario_id = usuario_id
    return request


def _preparar(monkeypatch, sticky: _FakeSticky) -> list[str]:
    llamadas: list[str] = []
    ro = _FakeSessionMaker("ro", llamadas)
    rw = _FakeSessionMaker("rw", llamadas)

    monkeypatch.setattr(dependencias, "get_sessionmaker_ro", lambda: ro)
    monkeypatch.setattr(dependencias, "get_sessionmaker_rw", lambda: rw)
    monkeypatch.setattr(dependencias, "get_sticky_reads", lambda: sticky)
    return llamadas


async def _consumir(generator: AsyncIterator[AsyncSession]) -> _FakeSession:
    session = await anext(generator)
    with pytest.raises(StopAsyncIteration):
        await anext(generator)
    return cast(_FakeSession, session)


@pytest.mark.asyncio
async def test_lectura_usa_ro_sin_sticky(monkeypatch) -> None:
    sticky = _FakeSticky()
    llamadas = _preparar(monkeypatch, sticky)

    session = await _consumir(dependencias.get_session_ro(_request("GET", "u1")))

    assert session.nombre == "ro"
    assert llamadas == ["ro:close"]


@pytest.mark.asyncio
async def test_escritura_usa_rw_y_marca_sticky(monkeypatch) -> None:
    sticky = _FakeSticky()
    llamadas = _preparar(monkeypatch, sticky)

    session = await _consumir(dependencias.get_session_rw(_request("POST", "u1")))

    assert session.nombre == "rw"
    assert llamadas == ["rw:commit", "rw:close"]
    assert sticky.marcados == ["u1"]


@pytest.mark.asyncio
async def test_lectura_posterior_a_escritura_usa_rw(monkeypatch) -> None:
    sticky = _FakeSticky()
    llamadas = _preparar(monkeypatch, sticky)

    await _consumir(dependencias.get_session_rw(_request("POST", "u1")))
    session = await _consumir(dependencias.get_session_ro(_request("GET", "u1")))

    assert session.nombre == "rw"
    assert llamadas == ["rw:commit", "rw:close", "rw:close"]


@pytest.mark.asyncio
async def test_sticky_no_afecta_a_otro_usuario(monkeypatch) -> None:
    sticky = _FakeSticky({"u1"})
    _preparar(monkeypatch, sticky)

    session = await _consumir(dependencias.get_session_ro(_request("GET", "u2")))

    assert session.nombre == "ro"


@pytest.mark.asyncio
async def test_error_en_escritura_hace_rollback_y_no_marca_sticky(
    monkeypatch,
) -> None:
    sticky = _FakeSticky()
    llamadas = _preparar(monkeypatch, sticky)
    generator = cast(
        AsyncGenerator[AsyncSession, None],
        dependencias.get_session_rw(_request("POST", "u1")),
    )
    await anext(generator)

    with pytest.raises(RuntimeError, match="boom"):
        await generator.athrow(RuntimeError("boom"))

    assert llamadas == ["rw:rollback", "rw:close"]
    assert sticky.marcados == []
