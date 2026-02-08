from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.contracts import (
    Base,
    CustomerORM,
    CustomerStatus,
    KycLevel,
    LimitsPolicyORM,
    PaymentMethod,
)


def build_engine(postgres_dsn: str) -> AsyncEngine:
    return create_async_engine(postgres_dsn, echo=False, pool_pre_ping=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        await _seed_customers(session)
        await _seed_limits_policies(session)
        await session.commit()


async def _seed_customers(session: AsyncSession) -> None:
    existing = await session.execute(select(CustomerORM.customer_id).limit(1))
    if existing.scalar_one_or_none():
        return
    session.add_all(
        [
            CustomerORM(
                customer_id="customer-basic-001",
                kyc_level=KycLevel.BASIC,
                status=CustomerStatus.ACTIVE,
            ),
            CustomerORM(
                customer_id="customer-full-001",
                kyc_level=KycLevel.FULL,
                status=CustomerStatus.ACTIVE,
            ),
            CustomerORM(
                customer_id="customer-suspended-001",
                kyc_level=KycLevel.FULL,
                status=CustomerStatus.SUSPENDED,
            ),
            CustomerORM(
                customer_id="customer-none-001",
                kyc_level=KycLevel.NONE,
                status=CustomerStatus.ACTIVE,
            ),
        ]
    )


async def _seed_limits_policies(session: AsyncSession) -> None:
    existing = await session.execute(select(LimitsPolicyORM.rail).limit(1))
    if existing.scalar_one_or_none():
        return

    session.add_all(
        [
            LimitsPolicyORM(
                rail=PaymentMethod.PIX,
                min_amount=Decimal("1.00"),
                max_amount=Decimal("5000.00"),
                daily_limit_amount=Decimal("20000.00"),
                velocity_limit_count=10,
                velocity_window_seconds=60,
            ),
            LimitsPolicyORM(
                rail=PaymentMethod.BOLETO,
                min_amount=Decimal("5.00"),
                max_amount=Decimal("10000.00"),
                daily_limit_amount=Decimal("30000.00"),
                velocity_limit_count=5,
                velocity_window_seconds=60,
            ),
            LimitsPolicyORM(
                rail=PaymentMethod.TED,
                min_amount=Decimal("50.00"),
                max_amount=Decimal("20000.00"),
                daily_limit_amount=Decimal("50000.00"),
                velocity_limit_count=4,
                velocity_window_seconds=60,
            ),
            LimitsPolicyORM(
                rail=PaymentMethod.CARD,
                min_amount=Decimal("1.00"),
                max_amount=Decimal("8000.00"),
                daily_limit_amount=Decimal("25000.00"),
                velocity_limit_count=12,
                velocity_window_seconds=60,
            ),
        ]
    )
