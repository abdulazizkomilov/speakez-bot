import logging

from aiogram.filters import Command
from aiogram.types import Message

from loader import dp


@dp.message(Command(commands=["help"]))
async def help_command(message: Message):
    try:
        await message.answer(
            "📚 <b>Need Assistance?</b>\n\n"
            "I'm here to help you enhance your IELTS Speaking and Writing skills! 🎯\n"
            "You can practice different sections, take a full mock test, or switch between practice modes.\n\n"
            "✨ <b>Available Commands:</b>\n\n"
            "🔹 /modes – Switch between different practice modes\n"
            "🔹 /premium – Upgrade to Premium for more benefits\n\n"
            "🔹 <b>Usage Limits:</b>\n"
            "   - 🆓 Free Users: <b>3 voice messages per day</b>\n"
            "   - 🌟 Premium Users: <b>25 voice messages per day</b>\n\n"
            "🚀 Let's start practicing and boost your IELTS score! 😊"
            "🚀 Ready to boost your IELTS skills?\n"
            "Choose a command and let's begin! 😊"
        )
    except Exception as e:
        logging.error(f"Error in /help command: {e}")
        await message.answer("⚠️ An error occurred while processing your request. Please try again later.")
