from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "payments-processor"
    app_env: str = "local"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payments"
    provider_mock_base_url: str = "http://provider-mock:8082"
    provider_timeout_seconds: float = Field(default=1.5, gt=0)

    poll_interval_seconds: float = Field(default=1.0, gt=0)
    batch_size: int = Field(default=50, ge=1)
    max_event_attempts: int = Field(default=5, ge=1)
    bulkhead_limit_per_provider: int = Field(default=25, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
