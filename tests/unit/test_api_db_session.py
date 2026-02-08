from __future__ import annotations

import pytest
from payments_api.db import session as api_session

from shared.contracts import PaymentMethod


class FakeExecuteResult:
    def __init__(self, value) -> None:  # noqa: ANN001
        self._value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self._value


class FakeSeedSession:
    def __init__(self, existing_value=None) -> None:  # noqa: ANN001
        self.existing_value = existing_value
        self.added_batches: list[list[object]] = []
        self.commit_count = 0

    async def execute(self, _stmt):  # noqa: ANN001
        return FakeExecuteResult(self.existing_value)

    def add_all(self, entities: list[object]) -> None:
        self.added_batches.append(entities)

    async def commit(self) -> None:
        self.commit_count += 1


class FakeSessionFactory:
    def __init__(self, session: FakeSeedSession) -> None:
        self._session = session

    def __call__(self) -> FakeSessionFactory:
        return self

    async def __aenter__(self) -> FakeSeedSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class FakeConnection:
    def __init__(self) -> None:
        self.sync_calls: list[object] = []

    async def run_sync(self, fn) -> None:  # noqa: ANN001
        self.sync_calls.append(fn)


class FakeBeginContext:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self._connection

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def begin(self) -> FakeBeginContext:
        return FakeBeginContext(self.connection)


@pytest.mark.asyncio
async def test_seed_customers_inserts_defaults_when_table_is_empty() -> None:
    seed_session = FakeSeedSession(existing_value=None)

    await api_session._seed_customers(seed_session)

    assert len(seed_session.added_batches) == 1
    customers = seed_session.added_batches[0]
    assert [customer.customer_id for customer in customers] == [
        "customer-basic-001",
        "customer-full-001",
        "customer-suspended-001",
        "customer-none-001",
    ]


@pytest.mark.asyncio
async def test_seed_customers_skips_when_table_has_data() -> None:
    seed_session = FakeSeedSession(existing_value="already-seeded")

    await api_session._seed_customers(seed_session)

    assert seed_session.added_batches == []


@pytest.mark.asyncio
async def test_seed_limits_policies_inserts_rails_when_missing() -> None:
    seed_session = FakeSeedSession(existing_value=None)

    await api_session._seed_limits_policies(seed_session)

    assert len(seed_session.added_batches) == 1
    policies = seed_session.added_batches[0]
    assert [policy.rail for policy in policies] == [
        PaymentMethod.PIX,
        PaymentMethod.BOLETO,
        PaymentMethod.TED,
        PaymentMethod.CARD,
    ]


@pytest.mark.asyncio
async def test_seed_limits_policies_skips_when_already_seeded() -> None:
    seed_session = FakeSeedSession(existing_value=PaymentMethod.PIX)

    await api_session._seed_limits_policies(seed_session)

    assert seed_session.added_batches == []


@pytest.mark.asyncio
async def test_init_db_creates_schema_and_runs_seed_pipeline(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    fake_engine = FakeEngine()
    seed_session = FakeSeedSession()
    session_factory = FakeSessionFactory(seed_session)
    calls = {"customers": 0, "limits": 0}

    async def fake_seed_customers(_session: FakeSeedSession) -> None:
        calls["customers"] += 1

    async def fake_seed_limits(_session: FakeSeedSession) -> None:
        calls["limits"] += 1

    monkeypatch.setattr(api_session, "build_session_factory", lambda _engine: session_factory)
    monkeypatch.setattr(api_session, "_seed_customers", fake_seed_customers)
    monkeypatch.setattr(api_session, "_seed_limits_policies", fake_seed_limits)

    await api_session.init_db(fake_engine)  # type: ignore[arg-type]

    assert len(fake_engine.connection.sync_calls) == 1
    assert calls == {"customers": 1, "limits": 1}
    assert seed_session.commit_count == 1


@pytest.mark.asyncio
async def test_get_session_yields_session_from_factory() -> None:
    seed_session = FakeSeedSession()
    factory = FakeSessionFactory(seed_session)

    sessions: list[FakeSeedSession] = []
    async for session in api_session.get_session(factory):  # type: ignore[arg-type]
        sessions.append(session)

    assert sessions == [seed_session]
