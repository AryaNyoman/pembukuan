from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta


def summarize_transactions(
    rows: Iterable[dict],
    *,
    start: datetime,
    end: datetime,
    budgets: dict[str, int] | None = None,
) -> dict:
    current = []
    previous = []
    # Treat the supplied interval as inclusive and compare the same duration before it.
    period_seconds = (end - start).total_seconds() + 1
    previous_start = start - timedelta(seconds=period_seconds)
    previous_end = start - timedelta(seconds=1)
    for row in rows:
        occurred = row["occurred_at"]
        if occurred.tzinfo is None and start.tzinfo is not None:
            # SQLite drops timezone metadata; preserve the configured local wall time.
            occurred = occurred.replace(tzinfo=start.tzinfo)
        elif occurred.tzinfo is not None and start.tzinfo is None:
            occurred = occurred.replace(tzinfo=None)
        if start <= occurred <= end:
            current.append(row)
        elif previous_start <= occurred <= previous_end:
            previous.append(row)
    income = sum(row["amount"] for row in current if row["kind"] == "income")
    expense = sum(row["amount"] for row in current if row["kind"] == "expense")
    previous_expense = sum(row["amount"] for row in previous if row["kind"] == "expense")
    by_category: dict[str, int] = defaultdict(int)
    for row in current:
        if row["kind"] == "expense":
            by_category[row.get("category") or "Lainnya"] += row["amount"]
    top = max(current, key=lambda row: row["amount"], default=None)
    budget_status = {}
    for category, budget in (budgets or {}).items():
        used = by_category.get(category, 0)
        budget_status[category] = {
            "budget": budget,
            "used": used,
            "remaining": budget - used,
            "percent": round((used / budget) * 100, 2) if budget else 0.0,
        }
    return {
        "start": start,
        "end": end,
        "income": income,
        "expense": expense,
        "net": income - expense,
        "previous_expense": previous_expense,
        "transaction_count": len(current),
        "by_category": dict(sorted(by_category.items(), key=lambda item: item[1], reverse=True)),
        "top_transaction": top,
        "budget_status": budget_status,
        "rows": sorted(current, key=lambda row: row["occurred_at"]),
    }


def format_idr(value: int) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}Rp{abs(value):,}".replace(",", ".")


def format_summary(summary: dict, title: str = "Ringkasan") -> str:
    lines = [
        f"📊 {title}",
        f"Periode: {summary['start']:%d/%m/%Y}–{summary['end']:%d/%m/%Y}",
        "",
        f"💰 Pemasukan: {format_idr(summary['income'])}",
        f"💸 Pengeluaran: {format_idr(summary['expense'])}",
        f"📈 Bersih: {format_idr(summary['net'])}",
        f"🧾 Transaksi: {summary['transaction_count']}",
    ]
    if summary["previous_expense"]:
        lines.append(f"Periode sebelumnya: {format_idr(summary['previous_expense'])} pengeluaran")
    if summary["by_category"]:
        lines.extend(["", "Kategori terbesar:"])
        lines.extend(
            f"• {category}: {format_idr(amount)}"
            for category, amount in list(summary["by_category"].items())[:5]
        )
    top = summary.get("top_transaction")
    if top:
        lines.append(
            f"\n🔎 Terbesar: {format_idr(top['amount'])} — {top.get('description', 'Transaksi')}"
        )
    for category, status in summary["budget_status"].items():
        if status["budget"]:
            marker = "⚠️" if status["percent"] >= 80 else "✅"
            lines.append(f"{marker} Anggaran {category}: {status['percent']:.0f}% terpakai")
    return "\n".join(lines)
