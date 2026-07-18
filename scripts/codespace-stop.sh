#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path
import os
import signal

stopped = 0
for process in Path("/proc").iterdir():
    if not process.name.isdigit():
        continue
    try:
        argv = [
            part.decode(errors="replace")
            for part in (process / "cmdline").read_bytes().split(b"\0")
            if part
        ]
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    is_bot = any(
        argv[index : index + 2] in (["-m", "app.main"], ["-m", "app.codespaces_runtime"])
        for index in range(len(argv) - 1)
    )
    if not is_bot:
        continue
    try:
        os.kill(int(process.name), signal.SIGTERM)
        stopped += 1
    except ProcessLookupError:
        continue

print(f"Bot processes stopped: {stopped}")
PY

# Stopping the Codespace itself is done from GitHub Codespaces UI or CLI.
# This script never prints Codespaces secret values.
