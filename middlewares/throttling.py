from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime, timedelta


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        super().__init__()
        self.rate_limit = timedelta(seconds=rate_limit)
        self.last_called = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.utcnow()

        if user_id in self.last_called:
            last_called_time = self.last_called[user_id]
            if now - last_called_time < self.rate_limit:
                if isinstance(event, Message):
                    await event.answer("🚫 Too many requests! Please wait a moment before trying again.")
                return

        self.last_called[user_id] = now
        return await handler(event, data)
