import json
from datetime import datetime

from app.services.user_backup import create_user_backup


def test_user_backup_contains_only_supplied_rows(tmp_path):
    path = create_user_backup(
        [{"id": 1, "amount": 25_000, "occurred_at": datetime(2026, 7, 18, 12)}],
        1105904688,
        tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["user_id"] == 1105904688
    assert len(payload["transactions"]) == 1
    assert payload["transactions"][0]["occurred_at"] == "2026-07-18T12:00:00"
    assert path.parent.name == "1105904688"
    assert path.suffix == ".json"
