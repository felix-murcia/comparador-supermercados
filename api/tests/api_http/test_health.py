from fastapi.testclient import TestClient

from src import main

client = TestClient(main.app)


def test_health_live() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_ok(monkeypatch) -> None:
    async def dependencies_ok() -> dict[str, bool]:
        return {"database_rw": True, "database_ro": True, "redis": True}

    monkeypatch.setattr(main, "check_dependencies", dependencies_ok)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database_rw": "ok", "database_ro": "ok", "redis": "ok"},
    }


def test_health_ready_fails_if_any_dependency_fails(monkeypatch) -> None:
    async def redis_down() -> dict[str, bool]:
        return {"database_rw": True, "database_ro": True, "redis": False}

    monkeypatch.setattr(main, "check_dependencies", redis_down)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database_rw": "ok", "database_ro": "ok", "redis": "error"},
    }
