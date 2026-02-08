from __future__ import annotations

from types import SimpleNamespace

import payments_api.main as api_main

from tests.helpers import create_test_client


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class FakeRedisClient:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _settings(app_env: str) -> SimpleNamespace:
    return SimpleNamespace(
        log_level="INFO",
        service_name="payments-api-test",
        postgres_dsn="postgresql+asyncpg://unused",
        redis_url="redis://unused",
        app_env=app_env,
    )


def test_lifespan_initializes_state_and_closes_resources(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = FakeEngine()
    redis_client = FakeRedisClient()
    session_factory = object()
    calls = {"init_db": 0}

    async def fake_init_db(_engine: FakeEngine) -> None:
        calls["init_db"] += 1

    monkeypatch.setattr(api_main, "get_settings", lambda: _settings("local"))
    monkeypatch.setattr(api_main, "configure_logging", lambda _level: None)
    monkeypatch.setattr(api_main, "configure_otel", lambda _service: None)
    monkeypatch.setattr(api_main, "build_engine", lambda _dsn: engine)
    monkeypatch.setattr(api_main, "build_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(api_main, "redis_from_url", lambda _url, decode_responses: redis_client)
    monkeypatch.setattr(api_main, "init_db", fake_init_db)

    with create_test_client(api_main.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "X-Trace-Id" in response.headers
        assert "/payments" in client.get("/openapi.json").json()["paths"]
        assert client.app.state.engine is engine
        assert client.app.state.session_factory is session_factory
        assert client.app.state.redis_client is redis_client

    assert calls["init_db"] == 1
    assert redis_client.closed is True
    assert engine.disposed is True


def test_lifespan_skips_init_db_when_not_local(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = FakeEngine()
    redis_client = FakeRedisClient()
    session_factory = object()
    calls = {"init_db": 0}

    async def fake_init_db(_engine: FakeEngine) -> None:
        calls["init_db"] += 1

    monkeypatch.setattr(api_main, "get_settings", lambda: _settings("prod"))
    monkeypatch.setattr(api_main, "configure_logging", lambda _level: None)
    monkeypatch.setattr(api_main, "configure_otel", lambda _service: None)
    monkeypatch.setattr(api_main, "build_engine", lambda _dsn: engine)
    monkeypatch.setattr(api_main, "build_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(api_main, "redis_from_url", lambda _url, decode_responses: redis_client)
    monkeypatch.setattr(api_main, "init_db", fake_init_db)

    with create_test_client(api_main.app) as client:
        assert client.get("/health").status_code == 200

    assert calls["init_db"] == 0
    assert redis_client.closed is True
    assert engine.disposed is True
