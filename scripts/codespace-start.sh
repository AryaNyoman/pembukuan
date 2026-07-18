#!/usr/bin/env bash
set -euo pipefail

: "${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN as a GitHub Codespaces secret first}"
: "${ALLOWED_USER_IDS:?Set ALLOWED_USER_IDS as a GitHub Codespaces secret first}"
: "${ADMIN_USER_ID:?Set ADMIN_USER_ID as a GitHub Codespaces secret first}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/bookkeeping.db}"
export APP_TIMEZONE="${APP_TIMEZONE:-Asia/Makassar}"
export CURRENCY="${CURRENCY:-IDR}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export BACKUP_DIR="${BACKUP_DIR:-./backups}"
export EXPORT_DIR="${EXPORT_DIR:-./exports}"
export EXPORT_TTL_SECONDS="${EXPORT_TTL_SECONDS:-3600}"
export REMINDER_HOUR="${REMINDER_HOUR:-21}"

mkdir -p data backups exports
alembic upgrade head
exec python -m app.main

# This script intentionally uses the secret from the environment and never writes .env.
