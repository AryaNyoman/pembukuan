FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN useradd --create-home --uid 10001 appuser
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY entrypoint.sh ./entrypoint.sh
RUN pip install --no-cache-dir .
RUN chmod +x /app/entrypoint.sh && mkdir -p /app/data /app/exports /app/backups && chown -R appuser:appuser /app
USER appuser

VOLUME ["/app/data", "/app/exports", "/app/backups"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import sqlite3, os; p='data/bookkeeping.db'; c=sqlite3.connect(p); c.execute('select 1'); c.close() if os.path.exists(p) else None"
ENTRYPOINT ["/app/entrypoint.sh"]

# Token is injected at runtime with --env-file; never COPY .env.
