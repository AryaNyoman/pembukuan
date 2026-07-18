from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.security import is_allowed_user


class AllowlistMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.events: defaultdict[int, deque[float]] = defaultdict(deque)
        self.window_seconds = 60.0
        self.max_events = 40

    def _rate_limited(self, user_id: int) -> bool:
        now = monotonic()
        bucket = self.events[user_id]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_events:
            return True
        bucket.append(now)
        return False

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        if not is_allowed_user(user_id, self.settings.allowed_user_ids):
            if isinstance(event, Message):
                await event.answer("Akses ditolak.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Akses ditolak.", show_alert=True)
            return None
        if self._rate_limited(user_id):
            if isinstance(event, Message):
                await event.answer("Terlalu banyak permintaan. Coba lagi sebentar.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Terlalu banyak permintaan.", show_alert=True)
            return None
        return await handler(event, data)
