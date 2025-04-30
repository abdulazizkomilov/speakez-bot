from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup
)

admin_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👥 Number of Users", callback_data="get_users_count")],
        [InlineKeyboardButton(text="📊 Users Statistics", callback_data="get_all_users_statistics")],
        
    ]
)
