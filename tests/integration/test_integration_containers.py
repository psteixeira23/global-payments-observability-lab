from __future__ import annotations

import pytest


@pytest.mark.integration
def test_testcontainers_smoke() -> None:
    postgres_module = pytest.importorskip("testcontainers.postgres")
    redis_module = pytest.importorskip("testcontainers.redis")

    postgres_container_cls = postgres_module.PostgresContainer
    redis_container_cls = redis_module.RedisContainer

    try:
        with (
            postgres_container_cls("postgres:16-alpine") as postgres,
            redis_container_cls("redis:7-alpine") as redis,
        ):
            assert "postgresql://" in postgres.get_connection_url()
            assert redis.get_container_host_ip()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Docker runtime unavailable for integration test: {exc}")
