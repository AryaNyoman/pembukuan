from __future__ import annotations

from datetime import datetime
from pathlib import Path


def cleanup_expired_exports(directory: str | Path, ttl_seconds: int) -> int:
    """Delete only generated PDF/XLSX files older than the configured TTL."""
    root = Path(directory)
    if not root.exists():
        return 0
    cutoff = datetime.now().timestamp() - ttl_seconds
    deleted = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".xlsx"}:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        except FileNotFoundError:
            continue
    return deleted
