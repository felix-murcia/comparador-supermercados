from pathlib import Path

import pytest

from src.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"

# Variables que solo usa la web (Next.js). La API no las necesita: el test
# de cobertura sirve para que `.env.example` y la API no se desincronicen.
VARIABLES_SOLO_WEB = {
    "api_internal_url",
    "next_public_app_env",
    "next_public_sentry_dsn",
    "sentry_org",
    "sentry_project",
    "session_ttl_segundos",
}


def _env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", 1)[0].strip().lower())
    return keys


@pytest.mark.skipif(
    not ENV_EXAMPLE.exists(), reason=".env.example no está en el contexto de tests"
)
def test_settings_cover_all_env_example_variables() -> None:
    missing = _env_keys(ENV_EXAMPLE) - set(Settings.model_fields) - VARIABLES_SOLO_WEB

    assert missing == set()


@pytest.mark.skipif(
    not ENV_EXAMPLE.exists(), reason=".env.example no está en el contexto de tests"
)
def test_settings_load_env_example_without_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # El entorno del proceso tiene prioridad sobre el fichero: se limpia
    # para que la carga sea la de `.env.example` y no la de quien ejecuta.
    for clave in _env_keys(ENV_EXAMPLE):
        monkeypatch.delenv(clave, raising=False)
        monkeypatch.delenv(clave.upper(), raising=False)

    settings = Settings(_env_file=ENV_EXAMPLE)  # type: ignore[call-arg]

    assert settings.app_env == "dev"
    assert settings.database_url_rw.get_secret_value().startswith(
        "postgresql+asyncpg://"
    )
    assert settings.database_url_ro.get_secret_value().startswith(
        "postgresql+asyncpg://"
    )
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.cache_ttl_segundos == 86400
    assert settings.sticky_reads_segundos == 5
    assert settings.log_level == "INFO"
