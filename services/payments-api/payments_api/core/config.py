from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "payments-api"
    app_env: str = "local"
    log_level: str = "INFO"
    api_auth_enabled: bool = False
    api_auth_token: str | None = None

    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payments"
    redis_url: str = "redis://localhost:6379/0"
    cors_allowed_origins_csv: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"
    )

    idempotency_ttl_seconds: int = Field(default=300, ge=10)
    limits_policy_cache_ttl_seconds: int = Field(default=60, ge=10)

    supported_currencies: set[str] = {"BRL", "USD"}

    merchant_rate_limit: int = Field(default=120, ge=1)
    customer_rate_limit: int = Field(default=80, ge=1)
    account_rate_limit: int = Field(default=80, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    aml_total_window_seconds: int = Field(default=10 * 60, ge=60)
    aml_total_threshold_amount: float = Field(default=5000.0, ge=0)
    aml_structuring_window_seconds: int = Field(default=15 * 60, ge=60)
    aml_structuring_count_threshold: int = Field(default=3, ge=1)
    aml_blocklist_destinations_csv: str = "dest-blocked-001,dest-blocked-002"

    risk_review_threshold: int = Field(default=50, ge=1, le=100)
    risk_block_threshold: int = Field(default=80, ge=1, le=100)

    @property
    def aml_blocklist_destinations(self) -> set[str]:
        return {
            item.strip() for item in self.aml_blocklist_destinations_csv.split(",") if item.strip()
        }

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_allowed_origins_csv.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
