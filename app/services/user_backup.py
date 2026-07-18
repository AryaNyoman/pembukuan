from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def create_user_backup(rows: list[dict], user_id: int, destination_dir: str | Path) -> Path:
    destination = Path(destination_dir) / str(user_id)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"backup-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex}.json"
    serializable = []
    for row in rows:
        item = dict(row)
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.isoformat()
        serializable.append(item)
    payload = {
        "format": "telegram-bookkeeping-user-backup-v1",
        "user_id": user_id,
        "created_at": datetime.now().astimezone().isoformat(),
        "transactions": serializable,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
