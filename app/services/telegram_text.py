from __future__ import annotations

from app.services.reports import format_idr


def transaction_text(transaction: dict) -> str:
    kind = "Pemasukan" if transaction["kind"] == "income" else "Pengeluaran"
    date_text = transaction["occurred_at"].strftime("%d/%m/%Y %H:%M")
    return (
        f"✅ {kind} tersimpan\n"
        f"{format_idr(transaction['amount'])} · {transaction.get('category', 'Lainnya')}\n"
        f"{transaction['description']}\n"
        f"{date_text} · ID #{transaction['id']}"
    )
