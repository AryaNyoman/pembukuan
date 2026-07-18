from __future__ import annotations


def parse_allowed_user_ids(value: str) -> set[int]:
    result: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            user_id = int(item)
        except ValueError as exc:
            raise ValueError(f"Invalid Telegram user ID: {item!r}") from exc
        if user_id <= 0:
            raise ValueError("Telegram user IDs must be positive")
        result.add(user_id)
    if not result:
        raise ValueError("At least one allowed user ID is required")
    return result


def is_allowed_user(user_id: int | None, allowed_ids: set[int] | frozenset[int]) -> bool:
    return user_id is not None and user_id in allowed_ids


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}…{value[-visible:]}"


def safe_filename(name: str, suffix: str) -> str:
    """Return a flat, non-traversing export filename."""
    clean = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
    clean = clean.strip("._") or "export"
    return f"{clean[:80]}.{suffix.lstrip('.')}"
