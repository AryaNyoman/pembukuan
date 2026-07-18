from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Create a scheduler; jobs are registered only after bot dependencies exist."""
    return AsyncIOScheduler()


def start_scheduler(scheduler: AsyncIOScheduler) -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
