from __future__ import annotations

from payments_processor.db import session as processor_session


def test_build_engine_uses_expected_sqlalchemy_options(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_create_async_engine(dsn: str, **kwargs):  # noqa: ANN001, ANN002
        captured["dsn"] = dsn
        captured["kwargs"] = kwargs
        return "engine"

    monkeypatch.setattr(processor_session, "create_async_engine", fake_create_async_engine)

    engine = processor_session.build_engine("postgresql+asyncpg://demo")

    assert engine == "engine"
    assert captured["dsn"] == "postgresql+asyncpg://demo"
    assert captured["kwargs"] == {"echo": False, "pool_pre_ping": True}


def test_build_session_factory_sets_expire_on_commit_false(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_sessionmaker(engine, **kwargs):  # noqa: ANN001, ANN002
        captured["engine"] = engine
        captured["kwargs"] = kwargs
        return "factory"

    monkeypatch.setattr(processor_session, "async_sessionmaker", fake_sessionmaker)

    factory = processor_session.build_session_factory("engine")  # type: ignore[arg-type]

    assert factory == "factory"
    assert captured["engine"] == "engine"
    assert captured["kwargs"]["expire_on_commit"] is False
    assert captured["kwargs"]["class_"] is processor_session.AsyncSession
