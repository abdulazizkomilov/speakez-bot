import logging

from aiogram import Bot
from aiogram import BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from typing import Callable, Dict, Any, Awaitable

from data.config import REQUIRED_CHANNELS


async def check_user_subscription(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Check if the user is subscribed to a specific channel."""
    try:
        member_status: ChatMember = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)

        if member_status.status in ("member", "administrator", "creator"):
            return True

        return False
    except Exception as e:
        logging.error(f"Error in check_user_subscription: {e}")
        return False


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self,
                       handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
                       event: Message,
                       data: Dict[str, Any]) -> Any:
        try:
            if event.text == "/start":
                return await handler(event, data)

            user_id = event.from_user.id
            not_subscribed_channels = []

            if REQUIRED_CHANNELS:
                for channel in REQUIRED_CHANNELS:
                    if not await check_user_subscription(event.bot, user_id, channel["channel_id"]):
                        try:
                            chat = await event.bot.get_chat(channel["channel_id"])
                            channel_name = chat.title
                        except Exception as e:
                            logging.warning(f"Couldn't fetch channel title: {e}")
                            channel_name = channel["channel_id"]  # fallback

                        not_subscribed_channels.append({
                            "channel_id": channel["channel_id"],
                            "link": channel["link"],
                            "name": channel_name
                        })

                if not_subscribed_channels:
                    buttons = [
                        [InlineKeyboardButton(
                            text=f"🔗 {channel['name']}",
                            url=channel["link"]
                        )] for channel in not_subscribed_channels
                    ]

                    buttons.append([InlineKeyboardButton(text="✅ I have subscribed", callback_data="subscribed")])

                    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                    await event.answer(
                        "🚨 You need to subscribe to the following channels:",
                        reply_markup=inline_keyboard
                    )
                else:
                    await handler(event, data)
            else:
                await handler(event, data)
        except Exception as e:
            logging.error(f"Error in SubscriptionMiddleware: {e}")
            return await handler(event, data)
