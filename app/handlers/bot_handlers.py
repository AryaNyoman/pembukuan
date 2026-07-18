from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db import repositories as repo
from app.handlers.states import EditingTransaction, PendingTransaction
from app.keyboards import (
    confirmation_keyboard,
    delete_confirmation,
    export_keyboard,
    main_menu,
    transaction_actions,
    transaction_delete_keyboard,
)
from app.services.exports import export_excel, export_pdf
from app.services.parser import parse_message
from app.services.periods import now_local, period_bounds
from app.services.reports import format_idr, format_summary, summarize_transactions
from app.services.telegram_text import transaction_text
from app.services.user_backup import create_user_backup

logger = logging.getLogger(__name__)


def build_router(settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> Router:
    router = Router(name="bookkeeping")

    async def get_user(session: AsyncSession, message: Message):
        user = message.from_user
        return await repo.get_or_create_user(
            session, user.id, username=user.username, first_name=user.first_name
        )

    async def report_for(user_id: int, period: str) -> tuple[dict, str]:
        async with session_factory() as session:
            user = await repo.get_or_create_user(session, user_id)
            settings_row = await repo.get_settings(session, user.id)
            current = now_local(settings_row.timezone or settings.app_timezone)
            start, end, title = period_bounds(period, current)
            rows = await repo.list_transactions(session, user.id, start=start, end=end, limit=None)
            budgets = await repo.get_budgets(session, user.id, current.year, current.month)
            return summarize_transactions(rows, start=start, end=end, budgets=budgets), title

    async def user_timezone(session: AsyncSession, user_id: int) -> str:
        settings_row = await repo.get_settings(session, user_id)
        return settings_row.timezone or settings.app_timezone

    async def send_report(message: Message, period: str, user_id: int | None = None) -> None:
        owner_id = user_id if user_id is not None else message.from_user.id
        report, title = await report_for(owner_id, period)
        await message.answer(
            format_summary(report, title), parse_mode=None, reply_markup=main_menu()
        )

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        async with session_factory() as session:
            await get_user(session, message)
        await message.answer(
            "👋 *Buku Kas siap digunakan.*\n\n"
            "Kirim transaksi langsung, misalnya:\n"
            "• `25k makan siang`\n"
            "• `kemarin 30rb bensin`\n"
            "• `+5jt gaji`\n\n"
            "Gunakan /help untuk bantuan.",
            parse_mode=None,
            reply_markup=main_menu(),
        )

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(
            "*Perintah Buku Kas*\n\n"
            "/hariini — ringkasan hari ini\n/minggu — ringkasan minggu ini\n"
            "/bulan — ringkasan bulan ini\n/periode — periode custom\n"
            "/terakhir — transaksi terbaru\n/cari kata — cari transaksi\n"
            "/kategori — lihat/tambah kategori\n/anggaran — lihat/set anggaran\n"
            "/export — PDF atau Excel\n/backup — backup transaksi pribadi\n"
            "/pengaturan — lihat/ubah pengaturan\n/status — status admin\n"
            "/batal — batalkan operasi\n\n"
            "Input cepat: 25k makan, -50rb bensin, +1,5jt freelance.",
            parse_mode=None,
        )

    @router.message(Command("hariini"))
    async def today(message: Message) -> None:
        await send_report(message, "today")

    @router.message(Command("minggu"))
    async def week(message: Message) -> None:
        await send_report(message, "week")

    @router.message(Command("bulan"))
    async def month(message: Message) -> None:
        await send_report(message, "month")

    @router.message(Command("tambah"))
    async def add_help(message: Message) -> None:
        await message.answer(
            "Kirim langsung seperti `25k makan siang` atau `+5jt gaji`.", parse_mode=None
        )

    @router.message(Command("export"))
    async def export_command(message: Message) -> None:
        await message.answer("Pilih laporan yang ingin diekspor:", reply_markup=export_keyboard())

    @router.message(Command("kategori"))
    async def categories(message: Message) -> None:
        argument = (message.text or "").partition(" ")[2].strip()
        async with session_factory() as session:
            user = await get_user(session, message)
            if argument.lower().startswith("tambah "):
                name = argument[7:].strip()
                try:
                    category = await repo.add_category(session, user.id, name)
                    await message.answer(f"Kategori dibuat: {category.emoji} {category.name}")
                except ValueError as exc:
                    await message.answer(f"Tidak bisa membuat kategori: {exc}")
                return
            items = await repo.get_categories(session, user.id)
        await message.answer(
            "Kategori:\n" + "\n".join(f"{item.emoji} {item.name}" for item in items),
            parse_mode=None,
        )

    @router.message(Command("anggaran"))
    async def budget(message: Message) -> None:
        argument = (message.text or "").partition(" ")[2].strip()
        async with session_factory() as session:
            user = await get_user(session, message)
            current = now_local(await user_timezone(session, user.id))
            if argument.lower().startswith("set "):
                parts = argument[4:].rsplit(" ", 1)
                if len(parts) != 2:
                    await message.answer("Format: /anggaran set Nama Kategori 500000")
                    return
                category_name, raw_amount = parts
                try:
                    amount = int(raw_amount.replace(".", "").replace(",", ""))
                    if amount <= 0:
                        raise ValueError
                    await repo.set_budget(
                        session, user.id, category_name, current.year, current.month, amount
                    )
                except ValueError:
                    await message.answer("Nominal anggaran tidak valid.")
                    return
                await message.answer(f"Anggaran {category_name} disimpan: {format_idr(amount)}")
                return
            budgets = await repo.get_budgets(session, user.id, current.year, current.month)
        if not budgets:
            await message.answer("Belum ada anggaran. Contoh: /anggaran set Makan & Minum 1000000")
            return
        await message.answer(
            "Anggaran bulan ini:\n"
            + "\n".join(f"• {name}: {format_idr(amount)}" for name, amount in budgets.items()),
            parse_mode=None,
        )

    @router.message(Command("periode"))
    async def custom_period(message: Message) -> None:
        raw = (message.text or "").partition(" ")[2].strip()
        parts = raw.split()
        if len(parts) != 2:
            await message.answer("Format: /periode DD/MM/YYYY DD/MM/YYYY")
            return
        try:
            async with session_factory() as session:
                user = await get_user(session, message)
                timezone = await user_timezone(session, user.id)
            current = now_local(timezone)
            start_date = datetime.strptime(parts[0], "%d/%m/%Y").date()
            end_date = datetime.strptime(parts[1], "%d/%m/%Y").date()
            if end_date < start_date or (end_date - start_date).days > 366:
                raise ValueError
            start = datetime.combine(start_date, datetime.min.time(), tzinfo=current.tzinfo)
            end = datetime.combine(end_date, datetime.max.time(), tzinfo=current.tzinfo)
        except ValueError:
            await message.answer("Tanggal/rentang tidak valid. Maksimal 366 hari.")
            return
        async with session_factory() as session:
            user = await get_user(session, message)
            rows = await repo.list_transactions(session, user.id, start=start, end=end, limit=None)
            budgets = await repo.get_budgets(session, user.id, current.year, current.month)
        report = summarize_transactions(rows, start=start, end=end, budgets=budgets)
        await message.answer(format_summary(report, "Periode custom"), parse_mode=None)

    @router.message(Command("backup"))
    async def backup(message: Message) -> None:
        async with session_factory() as session:
            user = await get_user(session, message)
            rows = await repo.list_transactions(session, user.id, limit=None)
        path = create_user_backup(rows, message.from_user.id, settings.backup_dir)
        try:
            await message.answer_document(FSInputFile(path), caption="Backup transaksi pribadi")
        except Exception:
            logger.exception("Failed to send user backup")
            await message.answer("Backup berhasil dibuat di server, tetapi gagal dikirim.")

    @router.message(Command("status"))
    async def status(message: Message) -> None:
        if message.from_user.id != settings.admin_user_id:
            await message.answer("Akses ditolak.")
            return
        await message.answer("Bot aktif. Database dan allowlist telah dimuat.")

    @router.message(Command("terakhir"))
    async def recent(message: Message, user_id: int | None = None) -> None:
        owner_id = user_id if user_id is not None else message.from_user.id
        async with session_factory() as session:
            user = await repo.get_or_create_user(session, owner_id)
            rows = await repo.list_transactions(session, user.id, limit=10)
        if not rows:
            await message.answer("Belum ada transaksi.", parse_mode=None)
            return
        lines = ["10 transaksi terbaru", ""]
        for row in rows:
            sign = "+" if row["kind"] == "income" else "-"
            lines.append(
                f"#{row['id']} {row['occurred_at']:%d/%m} "
                f"{sign}{format_idr(row['amount'])} · {row['description']}"
            )
        await message.answer(
            "\n".join(lines),
            parse_mode=None,
            reply_markup=transaction_delete_keyboard(rows),
        )

    @router.message(Command("cari"))
    async def search(message: Message) -> None:
        query = (message.text or "").partition(" ")[2].strip()
        if not query:
            await message.answer("Contoh: `/cari bensin`", parse_mode=None)
            return
        async with session_factory() as session:
            user = await get_user(session, message)
            rows = await repo.list_transactions(session, user.id, query=query, limit=20)
        if not rows:
            await message.answer("Tidak ada transaksi yang cocok.")
            return
        text = "*Hasil pencarian*\n\n" + "\n".join(
            f"#{row['id']} {row['occurred_at']:%d/%m/%Y} "
            f"{format_idr(row['amount'])} · {row['description']}"
            for row in rows
        )
        await message.answer(text, parse_mode=None)

    @router.message(Command("pengaturan"))
    async def preferences(message: Message) -> None:
        argument = (message.text or "").partition(" ")[2].strip()
        async with session_factory() as session:
            user = await get_user(session, message)
            current = await repo.get_settings(session, user.id)
            if argument.lower().startswith("timezone "):
                timezone = argument[9:].strip()
                try:
                    ZoneInfo(timezone)
                except ZoneInfoNotFoundError:
                    await message.answer("Timezone tidak valid. Contoh: Asia/Makassar")
                    return
                current = await repo.update_user_settings(session, user.id, timezone=timezone)
            elif argument.lower().startswith("currency "):
                currency = argument[9:].strip()
                if not 3 <= len(currency) <= 8 or not currency.isalnum():
                    await message.answer("Mata uang tidak valid. Contoh: IDR")
                    return
                current = await repo.update_user_settings(session, user.id, currency=currency)
        await message.answer(
            "Pengaturan\\n"
            f"Timezone: {current.timezone}\\n"
            f"Mata uang: {current.currency}\\n\\n"
            "Ubah: /pengaturan timezone Asia/Makassar atau /pengaturan currency IDR",
            parse_mode=None,
        )

    @router.message(Command("batal"))
    async def cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Operasi dibatalkan.")

    @router.callback_query(F.data == "txconfirm:yes")
    async def confirm_transaction(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        if not data:
            await callback.answer("Tidak ada transaksi yang menunggu konfirmasi.", show_alert=True)
            return
        try:
            occurred_at = datetime.fromisoformat(data["occurred_at"])
            async with session_factory() as session:
                user = await repo.get_or_create_user(session, callback.from_user.id)
                transaction = await repo.add_transaction(
                    session,
                    user_id=user.id,
                    kind=data["kind"],
                    amount=int(data["amount"]),
                    description=data["description"],
                    category_name=data["category_hint"],
                    tags=list(data.get("tags", [])),
                    occurred_at=occurred_at,
                )
            row = {
                "id": transaction.id,
                "kind": transaction.kind,
                "amount": transaction.amount,
                "description": transaction.description,
                "category": data["category_hint"],
                "occurred_at": transaction.occurred_at,
            }
            await state.clear()
            await callback.message.edit_text(
                transaction_text(row), reply_markup=transaction_actions(transaction.id)
            )
            await callback.answer("Transaksi disimpan.")
        except (KeyError, TypeError, ValueError):
            await state.clear()
            await callback.answer(
                "Data transaksi tidak valid. Silakan kirim ulang.", show_alert=True
            )

    @router.callback_query(F.data == "txconfirm:no")
    async def reject_transaction(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.edit_text("Transaksi dibatalkan.")
        await callback.answer("Dibatalkan.")

    @router.callback_query(F.data.startswith("menu:"))
    async def menu_callback(callback: CallbackQuery) -> None:
        action = callback.data.split(":", 1)[1]
        await callback.answer()
        if action == "export":
            await callback.message.answer("Pilih laporan:", reply_markup=export_keyboard())
        elif action == "recent":
            await recent(callback.message, user_id=callback.from_user.id)
        else:
            await send_report(
                callback.message,
                {"today": "today", "week": "week", "month": "month"}.get(action, "today"),
                user_id=callback.from_user.id,
            )

    @router.callback_query(F.data.startswith("export:"))
    async def export_callback(callback: CallbackQuery) -> None:
        _, fmt, period = callback.data.split(":", 2)
        await callback.answer("Membuat laporan…")
        report, title = await report_for(callback.from_user.id, period)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path(settings.export_dir) / str(callback.from_user.id)
        output_dir.mkdir(parents=True, exist_ok=True)
        file_id = uuid4().hex
        if fmt == "pdf":
            path = export_pdf(
                report,
                output_dir / f"laporan-{period}-{stamp}-{file_id}.pdf",
                title="Koran Keuangan",
            )
        else:
            path = export_excel(report, output_dir / f"laporan-{period}-{stamp}-{file_id}.xlsx")
        async with session_factory() as audit_session:
            owner = await repo.get_or_create_user(audit_session, callback.from_user.id)
            await repo.log_action(audit_session, owner.id, "export", period, {"format": fmt})
            await audit_session.commit()
        try:
            await callback.message.answer_document(
                FSInputFile(path), caption=f"{title} — {fmt.upper()}"
            )
        except Exception:
            logger.exception("Failed to send export")
            raise
        finally:
            path.unlink(missing_ok=True)

    @router.callback_query(F.data.startswith("tx:askdelete:"))
    async def ask_delete_callback(callback: CallbackQuery) -> None:
        transaction_id = int(callback.data.rsplit(":", 1)[1])
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=delete_confirmation(transaction_id))

    @router.callback_query(F.data.startswith("tx:canceldelete:"))
    async def cancel_delete_callback(callback: CallbackQuery) -> None:
        transaction_id = int(callback.data.rsplit(":", 1)[1])
        await callback.answer("Tidak dihapus.")
        await callback.message.edit_reply_markup(reply_markup=transaction_actions(transaction_id))

    @router.callback_query(F.data.startswith("tx:edit:"))
    async def edit_callback(callback: CallbackQuery, state: FSMContext) -> None:
        transaction_id = int(callback.data.rsplit(":", 1)[1])
        await state.set_state(EditingTransaction.waiting_for_text)
        await state.update_data(transaction_id=transaction_id)
        await callback.answer()
        await callback.message.answer(
            f"Kirim format baru untuk transaksi #{transaction_id}, misalnya `30k makan siang`.\n"
            "Ketik /batal untuk membatalkan.",
            parse_mode=None,
        )

    @router.callback_query(F.data.startswith("tx:delete:"))
    async def delete_callback(callback: CallbackQuery) -> None:
        transaction_id = int(callback.data.rsplit(":", 1)[1])
        async with session_factory() as session:
            user = await repo.get_or_create_user(session, callback.from_user.id)
            deleted = await repo.soft_delete_transaction(session, user.id, transaction_id)
            rows = await repo.list_transactions(session, user.id, limit=10) if deleted else []
        await callback.answer(
            "Transaksi dihapus." if deleted else "Transaksi tidak ditemukan.", show_alert=True
        )
        if deleted:
            if rows:
                lines = ["10 transaksi terbaru", ""]
                for row in rows:
                    sign = "+" if row["kind"] == "income" else "-"
                    lines.append(
                        f"#{row['id']} {row['occurred_at']:%d/%m} "
                        f"{sign}{format_idr(row['amount'])} · {row['description']}"
                    )
                await callback.message.edit_text(
                    "\n".join(lines),
                    parse_mode=None,
                    reply_markup=transaction_delete_keyboard(rows),
                )
            else:
                await callback.message.edit_text("Belum ada transaksi.", parse_mode=None)

    @router.message(EditingTransaction.waiting_for_text, F.text)
    async def edit_transaction_message(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        try:
            async with session_factory() as session:
                user = await get_user(session, message)
                settings_row = await repo.get_settings(session, user.id)
                parsed = parse_message(message.text or "", timezone=settings_row.timezone)
                if parsed.needs_confirmation:
                    raise ValueError("Edit membutuhkan nominal dan deskripsi yang jelas")
                transaction = await repo.update_transaction(
                    session,
                    user_id=user.id,
                    transaction_id=int(data["transaction_id"]),
                    kind=parsed.kind,
                    amount=parsed.amount,
                    description=parsed.description,
                    category_name=parsed.category_hint,
                    tags=parsed.tags,
                    occurred_at=parsed.occurred_at,
                )
            await state.clear()
            if transaction is None:
                await message.answer("Transaksi tidak ditemukan atau sudah dihapus.")
                return
            await message.answer(
                "✅ Transaksi diperbarui.\n"
                f"{format_idr(transaction.amount)} · {parsed.category_hint}\n"
                f"{transaction.description} · ID #{transaction.id}",
                reply_markup=transaction_actions(transaction.id),
            )
        except ValueError as exc:
            await message.answer(f"⚠️ {exc}\nContoh: `30k makan siang`", parse_mode=None)
        except Exception:
            logger.exception("Failed to edit transaction")
            await message.answer("Terjadi kesalahan saat mengubah transaksi. Coba lagi.")

    @router.message(F.text)
    async def transaction_message(message: Message, state: FSMContext) -> None:
        try:
            async with session_factory() as session:
                user = await get_user(session, message)
                settings_row = await repo.get_settings(session, user.id)
                parsed = parse_message(message.text or "", timezone=settings_row.timezone)
                if parsed.needs_confirmation:
                    await state.set_state(PendingTransaction.waiting_confirmation)
                    await state.update_data(
                        amount=parsed.amount,
                        kind=parsed.kind,
                        description=parsed.description,
                        category_hint=parsed.category_hint,
                        tags=parsed.tags,
                        occurred_at=parsed.occurred_at.isoformat(),
                    )
                    await message.answer(
                        "Saya memahami transaksi ini sebagai:\n"
                        f"{format_idr(parsed.amount)} · {parsed.category_hint}\n"
                        f"{parsed.description}\n\nSimpan?",
                        reply_markup=confirmation_keyboard("txconfirm"),
                    )
                    return
                transaction = await repo.add_transaction(
                    session,
                    user_id=user.id,
                    kind=parsed.kind,
                    amount=parsed.amount,
                    description=parsed.description,
                    category_name=parsed.category_hint,
                    tags=parsed.tags,
                    occurred_at=parsed.occurred_at,
                )
                row = {
                    "id": transaction.id,
                    "kind": transaction.kind,
                    "amount": transaction.amount,
                    "description": transaction.description,
                    "category": parsed.category_hint,
                    "occurred_at": transaction.occurred_at,
                }
            await message.answer(
                transaction_text(row), reply_markup=transaction_actions(transaction.id)
            )
        except ValueError as exc:
            await message.answer(f"⚠️ {exc}\nContoh: `25k makan siang`", parse_mode=None)
        except Exception:
            logger.exception("Failed to process transaction message")
            await message.answer("Terjadi kesalahan saat menyimpan transaksi. Coba lagi.")

    return router
