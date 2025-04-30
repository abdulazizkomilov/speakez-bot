import logging

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup
)

mode_type = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🗣️ IELTS Speaking", callback_data="mode_ielts")],
        [InlineKeyboardButton(text="🗣️ Multilevel Speaking", callback_data="mode_multilevel")],
        [InlineKeyboardButton(text="🗑 Remove", callback_data="remove_item")]
    ]
)

modes_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🗣️ Full Mock Speaking", callback_data="categories_full_speaking")],
        [InlineKeyboardButton(text="💬 Speaking Practice", callback_data="categories_speaking_practice")],
        [InlineKeyboardButton(text="🗑 Remove", callback_data="remove_item")]
    ]
)

full_exam_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🗣️ Full Mock Speaking", callback_data="full_speaking")],
        [InlineKeyboardButton(text="🗑 Remove", callback_data="remove_item")]
    ]
)

parts_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔹 Part 1", callback_data="part_1"),
            InlineKeyboardButton(text="🔹 Part 2", callback_data="part_2"),
            InlineKeyboardButton(text="🔹 Part 3", callback_data="part_3")
        ],
        [InlineKeyboardButton(text="🗑 Remove", callback_data="remove_item")]
    ]
)

CATEGORIES = [
    "Random Questions 🌀",
    "Animals-and-Pets 🐶",
    "Books-and-Reading 📖",
    "Childhood-and-Memories 🧸",
    "Daily-Routine-and-Lifestyle ⏰",
    "Education-and-Learning 📚",
    "Environment-and-Climate-Change 🌍",
    "Environment-and-Nature 🌿",
    "Family-and-Relationships 👨‍👩👧‍",
    "Fashion-and-Clothing 👗",
    "Festivals-and-Celebrations 🎉",
    "Food-and-Cooking 🍽",
    "Food-and-Nutrition 🥗",
    "Health-and-Fitness 💪",
    "Hobbies-and-Free-Time 🎨",
    "Homes-and-Living-Spaces 🏠",
    "Movies-and-Cinema 🎬",
    "Music-and-Entertainment 🎵",
    "Public-Transport-and-Infrastructure 🚉",
    "Science-and-Space 🧬",
    "School-and-University 🏫",
    "Shopping-and-Consumer-Habits 🛍",
    "Social-Media-and-Communication 📱",
    "Sports-and-Physical-Activities 🏆",
    "Technology-and-Innovation 🤖",
    "Technology-and-the-Internet 💻",
    "Transport-and-Commuting 🚗",
    "Travel-and-Holidays ✈️",
    "Travel-and-Tourism 🗺",
    "Weather-and-Seasons ⛅",
    "Work-and-Career 💼"
]

ITEMS_PER_PAGE = 5


def get_category_keyboard(page: int = 0) -> InlineKeyboardMarkup | None:
    """Creates an inline keyboard with paginated categories."""
    try:
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        categories_subset = CATEGORIES[start_idx:end_idx]

        keyboard_buttons = [
            [InlineKeyboardButton(text=category, callback_data=f"category_{category}")]
            for category in categories_subset
        ]

        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page - 1}"))
        if end_idx < len(CATEGORIES):
            pagination_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{page + 1}"))

        back_button = [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]

        if pagination_buttons:
            if page == 0 and len(pagination_buttons) == 1:
                keyboard_buttons.append(back_button + pagination_buttons)
            elif len(pagination_buttons) == 1:
                keyboard_buttons.append(pagination_buttons + back_button)
            else:
                keyboard_buttons.append(pagination_buttons)
                keyboard_buttons.append(back_button)
        else:
            keyboard_buttons.append(back_button)

        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    except Exception as e:
        logging.error(f"Error in get_category_keyboard: {e}")


def get_part_keyboard(call_data: str = None) -> InlineKeyboardMarkup:
    """Creates a keyboard for selecting parts after choosing a category."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔹 Part 1", callback_data="part_1"),
                InlineKeyboardButton(text="🔹 Part 2", callback_data="part_2"),
                InlineKeyboardButton(text="🔹 Part 3", callback_data="part_3")
            ],
            [InlineKeyboardButton(text="🔙 Back to categories", callback_data=f"categories_{call_data}")]
        ]
    )


def invite_func(invite_link):
    """Returns an inline keyboard with a button to share the invite link"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Share Your Invite Link", switch_inline_query=invite_link)]
        ]
    )
    return keyboard
