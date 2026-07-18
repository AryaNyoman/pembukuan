from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.parser import parse_message

NOW = datetime(2026, 7, 18, 12, 0, tzinfo=ZoneInfo("Asia/Makassar"))


def test_parses_k_expense_and_category_hint():
    result = parse_message("25k makan siang #kantor", now=NOW)
    assert result.amount == 25_000
    assert result.kind == "expense"
    assert result.description == "makan siang"
    assert result.tags == ["kantor"]
    assert result.occurred_at.date().isoformat() == "2026-07-18"
    assert result.category_hint == "Makan & Minum"


def test_parses_income_with_plus_and_juta_decimal():
    result = parse_message("+1,5jt freelance", now=NOW)
    assert result.amount == 1_500_000
    assert result.kind == "income"
    assert result.description == "freelance"


def test_parses_yesterday_and_rupiah_separator():
    result = parse_message("kemarin 30.000 bensin", now=NOW)
    assert result.amount == 30_000
    assert result.kind == "expense"
    assert result.occurred_at.date().isoformat() == "2026-07-17"
    assert result.category_hint == "Transportasi"


def test_empty_description_requires_confirmation():
    result = parse_message("18rb", now=NOW)
    assert result.amount == 18_000
    assert result.needs_confirmation is True
    assert result.description == "Transaksi"


def test_rejects_missing_amount():
    try:
        parse_message("makan siang", now=NOW)
    except ValueError as exc:
        assert "nominal" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError")


def test_date_before_amount_does_not_become_the_amount():
    result = parse_message("12/08 75k transport", now=NOW)
    assert result.amount == 75_000
    assert result.description == "transport"
    assert result.occurred_at.date().isoformat() == "2026-08-12"


def test_description_before_amount_is_preserved():
    result = parse_message("kopi 18.000", now=NOW)
    assert result.amount == 18_000
    assert result.description == "kopi"
    assert result.needs_confirmation is False


def test_masked_amount_is_rejected_instead_of_truncated():
    try:
        parse_message("+5****00 gaji", now=NOW)
    except ValueError as exc:
        assert "nominal" in str(exc).lower()
    else:
        raise AssertionError("Masked nominal must not be stored as Rp5")
