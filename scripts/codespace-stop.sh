#!/usr/bin/env bash
set -euo pipefail

pkill -f 'python -m app.main' 2>/dev/null || true
printf '%s\n' 'Bot process stopped.'

# Stopping the Codespace itself is done from GitHub Codespaces UI or CLI.
# Do not delete the Codespace unless pushed work and backups are safe.

# This script never prints TELEGRAM_BOT_TOKEN.
