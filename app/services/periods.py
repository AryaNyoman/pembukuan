from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def now_local(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone))


def period_bounds(period: str, now: datetime) -> tuple[datetime, datetime, str]:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return day, day + timedelta(days=1) - timedelta(microseconds=1), "Hari ini"
    if period == "week":
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=7) - timedelta(microseconds=1), "Minggu ini"
    if period == "month":
        start = day.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        return start, next_month - timedelta(microseconds=1), "Bulan ini"
    raise ValueError(f"Unknown period: {period}")
