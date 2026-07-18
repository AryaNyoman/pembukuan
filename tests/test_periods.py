from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.periods import period_bounds

NOW = datetime(2026, 7, 18, 12, tzinfo=ZoneInfo("Asia/Makassar"))


def test_period_bounds_cover_expected_calendar_windows():
    start, end, title = period_bounds("today", NOW)
    assert start == datetime(2026, 7, 18, tzinfo=NOW.tzinfo)
    assert end.day == 18 and end.hour == 23
    assert title == "Hari ini"

    start, end, title = period_bounds("week", NOW)
    assert start.date().isoformat() == "2026-07-13"
    assert end.date().isoformat() == "2026-07-19"
    assert title == "Minggu ini"

    start, end, title = period_bounds("month", NOW)
    assert start.date().isoformat() == "2026-07-01"
    assert end.date().isoformat() == "2026-07-31"
    assert title == "Bulan ini"


def test_unknown_period_is_rejected():
    with pytest.raises(ValueError):
        period_bounds("year", NOW)
