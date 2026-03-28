from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: float = 2.0) -> None:
        self.limit_seconds = limit_seconds
        self._last_hits: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last_hits.get(user_id)
        if last is not None and (now - last) < self.limit_seconds:
            return await self._notify_too_fast(event)

        self._last_hits[user_id] = now
        return await handler(event, data)

    @staticmethod
    def _extract_user_id(event: TelegramObject) -> int | None:
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            return event.from_user.id
        return None

    @staticmethod
    async def _notify_too_fast(event: TelegramObject) -> Any:
        if isinstance(event, Message):
            return await event.answer("Juda tez yuboryapsiz. Iltimos, 1-2 soniya kuting.")
        if isinstance(event, CallbackQuery):
            return await event.answer("Biroz sekinroq :)", show_alert=False)
        return None
