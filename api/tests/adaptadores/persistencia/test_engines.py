from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import SecretStr

from src.adaptadores.persistencia import engines


class _FakeEngine:
    def __init__(self, url: str) -> None:
        self.url = url
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


@pytest.fixture(autouse=True)
def _limpiar_caches() -> Any:
    engines._reset_engines_for_tests()
    yield
    engines._reset_engines_for_tests()


@pytest.mark.asyncio
async def test_engines_usan_las_urls_rw_y_ro(monkeypatch) -> None:
    creados: list[_FakeEngine] = []

    def fake_create(url: str, **kwargs: object) -> _FakeEngine:
        engine = _FakeEngine(url)
        creados.append(engine)
        return engine

    monkeypatch.setattr(
        engines,
        "settings",
        SimpleNamespace(
            database_url_rw=SecretStr("postgresql+asyncpg://rw/test"),
            database_url_ro=SecretStr("postgresql+asyncpg://ro/test"),
        ),
    )
    monkeypatch.setattr(engines, "create_async_engine", fake_create)

    engine_rw = cast(_FakeEngine, engines.get_engine_rw())
    engine_ro = cast(_FakeEngine, engines.get_engine_ro())

    assert [engine.url for engine in creados] == [
        "postgresql+asyncpg://rw/test",
        "postgresql+asyncpg://ro/test",
    ]
    assert engine_rw is not engine_ro
    assert engines.get_engine_rw() is engine_rw

    await engines.dispose_engines()

    assert engine_rw.disposed is True
    assert engine_ro.disposed is True
    assert engines.get_engine_rw.cache_info().currsize == 0


def test_engine_rw_falla_si_falta_la_url(monkeypatch) -> None:
    monkeypatch.setattr(
        engines,
        "settings",
        SimpleNamespace(
            database_url_rw=SecretStr(""),
            database_url_ro=SecretStr("postgresql+asyncpg://ro/test"),
        ),
    )

    with pytest.raises(RuntimeError, match="DATABASE_URL_RW"):
        engines.get_engine_rw()
