import logging

from aiogram import F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)

from loader import dp
from data.config import REQUIRED_CHANNELS
from middlewares.channels import check_user_subscription


@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    """Check if the user has subscribed to all required channels"""
    try:
        user_id = callback.from_user.id
        not_subscribed_channels = []

        for channel in REQUIRED_CHANNELS:
            if not await check_user_subscription(callback.bot, user_id, channel["channel_id"]):
                not_subscribed_channels.append(channel)

        if not_subscribed_channels:
            buttons = [
                [InlineKeyboardButton(
                    text=f"Subscribe to {channel['channel_id']}",
                    url=channel["link"]
                )] for channel in not_subscribed_channels
            ]

            buttons.append([InlineKeyboardButton(text="✅ I have subscribed", callback_data="subscribed")])

            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            try:
                if callback.message.reply_markup != inline_keyboard:
                    await callback.answer("🚨 You still need to subscribe to the following channels.", show_alert=True)
            except Exception as e:
                logging.error(f"Error in check_subscription: {e}")
        else:
            if callback.message.text != "🎉 Thank you for subscribing! You can now use the bot.":
                await callback.message.edit_text(
                    "🎉 Thank you for subscribing! You can now use the bot."
                )
    except Exception as e:
        logging.error(f"Error in check_subscription: {e}")


@dp.callback_query(F.data == "subscribed")
async def confirm_subscription(callback: CallbackQuery):
    """Handle the confirmation after the user presses the 'I have subscribed' button"""
    try:
        await check_subscription(callback)
    except Exception as e:
        logging.error(f"Error in confirm_subscription: {e}")
