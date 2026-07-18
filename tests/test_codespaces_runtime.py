from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.codespaces_runtime import load_codespaces_secrets


def encoded(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def test_load_codespaces_secrets_decodes_required_values(tmp_path: Path) -> None:
    path = tmp_path / ".env-secrets"
    path.write_text(
        "\n".join(
            [
                f"TELEGRAM_BOT_TOKEN={encoded('123456789:abcdefghijklmnopqrstuvwxyz_ABCD')}",
                f"ALLOWED_USER_IDS={encoded('123456789,987654321')}",
                f"ADMIN_USER_ID={encoded('123456789')}",
                f"GITHUB_TOKEN={encoded('must-not-be-loaded')}",
            ]
        ),
        encoding="utf-8",
    )

    secrets = load_codespaces_secrets(path)

    assert secrets == {
        "TELEGRAM_BOT_TOKEN": "123456789:abcdefghijklmnopqrstuvwxyz_ABCD",
        "ALLOWED_USER_IDS": "123456789,987654321",
        "ADMIN_USER_ID": "123456789",
    }


def test_load_codespaces_secrets_accepts_plain_values(tmp_path: Path) -> None:
    path = tmp_path / ".env-secrets"
    path.write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=123456789:abcdefghijklmnopqrstuvwxyz_ABCD",
                "ALLOWED_USER_IDS=123456789,987654321",
                "ADMIN_USER_ID=123456789",
            ]
        ),
        encoding="utf-8",
    )

    secrets = load_codespaces_secrets(path)
    assert secrets["ADMIN_USER_ID"] == "123456789"


def test_load_codespaces_secrets_rejects_invalid_values(tmp_path: Path) -> None:
    path = tmp_path / ".env-secrets"
    path.write_text(
        "\n".join(
            [
                f"TELEGRAM_BOT_TOKEN={encoded('not-a-token')}",
                f"ALLOWED_USER_IDS={encoded('123456789')}",
                f"ADMIN_USER_ID={encoded('123456789')}",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN has an invalid format"):
        load_codespaces_secrets(path)
