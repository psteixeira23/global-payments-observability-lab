from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "provider-mock"
    log_level: str = "INFO"

    random_seed: int = 42
    base_latency_ms: int = Field(default=40, ge=0)
    latency_spike_ms: int = Field(default=350, ge=0)
    timeout_ms: int = Field(default=1200, ge=1)

    fault_5xx_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    timeout_rate: float = Field(default=0.03, ge=0.0, le=1.0)
    latency_spike_rate: float = Field(default=0.10, ge=0.0, le=1.0)
    duplicate_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    partial_failure_rate: float = Field(default=0.04, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
