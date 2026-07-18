#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/pembukuan
mkdir -p data exports backups

# Non-secret runtime defaults. Codespaces secrets remain environment-only.
export ALLOWED_USER_IDS="${ALLOWED_USER_IDS:-1105904688,6373275001,7427314023}"
export ADMIN_USER_ID="${ADMIN_USER_ID:-1105904688}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./data/bookkeeping.db}"
export APP_TIMEZONE="${APP_TIMEZONE:-Asia/Makassar}"
export CURRENCY="${CURRENCY:-IDR}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export BACKUP_DIR="${BACKUP_DIR:-./backups}"
export EXPORT_DIR="${EXPORT_DIR:-./exports}"
export EXPORT_TTL_SECONDS="${EXPORT_TTL_SECONDS:-3600}"
export REMINDER_HOUR="${REMINDER_HOUR:-21}"

.venv/bin/python -m alembic upgrade head

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  printf '%s\n' 'TELEGRAM_BOT_TOKEN belum tersedia; bot tidak dijalankan.'
  exit 0
fi

if pgrep -f 'python -m app.main' >/dev/null 2>&1; then
  printf '%s\n' 'Bot sudah berjalan; tidak membuat proses polling kedua.'
  exit 0
fi

nohup env PATH="$PWD/.venv/bin:$PATH" bash scripts/codespace-start.sh \
  > /tmp/bookkeeping-bot.log 2>&1 &
printf '%s\n' "Bot dimulai dengan PID $!."
