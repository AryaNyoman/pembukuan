from datetime import datetime

from app.services.reports import summarize_transactions


def test_summary_totals_categories_and_previous_period():
    rows = [
        {
            "amount": 100_000,
            "kind": "income",
            "category": "Pemasukan",
            "occurred_at": datetime(2026, 7, 1),
        },
        {
            "amount": 25_000,
            "kind": "expense",
            "category": "Makan & Minum",
            "occurred_at": datetime(2026, 7, 1),
        },
        {
            "amount": 50_000,
            "kind": "expense",
            "category": "Transportasi",
            "occurred_at": datetime(2026, 7, 2),
        },
        {
            "amount": 10_000,
            "kind": "expense",
            "category": "Makan & Minum",
            "occurred_at": datetime(2026, 6, 30),
        },
    ]
    result = summarize_transactions(
        rows, start=datetime(2026, 7, 1), end=datetime(2026, 7, 2, 23, 59, 59)
    )
    assert result["income"] == 100_000
    assert result["expense"] == 75_000
    assert result["net"] == 25_000
    assert result["by_category"] == {"Transportasi": 50_000, "Makan & Minum": 25_000}
    assert result["previous_expense"] == 10_000
    assert result["transaction_count"] == 3


def test_summary_budget_status():
    rows = [
        {
            "amount": 80_000,
            "kind": "expense",
            "category": "Makan & Minum",
            "occurred_at": datetime(2026, 7, 1),
        }
    ]
    result = summarize_transactions(
        rows,
        start=datetime(2026, 7, 1),
        end=datetime(2026, 7, 31, 23, 59, 59),
        budgets={"Makan & Minum": 100_000},
    )
    assert result["budget_status"]["Makan & Minum"] == {
        "budget": 100_000,
        "used": 80_000,
        "remaining": 20_000,
        "percent": 80.0,
    }
