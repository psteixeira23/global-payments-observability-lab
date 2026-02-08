from __future__ import annotations

from payments_processor.core.config import Settings


def test_resolved_provider_mock_base_url_prefers_explicit_value(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PROVIDER_MOCK_BASE_URL", "https://provider.example")

    settings = Settings()

    assert settings.resolved_provider_mock_base_url == "https://provider.example"


def test_resolved_provider_mock_base_url_uses_http_only_in_local_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("PROVIDER_MOCK_BASE_URL", raising=False)

    settings = Settings()

    assert settings.resolved_provider_mock_base_url == "http://provider-mock:8082"


def test_resolved_provider_mock_base_url_defaults_to_https_outside_local(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.delenv("PROVIDER_MOCK_BASE_URL", raising=False)

    settings = Settings()

    assert settings.resolved_provider_mock_base_url == "https://provider-mock:8082"
