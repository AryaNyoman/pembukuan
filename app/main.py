from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import load_settings
from app.db.session import create_engine, create_session_factory, init_db
from app.handlers.access import AllowlistMiddleware
from app.handlers.bot_handlers import build_router
from app.services.cleanup import cleanup_expired_exports
from app.services.scheduler import create_scheduler, start_scheduler, stop_scheduler


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def run() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url)
    await init_db(engine)
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=settings.telegram_bot_token,
        # User-controlled descriptions/categories are sent as plain text by default.
        default=DefaultBotProperties(parse_mode=None),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.message.middleware(AllowlistMiddleware(settings))
    dispatcher.callback_query.middleware(AllowlistMiddleware(settings))
    dispatcher.include_router(build_router(settings, session_factory))
    scheduler = create_scheduler()
    scheduler.add_job(
        cleanup_expired_exports,
        "interval",
        minutes=15,
        args=[settings.export_dir, settings.export_ttl_seconds],
        id="cleanup_exports",
        replace_existing=True,
    )
    start_scheduler(scheduler)
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Mulai Buku Kas"),
                BotCommand(command="help", description="Bantuan"),
                BotCommand(command="hariini", description="Ringkasan hari ini"),
                BotCommand(command="minggu", description="Ringkasan minggu ini"),
                BotCommand(command="bulan", description="Ringkasan bulan ini"),
                BotCommand(command="terakhir", description="Transaksi terbaru"),
                BotCommand(command="cari", description="Cari transaksi"),
                BotCommand(command="export", description="Export PDF/Excel"),
                BotCommand(command="kategori", description="Lihat/tambah kategori"),
                BotCommand(command="anggaran", description="Lihat/set anggaran"),
                BotCommand(command="periode", description="Laporan periode custom"),
                BotCommand(command="backup", description="Backup transaksi pribadi"),
                BotCommand(command="pengaturan", description="Pengaturan"),
                BotCommand(command="status", description="Status bot untuk admin"),
                BotCommand(command="batal", description="Batalkan operasi"),
            ]
        )
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        stop_scheduler(scheduler)
        await bot.session.close()
        await engine.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
