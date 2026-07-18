from __future__ import annotations

import base64
import binascii
import os
import re
from pathlib import Path

_REQUIRED_PATTERNS = {
    "TELEGRAM_BOT_TOKEN": re.compile(r"[0-9]+:[A-Za-z0-9_-]+"),
    "ALLOWED_USER_IDS": re.compile(r"[0-9]+(?:,[0-9]+)*"),
    "ADMIN_USER_ID": re.compile(r"[0-9]+"),
}


def _decode_secret(value: str, pattern: re.Pattern[str]) -> str:
    plain = value.strip().strip('"').strip("'")
    if pattern.fullmatch(plain):
        return plain
    try:
        decoded = base64.b64decode(plain, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return plain
    return decoded


def load_codespaces_secrets(path: str | Path) -> dict[str, str]:
    """Load only required app secrets, accepting GitHub's Base64 env-file form."""
    source = Path(path)
    values: dict[str, str] = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.removeprefix("export ").split("=", 1)
        key = key.strip()
        pattern = _REQUIRED_PATTERNS.get(key)
        if pattern is None:
            continue
        decoded = _decode_secret(value, pattern)
        if not pattern.fullmatch(decoded):
            raise ValueError(f"{key} has an invalid format")
        values[key] = decoded
    return values


def install_codespaces_secrets(path: str | Path) -> None:
    for key, value in load_codespaces_secrets(path).items():
        os.environ[key] = value


def main() -> None:
    path = os.getenv("CODESPACES_SECRETS_FILE", "/workspaces/.codespaces/shared/.env-secrets")
    install_codespaces_secrets(path)
    from app.main import main as run_bot

    run_bot()


if __name__ == "__main__":
    main()
