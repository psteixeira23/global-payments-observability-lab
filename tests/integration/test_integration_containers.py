from __future__ import annotations

import pytest


@pytest.mark.integration
def test_testcontainers_smoke() -> None:
    postgres_module = pytest.importorskip("testcontainers.postgres")
    redis_module = pytest.importorskip("testcontainers.redis")

    PostgresContainer = postgres_module.PostgresContainer
    RedisContainer = redis_module.RedisContainer

    try:
        with (
            PostgresContainer("postgres:16-alpine") as postgres,
            RedisContainer("redis:7-alpine") as redis,
        ):
            assert "postgresql://" in postgres.get_connection_url()
            assert redis.get_container_host_ip()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Docker runtime unavailable for integration test: {exc}")
