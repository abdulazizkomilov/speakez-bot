from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

mode_type = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗣️ Multilevel Speaking")],
        [KeyboardButton(text="🗣️ IELTS Speaking")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)
