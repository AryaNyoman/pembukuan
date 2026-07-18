from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    Budget,
    Category,
    Transaction,
    User,
    UserSetting,
)

DEFAULT_CATEGORIES = [
    ("Makan & Minum", "🍜", False),
    ("Transportasi", "🚗", False),
    ("Rumah & Tagihan", "🏠", False),
    ("Belanja", "🛒", False),
    ("Kesehatan", "❤️", False),
    ("Pendidikan", "🎓", False),
    ("Hiburan", "🎮", False),
    ("Pekerjaan", "💼", False),
    ("Hadiah/Donasi", "🎁", False),
    ("Pemasukan", "💰", True),
    ("Lainnya", "📦", False),
]


async def get_or_create_user(session: AsyncSession, telegram_user_id: int, **profile: Any) -> User:
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            **{key: profile.get(key) for key in ("username", "first_name")},
        )
        session.add(user)
        await session.flush()
        session.add(UserSetting(user_id=user.id))
        for name, emoji, is_income in DEFAULT_CATEGORIES:
            session.add(Category(user_id=user.id, name=name, emoji=emoji, is_income=is_income))
        await session.commit()
        await session.refresh(user)
    else:
        changed = False
        for key in ("username", "first_name"):
            value = profile.get(key)
            if value is not None and getattr(user, key) != value:
                setattr(user, key, value)
                changed = True
        if changed:
            await session.commit()
    return user


async def get_settings(session: AsyncSession, user_id: int) -> UserSetting:
    settings = await session.scalar(select(UserSetting).where(UserSetting.user_id == user_id))
    if settings is None:
        settings = UserSetting(user_id=user_id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def get_categories(session: AsyncSession, user_id: int) -> list[Category]:
    result = await session.scalars(
        select(Category).where(Category.user_id == user_id).order_by(Category.id)
    )
    return list(result.all())


async def find_category(session: AsyncSession, user_id: int, name: str) -> Category | None:
    return await session.scalar(
        select(Category).where(Category.user_id == user_id, Category.name == name)
    )


async def add_category(
    session: AsyncSession,
    user_id: int,
    name: str,
    emoji: str = "📦",
    is_income: bool = False,
) -> Category:
    name = " ".join(name.strip().split())[:80]
    if not name:
        raise ValueError("Nama kategori kosong")
    if await find_category(session, user_id, name):
        raise ValueError("Kategori sudah ada")
    category = Category(user_id=user_id, name=name, emoji=emoji[:8], is_income=is_income)
    session.add(category)
    await log_action(session, user_id, "create_category", name)
    await session.commit()
    await session.refresh(category)
    return category


async def update_user_settings(
    session: AsyncSession,
    user_id: int,
    *,
    timezone: str | None = None,
    currency: str | None = None,
    reminders_enabled: bool | None = None,
) -> UserSetting:
    settings = await get_settings(session, user_id)
    if timezone is not None:
        settings.timezone = timezone[:64]
    if currency is not None:
        settings.currency = currency[:8].upper()
    if reminders_enabled is not None:
        settings.reminders_enabled = reminders_enabled
    await log_action(session, user_id, "update_settings")
    await session.commit()
    await session.refresh(settings)
    return settings


async def add_transaction(
    session: AsyncSession,
    *,
    user_id: int,
    kind: str,
    amount: int,
    description: str,
    category_name: str,
    tags: list[str],
    occurred_at: datetime,
    source: str = "telegram",
) -> Transaction:
    category = await find_category(session, user_id, category_name)
    if category is None:
        category = await find_category(session, user_id, "Lainnya")
    transaction = Transaction(
        user_id=user_id,
        category_id=category.id if category else None,
        kind=kind,
        amount=amount,
        description=description[:500],
        tags=",".join(tags)[:500],
        source=source[:32],
        occurred_at=occurred_at,
    )
    session.add(transaction)
    await session.flush()
    await log_action(session, user_id, "create_transaction", str(transaction.id))
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def update_transaction(
    session: AsyncSession,
    *,
    user_id: int,
    transaction_id: int,
    kind: str,
    amount: int,
    description: str,
    category_name: str,
    tags: list[str],
    occurred_at: datetime,
) -> Transaction | None:
    transaction = await session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        )
    )
    if transaction is None:
        return None
    category = await find_category(session, user_id, category_name)
    if category is None:
        category = await find_category(session, user_id, "Lainnya")
    transaction.category_id = category.id if category else None
    transaction.kind = kind
    transaction.amount = amount
    transaction.description = description[:500]
    transaction.tags = ",".join(tags)[:500]
    transaction.occurred_at = occurred_at
    await log_action(session, user_id, "update_transaction", str(transaction_id))
    await session.commit()
    await session.refresh(transaction)
    return transaction


def _row_dict(transaction: Transaction, category_name: str | None) -> dict[str, Any]:
    return {
        "id": transaction.id,
        "amount": transaction.amount,
        "kind": transaction.kind,
        "description": transaction.description,
        "category": category_name or "Lainnya",
        "tags": transaction.tags,
        "source": transaction.source,
        "occurred_at": transaction.occurred_at,
        "created_at": transaction.created_at,
        "updated_at": transaction.updated_at,
    }


async def list_transactions(
    session: AsyncSession,
    user_id: int,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = 50,
    offset: int = 0,
    query: str | None = None,
) -> list[dict[str, Any]]:
    conditions = [Transaction.user_id == user_id, Transaction.deleted_at.is_(None)]
    if start is not None:
        conditions.append(Transaction.occurred_at >= start)
    if end is not None:
        conditions.append(Transaction.occurred_at <= end)
    if query:
        pattern = f"%{query[:100]}%"
        conditions.append(
            or_(Transaction.description.ilike(pattern), Transaction.tags.ilike(pattern))
        )
    statement = (
        select(Transaction, Category.name.label("category_name"))
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(and_(*conditions))
        .order_by(desc(Transaction.occurred_at), desc(Transaction.id))
        .offset(max(offset, 0))
    )
    if limit is not None:
        statement = statement.limit(min(max(limit, 1), 100_000))
    result = await session.execute(statement)
    return [_row_dict(transaction, category_name) for transaction, category_name in result.all()]


async def get_budgets(session: AsyncSession, user_id: int, year: int, month: int) -> dict[str, int]:
    statement = (
        select(Category.name, Budget.amount)
        .join(Budget, Budget.category_id == Category.id)
        .where(Budget.user_id == user_id, Budget.year == year, Budget.month == month)
    )
    return {name: amount for name, amount in (await session.execute(statement)).all()}


async def set_budget(
    session: AsyncSession, user_id: int, category_name: str, year: int, month: int, amount: int
) -> None:
    category = await find_category(session, user_id, category_name)
    if category is None:
        raise ValueError("Kategori tidak ditemukan")
    budget = await session.scalar(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category.id,
            Budget.year == year,
            Budget.month == month,
        )
    )
    if budget is None:
        session.add(
            Budget(
                user_id=user_id,
                category_id=category.id,
                year=year,
                month=month,
                amount=amount,
            )
        )
    else:
        budget.amount = amount
    await log_action(session, user_id, "set_budget", str(category.id))
    await session.commit()


async def soft_delete_transaction(session: AsyncSession, user_id: int, transaction_id: int) -> bool:
    transaction = await session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        )
    )
    if transaction is None:
        return False
    transaction.deleted_at = datetime.utcnow()
    await log_action(session, user_id, "delete_transaction", str(transaction_id))
    await session.commit()
    return True


async def log_action(
    session: AsyncSession,
    user_id: int | None,
    action: str,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
    )
