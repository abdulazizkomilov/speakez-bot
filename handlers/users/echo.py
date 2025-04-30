from aiogram.types import Message
from aiogram.enums import ParseMode

from loader import dp


@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        text = "<b>Unknown message type!</b>\n\n<b>Use /modes to switch between practice modes.</b>"
        await message.answer(text, parse_mode=ParseMode.HTML)
    except TypeError:
        await message.answer("Nice try!")
