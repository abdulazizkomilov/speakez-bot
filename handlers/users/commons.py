import re
import logging

from aiogram import F
from aiogram.enums import ParseMode, ChatAction
from aiogram.types import CallbackQuery, Message

from loader import dp
from utils.commons import send_ogg_voice  # fetch_tenor_gif
from utils.redis import store_item, get_item
from utils.question_generator import get_random_question
from keyboards.inline.speaking import (
    parts_keyboard
)


@dp.callback_query(F.data == "back_to_parts")
async def back_to_part_selection(callback_query: CallbackQuery):
    """Returns to part selection menu by updating the same message"""
    try:
        await callback_query.message.edit_text(
            "Choose a part of the exam to practice:",
            reply_markup=parts_keyboard
        )
    except Exception as e:
        logging.error(f"Error in back_to_part_selection: {e}")
        await callback_query.answer("Error returning to part selection.")


@dp.callback_query(F.data == "remove_item")
async def remove_question(callback_query: CallbackQuery):
    """Removes the question by deleting the message"""
    try:
        await callback_query.message.delete()
    except Exception as e:
        logging.error(f"Error in remove_question: {e}")


# async def move_to_next_part(message: Message, next_part_state: str):
#     """Move the user to the next part of the IELTS exam"""
#     try:
#         await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
#
#         user_id = message.from_user.id
#         part_number = 2 if next_part_state == SpeakingExamState.PART_2 else 3
#         category_name = await get_item(user_id, "category")
#
#         result = await get_random_question(part_number, category_name)
#         question = result.get("question")
#
#         await store_item(user_id, question, "question")
#         await store_item(user_id, next_part_state, "state")
#
#         await store_questions_full_speaking(
#             message,
#             user_id,
#             message.chat.id,
#             category_name,
#             part_number
#         )
#
#     except Exception as e:
#         logging.error(f"Error in move_to_next_part: {e}")
#         await message.answer("An error occurred while moving to the next part.")


async def audio_sender(callback_query: CallbackQuery, audio_base64):
    try:
        await send_ogg_voice(callback_query.message, audio_base64)
    except Exception as audio_error:
        logging.error(f"Error in audio_sender: {audio_error}", exc_info=True)


# async def sender(callback_query: CallbackQuery, user_id: int, chat_id: int, category_name: str):
#     try:
#         result = await get_random_question(1, category_name)
#         question = result.get("question")
#
#         await callback_query.message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
#         await store_item(user_id, question, "question")
#         await store_item(user_id, SpeakingExamState.PART_1, "state")
#
#         await callback_query.message.edit_text(
#             f"IELTS Speaking Part 1 ```Question:\n{question}```",
#             parse_mode=ParseMode.MARKDOWN_V2
#         )
#
#         audio_base64 = result.get("audio_base64")
#         if audio_base64:
#             await audio_sender(callback_query, audio_base64)
#     except Exception as e:
#         logging.error(f"Error in sender: {e}")


async def store_questions_full_speaking(
        message: Message | CallbackQuery,
        user_id: int,
        chat_id: int,
        category_name: str,
        part_number: int,
        mode_type_name: str
):
    try:
        if isinstance(message, CallbackQuery):
            if mode_type_name is None:
                await message.message.bot.send_message(
                    chat_id,
                    "Please select a mode first \modes.",
                    parse_mode="HTML"
                )
        else:
            if mode_type_name is None:
                await message.bot.send_message(
                    chat_id,
                    "Please select a mode first \modes.",
                    parse_mode="HTML"
                )

        result = await get_random_question(part_number, category_name, mode_type_name)
        question = result.get("question")

        bot = message.bot
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        await store_item(user_id, category_name, "category")

        await store_item(user_id, question, f"full_speaking_question_{part_number}")

        text = f"IELTS Speaking Part {part_number} ```Question:\n{question}```"
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            audio_base64 = result.get("audio_base64")
            if audio_base64:
                try:
                    await send_ogg_voice(message.message, audio_base64)
                except Exception as audio_error:
                    logging.error(f"Error in audio_sender: {audio_error}", exc_info=True)
            # try:
            #     category_name = await get_item(user_id, "category")
            #     gif_url = await fetch_tenor_gif(category_name)
            #     if gif_url:
            #         await message.message.answer_animation(gif_url)
            # except Exception as git_error:
            #     logging.error(f"Error in git_error: {git_error}", exc_info=True)
        else:
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            audio_base64 = result.get("audio_base64")
            if audio_base64:
                try:
                    await send_ogg_voice(message, audio_base64)
                except Exception as audio_error:
                    logging.error(f"Error in audio_sender: {audio_error}", exc_info=True)

            # try:
            #     category_name = await get_item(user_id, "category")
            #     gif_url = await fetch_tenor_gif(category_name)
            #     if gif_url:
            #         await message.answer_animation(gif_url)
            # except Exception as git_error:
            #     logging.error(f"Error in audio_sender: {git_error}", exc_info=True)

    except Exception as e:
        logging.exception(f"Error in store_questions_full_speaking: {e}")


def escape_markdown(text: str) -> str:
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


async def store_questions_full_speaking_multilevel(
        message: Message | CallbackQuery,
        user_id: int,
        chat_id: int,
        category_name: str,
        part_number: int,
        mode_type_name: str
):
    try:
        if isinstance(message, CallbackQuery):
            if mode_type_name is None:
                await message.message.bot.send_message(
                    chat_id,
                    "Please select a mode first \modes.",
                    parse_mode="HTML"
                )
        else:
            if mode_type_name is None:
                await message.bot.send_message(
                    chat_id,
                    "Please select a mode first \modes.",
                    parse_mode="HTML"
                )

        if part_number in (1, 2, 3, 4, 5, 6):
            result = await get_random_question(1, category_name, mode_type_name)
        elif part_number == 7:
            result = await get_random_question(2, category_name, mode_type_name)
        elif part_number == 8:
            result = await get_random_question(3, category_name, mode_type_name)

        question = result.get("question")
        escaped_question = escape_markdown(question)

        bot = message.bot
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        await store_item(user_id, category_name, "category")
        await store_item(user_id, question, f"full_speaking_question_{part_number}")

        part_titles = {
            1: "Multilevel Speaking Part 1.1 Q:1\nTime: 10 - 30 sec",
            2: "Multilevel Speaking Part 1.1 Q:2\nTime: 10 - 30 sec",
            3: "Multilevel Speaking Part 1.1 Q:3\nTime: 10 - 30 sec",
            4: "Multilevel Speaking Part 1.2 Q:1\nTime: 15 - 45 sec",
            5: "Multilevel Speaking Part 1.2 Q:2\nTime: 10 - 30 sec",
            6: "Multilevel Speaking Part 1.2 Q:3\nTime: 10 - 30 sec",
            7: "Multilevel Speaking Part 2\nTime: 1 min - 2 min",
            8: "Multilevel Speaking Part 3\nTime: 1 min - 2 min",
        }

        title = escape_markdown(part_titles.get(part_number, "Multilevel Speaking"))
        text = f"*{title}*\n\n*Question:*\n```\n{escaped_question}\n```"

        audio_base64 = result.get("audio_base64")

        if isinstance(message, CallbackQuery):
            await message.message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
            if audio_base64:
                try:
                    await send_ogg_voice(message.message, audio_base64)
                except Exception as audio_error:
                    logging.error(f"Error in audio_sender: {audio_error}", exc_info=True)

        else:
            await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
            if audio_base64:
                try:
                    await send_ogg_voice(message, audio_base64)
                except Exception as audio_error:
                    logging.error(f"Error in audio_sender: {audio_error}", exc_info=True)

    except Exception as e:
        logging.exception(f"Error in store_questions_full_speaking: {e}")
