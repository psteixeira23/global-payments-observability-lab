from __future__ import annotations

import pytest
from provider_mock.core.config import Settings, get_settings
from pydantic import ValidationError


def test_settings_loads_values_from_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("RANDOM_SEED", "123")
    monkeypatch.setenv("FAULT_5XX_RATE", "0.20")
    monkeypatch.setenv("TIMEOUT_RATE", "0.15")

    settings = Settings()

    assert settings.random_seed == 123
    assert settings.fault_5xx_rate == 0.20
    assert settings.timeout_rate == 0.15


def test_settings_rejects_invalid_fault_rate(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FAULT_5XX_RATE", "1.5")

    with pytest.raises(ValidationError):
        Settings()


def test_get_settings_is_cached_until_cache_clear() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()

    assert first is second

    get_settings.cache_clear()
    third = get_settings()
    assert third is not first
