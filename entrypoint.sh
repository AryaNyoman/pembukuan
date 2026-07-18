#!/bin/sh
set -eu

alembic upgrade head
exec python -m app.main

# The image never receives .env; credentials are injected at runtime.
