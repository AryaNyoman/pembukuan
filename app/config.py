from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    allowed_user_ids: frozenset[int]
    admin_user_id: int | None
    database_url: str
    app_timezone: str
    currency: str
    log_level: str
    backup_dir: Path
    export_dir: Path
    export_ttl_seconds: int
    reminder_hour: int


def _parse_ids(value: str) -> frozenset[int]:
    ids: set[int] = set()
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = int(raw)
        except ValueError as exc:
            raise ValueError(f"Invalid Telegram user ID: {raw!r}") from exc
        if parsed <= 0:
            raise ValueError("Telegram user IDs must be positive integers")
        ids.add(parsed)
    if not ids:
        raise ValueError("ALLOWED_USER_IDS must contain at least one ID")
    return frozenset(ids)


def load_settings(env_file: str | Path | None = None) -> Settings:
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token.startswith("PASTE_"):
        raise ValueError("TELEGRAM_BOT_TOKEN is missing; set a new token from BotFather")
    allowed = _parse_ids(os.getenv("ALLOWED_USER_IDS", ""))
    admin_raw = os.getenv("ADMIN_USER_ID", "").strip()
    try:
        admin = int(admin_raw) if admin_raw else None
    except ValueError as exc:
        raise ValueError("ADMIN_USER_ID must be an integer") from exc
    if admin is not None and admin not in allowed:
        raise ValueError("ADMIN_USER_ID must also be in ALLOWED_USER_IDS")
    timezone = os.getenv("APP_TIMEZONE", "Asia/Makassar")
    try:
        ZoneInfo(timezone)
    except Exception as exc:
        raise ValueError(f"Invalid APP_TIMEZONE: {timezone}") from exc
    try:
        ttl = int(os.getenv("EXPORT_TTL_SECONDS", "3600"))
        reminder_hour = int(os.getenv("REMINDER_HOUR", "21"))
    except ValueError as exc:
        raise ValueError("EXPORT_TTL_SECONDS and REMINDER_HOUR must be integers") from exc
    if ttl < 60:
        raise ValueError("EXPORT_TTL_SECONDS must be at least 60")
    if not 0 <= reminder_hour <= 23:
        raise ValueError("REMINDER_HOUR must be between 0 and 23")
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups"))
    export_dir = Path(os.getenv("EXPORT_DIR", "./exports"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        telegram_bot_token=token,
        allowed_user_ids=allowed,
        admin_user_id=admin,
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bookkeeping.db"),
        app_timezone=timezone,
        currency=os.getenv("CURRENCY", "IDR"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        backup_dir=backup_dir,
        export_dir=export_dir,
        export_ttl_seconds=ttl,
        reminder_hour=reminder_hour,
    )
