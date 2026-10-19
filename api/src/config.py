from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# api/src/config.py -> repo/.env (local) y api/.env (override opcional).
_REPO_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_API_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Configuración de la aplicación, cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=(_REPO_ENV_FILE, _API_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== Entorno =====
    app_env: Literal["dev", "prod"] = "dev"
    app_secret_key: SecretStr = SecretStr("")
    app_base_url: str = ""
    web_base_url: str = ""
    api_port: int = 8000
    web_port: int = 3000
    http_port: int = 80
    https_port: int = 443
    image_tag: str = "0.1.0"

    # ===== Base de datos =====
    postgres_user: str = "app"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "precios"
    postgres_port: int = 5432
    postgres_replica_port: int = 5433
    postgres_replication_user: str = "replicator"
    postgres_replication_password: SecretStr = SecretStr("")
    database_url_rw: SecretStr = SecretStr("")
    database_url_ro: SecretStr = SecretStr("")

    # ===== Redis =====
    redis_url: str = ""
    cache_ttl_segundos: int = 86400

    # ===== Auth =====
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_redirect_uri: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: SecretStr = SecretStr("")
    microsoft_tenant_id: str = "common"
    microsoft_redirect_uri: str = ""

    # ===== LLM =====
    llm_provider: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    llm_max_reintentos: int = 3

    # ===== Observabilidad =====
    sentry_dsn: SecretStr = SecretStr("")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ===== Rate limit =====
    rate_limit_busquedas_por_minuto: int = 10


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
