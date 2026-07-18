from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Backup helper currently supports SQLite only")
    raw = unquote(database_url.removeprefix(prefix))
    return Path(raw)


def create_sqlite_backup(database_url: str, destination_dir: str | Path) -> Path:
    source = sqlite_path_from_url(database_url)
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f"bookkeeping-{datetime.now():%Y%m%d-%H%M%S}.db"
    source_conn = sqlite3.connect(source)
    target_conn = sqlite3.connect(target)
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()
    return target
