import logging
import redis.asyncio as redis

from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable

from loader import db, REDIS_URL
from utils.celery import (
    check_user_exists,
    send_invite_notification_to_referrer
)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        try:
            user_id = event.from_user.id
            chat_id = event.chat.id
            username = event.from_user.username or ""
            first_name = event.from_user.first_name or ""
            last_name = event.from_user.last_name or ""

            if event.text and event.text.startswith("/start"):
                await self.create_or_update_user(user_id, chat_id, username, first_name, last_name, event.text)
            else:
                check_user_exists.delay(user_id, chat_id, username, first_name, last_name)

            return await handler(event, data)
        except Exception as e:
            logging.error(f"Error in UserMiddleware: {e}")
            return await handler(event, data)

    @staticmethod
    async def create_or_update_user(user_id, chat_id, username, first_name, last_name, text):
        try:
            user_exists = await db.check_if_user_exists(user_id)
            referred_by = None

            parts = text.split()
            if len(parts) > 1 and parts[1].isdigit():
                referred_by = int(parts[1])

            if not user_exists:
                await db.add_new_user(
                    user_id, chat_id, username, first_name, last_name
                )

                if referred_by and referred_by != user_id:
                    await db.user_collection.update_one(
                        {"_id": referred_by},
                        {"$inc": {"invited_users": 1}}
                    )
                    await db.user_collection.update_one(
                        {"_id": user_id},
                        {"$set": {"referred_by": referred_by}}
                    )

                    send_invite_notification_to_referrer.delay(referred_by, user_id)
                
            else:
                await db.update_user_info(user_id, chat_id, username, first_name, last_name)

            await db.update_user_last_interaction(user_id)
        except Exception as e:
            logging.error(f"Error while creating/updating user directly: {e}")


class StreamingGuardMiddleware(BaseMiddleware):
    def __init__(self):
        self.redis = redis_client = redis.from_url(REDIS_URL)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Any],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        chat_id = event.chat.id

        try:
            status = await self.redis.get(f"streaming:{chat_id}")
        except Exception as e:
            logging.error(f"Failed to get streaming status: {e}")
            return await handler(event, data)

        if status == b'in_progress':
            await event.answer("<i>⏳ Please wait until your previous message is finished!</i>", parse_mode="HTML")
            return

        return await handler(event, data)
