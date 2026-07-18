from datetime import datetime

from app.keyboards import transaction_delete_keyboard


def test_transaction_delete_keyboard_lists_income_and_expense_rows():
    keyboard = transaction_delete_keyboard(
        [
            {
                "id": 12,
                "kind": "income",
                "amount": 500_000,
                "description": "Gaji",
                "occurred_at": datetime(2026, 7, 18, 9),
            },
            {
                "id": 13,
                "kind": "expense",
                "amount": 25_000,
                "description": "Makan siang",
                "occurred_at": datetime(2026, 7, 18, 12),
            },
        ]
    )

    buttons = [row[0] for row in keyboard.inline_keyboard]
    assert len(buttons) == 2
    assert buttons[0].callback_data == "tx:askdelete:12"
    assert "Rp500.000" in buttons[0].text
    assert "Pemasukan" in buttons[0].text
    assert buttons[1].callback_data == "tx:askdelete:13"
    assert "Rp25.000" in buttons[1].text
    assert "Pengeluaran" in buttons[1].text


def test_transaction_delete_keyboard_truncates_long_description():
    keyboard = transaction_delete_keyboard(
        [
            {
                "id": 1,
                "kind": "expense",
                "amount": 1_000,
                "description": "x" * 200,
                "occurred_at": datetime(2026, 7, 18),
            }
        ]
    )
    assert len(keyboard.inline_keyboard[0][0].text) <= 64
