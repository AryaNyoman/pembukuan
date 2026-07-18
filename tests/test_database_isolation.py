import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.db import repositories as repo
from app.db.models import Category, User, UserSetting
from app.db.session import create_engine, create_session_factory, init_db
from app.services.reports import summarize_transactions


@pytest.mark.asyncio
async def test_transactions_are_isolated_and_sqlite_dates_can_be_summarized():
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    sessions = create_session_factory(engine)
    occurred = datetime(2026, 7, 18, 12, tzinfo=ZoneInfo("Asia/Makassar"))

    async with sessions() as session:
        first = await repo.get_or_create_user(session, 123456789)
        second = await repo.get_or_create_user(session, 987654321)
        await repo.add_transaction(
            session,
            user_id=first.id,
            kind="expense",
            amount=25_000,
            description="Makan siang",
            category_name="Makan & Minum",
            tags=[],
            occurred_at=occurred,
        )
        first_rows = await repo.list_transactions(session, first.id, limit=20)
        second_rows = await repo.list_transactions(session, second.id, limit=20)

    assert len(first_rows) == 1
    assert second_rows == []
    summary = summarize_transactions(
        first_rows,
        start=datetime(2026, 7, 18, tzinfo=ZoneInfo("Asia/Makassar")),
        end=datetime(2026, 7, 18, 23, 59, 59, tzinfo=ZoneInfo("Asia/Makassar")),
    )
    assert summary["expense"] == 25_000
    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_get_or_create_user_is_idempotent(tmp_path):
    database = tmp_path / "concurrent.db"
    engine = create_engine(f"sqlite+aiosqlite:///{database}")
    await init_db(engine)
    sessions = create_session_factory(engine)

    async def create_same_user():
        async with sessions() as session:
            return await repo.get_or_create_user(session, 123456789)

    first, second = await asyncio.gather(create_same_user(), create_same_user())

    async with sessions() as session:
        user_count = await session.scalar(
            select(func.count()).select_from(User).where(User.telegram_user_id == 123456789)
        )
        settings_count = await session.scalar(
            select(func.count()).select_from(UserSetting).where(UserSetting.user_id == first.id)
        )
        category_count = await session.scalar(
            select(func.count()).select_from(Category).where(Category.user_id == first.id)
        )

    assert first.id == second.id
    assert user_count == 1
    assert settings_count == 1
    assert category_count == len(repo.DEFAULT_CATEGORIES)
    await engine.dispose()
