import logging

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta

from loader import dp, db
from keyboards.default.speaking import mode_type
from states.promocode import PromoState
from keyboards.inline.speaking import (
    parts_keyboard, modes_keyboard,
    full_exam_keyboard
)
from utils.redis import (
    store_item, get_item, get_streaming_status,
    set_streaming_status, delete_item,
    set_message
)


@dp.message(F.text == "/promocode")
async def ask_for_promocode(message: Message, state: FSMContext):
    await message.answer("Send promocode:")
    await state.set_state(PromoState.waiting_for_code)


@dp.message(PromoState.waiting_for_code)
async def handle_promocode(message: Message, state: FSMContext):
    user_input = message.text.strip().lower()
    user_id = message.from_user.id

    valid_code = "naimov_akmalkhan"

    if user_input == valid_code:
        user_data = await db.get_user(user_id)
        used_codes = user_data.get("used_promo_codes", [])

        if valid_code in used_codes:
            await message.answer("⚠️ You've already used this promo code.")
        else:
            now = datetime.utcnow()
            premium_until = now + timedelta(weeks=1)
            await db.user_collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "is_paid": True,
                        "payment_date": now,
                        "payment_type": "promocode",
                        "payment_valid_date": premium_until
                    },
                    "$addToSet": {"used_promo_codes": valid_code}
                }
            )
            await message.answer("🎉 You received a week of premium!")
    else:
        await message.answer("❌ Invalid promo code.")

    await state.clear()


@dp.message(F.text == "🗣️ IELTS Speaking")
async def handle_ielts(message: Message):
    try:
        user_id = message.from_user.id
        await store_item(user_id, "ielts", "type")
        await send_mode_selection_menu(message)
    except Exception as e:
        logging.error(f"Error in IELTS Speaking handler: {e}")
        await message.answer("An error occurred while processing your request.")


@dp.message(F.text == "🗣️ Multilevel Speaking")
async def handle_multilevel(message: Message):
    try:
        user_id = message.from_user.id
        await store_item(user_id, "multilevel", "type")
        await send_mode_selection_menu(message)
    except Exception as e:
        logging.error(f"Error in Multilevel Speaking handler: {e}")
        await message.answer("An error occurred while processing your request.")


@dp.message(Command(commands=["modes"]))
async def speaking_command(message: Message):
    """Switch between practice modes"""
    try:
        await send_mode_type_menu(message)
    except Exception as e:
        logging.error(f"Error in /modes command: {e}")
        await message.answer("An error occurred while processing your request.")


@dp.callback_query(F.data == "speaking_parts")
async def speaking_parts_selection(callback_query: CallbackQuery):
    """Allow the user to select specific parts of the IELTS Speaking exam"""
    try:
        await callback_query.message.edit_text(
            "Select which part of the exam you want to practice:",
            reply_markup=parts_keyboard
        )
    except Exception as e:
        logging.error(f"Error in speaking_parts callback: {e}")
        await callback_query.answer("An error occurred while processing your request.")


@dp.callback_query(F.data == "main_menu")
async def go_main_menu(callback_query: CallbackQuery):
    try:
        await callback_query.message.edit_text(
            "📌 <b>Choose one of the speaking modes:</b>",
            reply_markup=modes_keyboard
        )
    except Exception as e:
        logging.error(f"Error in /modes command: {e}")
        await callback_query.message.answer("An error occurred while processing your request.")


async def send_full_exam_selection_menu(message: Message):
    """Send part selection menu"""
    try:
        await message.answer(
            "Start Full Speaking Mock Exam:",
            reply_markup=full_exam_keyboard
        )
    except Exception as e:
        logging.error(f"Error in send_full_exam_selection_menu: {e}")
        await message.answer("An error occurred while sending the mode selection menu.")


async def send_part_selection_menu(message: Message):
    """Send part selection menu"""
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        await message.answer("📌 <b>Choose a part:</b>", reply_markup=parts_keyboard)
    except Exception as e:
        logging.error(f"Error in send_part_selection_menu: {e}")
        await message.answer("An error occurred while sending the part selection menu.")


async def send_mode_selection_menu(message: Message):
    """Send mode selection menu"""
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        await message.answer(
            "📌 <b>Choose one of the speaking modes:</b>",
            reply_markup=modes_keyboard
        )
    except Exception as e:
        logging.error(f"Error in send_mode_selection_menu: {e}")
        await message.answer("An error occurred while sending the mode selection menu.")


async def send_mode_type_menu(message: Message):
    """Send mode selection menu"""
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        await message.answer(
            "📌 <b>Choose one of these categories:</b>",
            reply_markup=mode_type
        )
    except Exception as e:
        logging.error(f"Error in send_mode_selection_menu: {e}")
        await message.answer("An error occurred while sending the mode selection menu.")
