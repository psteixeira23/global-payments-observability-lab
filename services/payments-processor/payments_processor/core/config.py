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
    provider_mock_base_url: str | None = None
    provider_mock_host: str = "provider-mock:8082"
    local_provider_scheme: str = "http"
    secure_provider_scheme: str = "https"
    provider_timeout_seconds: float = Field(default=1.5, gt=0)
    event_bus_backend: str = "none"
    event_bus_url: str | None = None
    event_bus_exchange: str = "payments.events"
    event_bus_routing_prefix: str = "payments"
    event_bus_kafka_bootstrap_servers: str = "kafka:9092"
    event_bus_kafka_topic: str = "payments.domain-events"

    poll_interval_seconds: float = Field(default=1.0, gt=0)
    batch_size: int = Field(default=50, ge=1)
    max_event_attempts: int = Field(default=5, ge=1)
    bulkhead_limit_per_provider: int = Field(default=25, ge=1)

    @property
    def resolved_provider_mock_base_url(self) -> str:
        if self.provider_mock_base_url:
            return self.provider_mock_base_url
        scheme = (
            self.local_provider_scheme if self.app_env == "local" else self.secure_provider_scheme
        )
        return f"{scheme}://{self.provider_mock_host}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
