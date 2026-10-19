from __future__ import annotations

from typing import cast

import pytest
from redis.asyncio import Redis

from src.adaptadores.persistencia.sticky import StickyReads


class _FakeRedis:
    def __init__(self) -> None:
        self.valores: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}
        self.cerrado = False

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.valores[key] = value
        self.ttls[key] = ex
        return True

    async def exists(self, key: str) -> int:
        return int(key in self.valores)

    async def aclose(self) -> None:
        self.cerrado = True


def _sticky(ttl: int = 30) -> tuple[StickyReads, _FakeRedis]:
    redis = _FakeRedis()
    return StickyReads(cast(Redis, redis), ttl), redis


@pytest.mark.asyncio
async def test_marca_y_consulta_sticky() -> None:
    sticky, redis = _sticky()

    await sticky.marcar("usuario-1")

    assert redis.valores == {"sticky:rw:usuario-1": "1"}
    assert redis.ttls == {"sticky:rw:usuario-1": 30}
    assert await sticky.activo("usuario-1") is True
    assert await sticky.activo("usuario-2") is False

    await sticky.aclose()
    assert redis.cerrado is True


@pytest.mark.asyncio
async def test_ttl_cero_desactiva_el_sticky() -> None:
    sticky, redis = _sticky(ttl=0)

    await sticky.marcar("usuario-1")

    assert redis.valores == {}
    assert await sticky.activo("usuario-1") is False


def test_ttl_negativo_es_invalido() -> None:
    with pytest.raises(ValueError, match="negativo"):
        _sticky(ttl=-1)
