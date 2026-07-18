"""Telegram inline/reply keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.reports import format_idr


def transaction_actions(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Ubah", callback_data=f"tx:edit:{transaction_id}"),
                InlineKeyboardButton(
                    text="🗑 Hapus", callback_data=f"tx:askdelete:{transaction_id}"
                ),
            ],
            [
                InlineKeyboardButton(text="➕ Tambah lagi", callback_data="menu:add"),
                InlineKeyboardButton(text="📊 Ringkasan", callback_data="menu:today"),
            ],
        ]
    )


def confirmation_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Konfirmasi", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="❌ Batal", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def delete_confirmation(transaction_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ya, hapus",
                    callback_data=f"tx:delete:{transaction_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Batal",
                    callback_data=f"tx:canceldelete:{transaction_id}",
                ),
            ]
        ]
    )


def transaction_delete_keyboard(rows: list[dict]) -> InlineKeyboardMarkup:
    """Create one safe-to-click delete selector for each transaction row."""
    buttons = []
    for row in rows:
        kind = "Pemasukan" if row["kind"] == "income" else "Pengeluaran"
        description = " ".join(str(row.get("description", "Transaksi")).split())
        if len(description) > 24:
            description = description[:21] + "..."
        label = f"🗑 {kind} · {format_idr(row['amount'])} · {description}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=label[:64],
                    callback_data=f"tx:askdelete:{int(row['id'])}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def export_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 PDF hari ini", callback_data="export:pdf:today")],
            [InlineKeyboardButton(text="📊 Excel minggu ini", callback_data="export:xlsx:week")],
            [InlineKeyboardButton(text="📄 PDF bulan ini", callback_data="export:pdf:month")],
            [InlineKeyboardButton(text="📊 Excel bulan ini", callback_data="export:xlsx:month")],
        ]
    )


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Hari ini", callback_data="menu:today"),
                InlineKeyboardButton(text="📆 Minggu", callback_data="menu:week"),
                InlineKeyboardButton(text="🗓 Bulan", callback_data="menu:month"),
            ],
            [
                InlineKeyboardButton(text="📤 Export", callback_data="menu:export"),
                InlineKeyboardButton(text="🧾 Transaksi", callback_data="menu:recent"),
            ],
        ]
    )
