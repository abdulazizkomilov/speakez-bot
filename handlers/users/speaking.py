import logging
# import asyncio

from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.enums import ChatAction
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from loader import dp, db, KAFKA_URL
from data import config
from states.speaking import SpeakingExamState, MultilevelSpeakingFullState
from utils.question_generator import get_random_question
# from utils.audio_generator import transcribe_voice_message
from utils.gemini.gemini import transcribe_voice_message
from utils.commons import can_send_voice, send_part  # fetch_tenor_gif
from handlers.users.menu import send_mode_selection_menu
from utils.prompt_generator import (
    build_openai_prompt,
    build_openai_prompt_full_speaking,
    build_openai_prompt_full_speaking_multilevel
)
from handlers.users.commons import (
    audio_sender, store_questions_full_speaking,
    store_questions_full_speaking_multilevel
)
from keyboards.inline.speaking import (
    get_category_keyboard, get_part_keyboard,
    parts_keyboard
)
# from handlers.users.menu import (
#     send_mode_selection_menu, send_part_selection_menu
# )
from utils.redis import (
    store_item, get_item, get_streaming_status,
    set_streaming_status, delete_item,
    set_message
)

USER_SELECTED_CATEGORY = {}
KAFKA_BOOTSTRAP_SERVERS = KAFKA_URL
KAFKA_TOPIC = config.KAFKA_TOPIC


async def count_checker(callback_query: CallbackQuery, user_id: int, chat_id: int):
    daily_voice_count = await db.get_user_daily_count(user_id)
    mode_type_name = await get_item(user_id, "type")

    limits = {
        "ielts": 22,
        "multilevel": 17
    }

    if mode_type_name in limits and daily_voice_count > limits[mode_type_name]:
        text = "There is no daily limit for the full speaking exam."

        try:
            await callback_query.message.delete()
        except Exception as e:
            logging.error(f"Error in remove_question: {e}")

        if daily_voice_count < 20:
            text += f"\n\n🚀 Let's start practicing with parts and boost your {mode_type_name.upper()} score! 😊"
            await callback_query.message.bot.send_message(
                chat_id=chat_id,
                text=text
            )
        else:
            await callback_query.message.bot.send_message(
                chat_id=chat_id,
                text=text
            )


@dp.callback_query(F.data.startswith("mode_"))
async def mode_type(callback_query: CallbackQuery):
    """Handles mode selection menu."""
    try:
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        _, mode_name = callback_query.data.split("_", 1)  # noqa

        can_send, limit_message = await can_send_voice(user_id)
        if not can_send:
            await callback_query.message.answer(limit_message)
            return
        
        await store_item(user_id, mode_name, "type")
        await send_mode_selection_menu(callback_query.message)

    except Exception as e:
        logging.error(f"Error in categories callback: {e}")
        await callback_query.answer("An error occurred while processing your request.")


@dp.callback_query(F.data.startswith("categories_"))
async def categories_question(callback_query: CallbackQuery):
    """Handles category selection menu."""
    try:
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        _, mode_name = callback_query.data.split("_", 1)  # noqa

        if mode_name == "full_speaking":
            is_chance = await db.get_user_attribute(user_id, "full_speaking")
            is_paid = await db.get_user_attribute(user_id, "is_paid")

            if not is_paid and not is_chance:
                text = (
                    "🔒<b>This feature is available for PREMIUM subscribers only!</b>\n\n"
                    "✨<b>Unlock exclusive benefits</b> 🚀\n\n"
                    "👉 /premium - <b>Upgrade to PREMIUM</b>"
                )
                await callback_query.message.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                return
            else:
                await count_checker(callback_query, user_id, chat_id)

        can_send, limit_message = await can_send_voice(user_id)
        if not can_send:
            await callback_query.message.answer(limit_message)
            return

        await store_item(user_id, mode_name, "mode")

        keyboard = get_category_keyboard(page=0)
        await callback_query.message.edit_text(
            "📌 <b>Choose one of the speaking categories:</b>",
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Error in categories callback: {e}")
        await callback_query.answer("An error occurred while processing your request.")


@dp.callback_query(F.data.startswith("category_"))
async def handle_category_selection(callback_query: CallbackQuery):
    """Handles when a user selects a category and shows parts."""
    try:
        user_id = callback_query.from_user.id
        chat_id = callback_query.message.chat.id
        category_name = callback_query.data.split("_", 1)[1]  # noqa

        await store_item(user_id, category_name, "category")
        mode_name = await get_item(user_id, "mode")

        if category_name is None:
            await callback_query.answer("Please select a category first.", show_alert=True)
            return

        if mode_name is None:
            await callback_query.answer("Please select a mode first.", show_alert=True)
            return
        
        mode_type_name = await get_item(user_id, "type")
        if mode_type_name is None:
            await callback_query.answer("Please select a mode first \modes.", show_alert=True)
            return

        can_send, limit_message = await can_send_voice(user_id)

        if not can_send:
            await callback_query.message.answer(limit_message)
            return

        if mode_name == "speaking_practice":
            keyboard = get_part_keyboard(mode_name)
            await callback_query.message.edit_text(
                f"<b>Selected Category:</b> {category_name}\n\n📌 <b>Now, select a part:</b>",
                reply_markup=keyboard
            )
        elif mode_name == "full_speaking" and mode_type_name == "ielts":
            is_chance = await db.get_user_attribute(user_id, "full_speaking")
            is_paid = await db.get_user_attribute(user_id, "is_paid")
            if not is_paid and not is_chance:
                text = (
                    "🔒<b>This feature is available for PREMIUM subscribers only!</b>\n\n"
                    "✨<b>Unlock exclusive benefits</b> 🚀\n\n"
                    "👉 /premium - <b>Upgrade to PREMIUM</b>"
                )

                await callback_query.answer("Get PREMIUM now!")

                await callback_query.message.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                return

            await count_checker(callback_query, user_id, chat_id)

            await store_item(user_id, SpeakingExamState.FULL_SPEAKING, "state")
            await store_questions_full_speaking(callback_query, user_id, chat_id, category_name, 1, mode_type_name)
        elif mode_name == "full_speaking" and mode_type_name == "multilevel":
            is_chance = await db.get_user_attribute(user_id, "full_speaking")
            is_paid = await db.get_user_attribute(user_id, "is_paid")
            if not is_paid and not is_chance:
                text = (
                    "🔒<b>This feature is available for PREMIUM subscribers only!</b>\n\n"
                    "✨<b>Unlock exclusive benefits</b> 🚀\n\n"
                    "👉 /premium - <b>Upgrade to PREMIUM</b>"
                )

                await callback_query.answer("Get PREMIUM now!")

                await callback_query.message.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                return

            await count_checker(callback_query, user_id, chat_id)

            await store_item(user_id, MultilevelSpeakingFullState.FULL_SPEAKING_MULTILEVEL, "state")
            await store_questions_full_speaking_multilevel(callback_query, user_id, chat_id, category_name, 1, mode_type_name)
    except Exception as e:
        logging.error(f"Error in category selection callback: {e}")
        await callback_query.answer("An error occurred while processing your request.")


@dp.callback_query(F.data.startswith("page_"))
async def change_page(callback_query: CallbackQuery):
    """Handles pagination for categories."""
    try:
        page = int(callback_query.data.split("_")[1])  # noqa
        keyboard = get_category_keyboard(page)
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Error in pagination callback: {e}")
        await callback_query.answer("An error occurred while processing your request.")


@dp.callback_query(F.data.startswith("part_"))
async def handle_part_selection(callback_query: CallbackQuery):
    """Handles specific part selection after category selection."""
    try:
        user_id = callback_query.from_user.id

        await callback_query.message.bot.send_chat_action(
            chat_id=callback_query.message.chat.id,
            action=ChatAction.TYPING
        )

        mode_type_name = await get_item(user_id, "type")
        if mode_type_name is None:
            await callback_query.answer("Please select a mode first \modes.", show_alert=True)
            return

        category_name = await get_item(user_id, "category")
        if category_name is None:
            await callback_query.answer("Please select a category first.", show_alert=True)
            return

        part_number = int(callback_query.data.split("_")[1])  # noqa
        can_send, limit_message = await can_send_voice(user_id)
        if not can_send:
            await callback_query.message.answer(limit_message)
            return

        if await get_item(user_id, "state") == SpeakingExamState.FULL_SPEAKING:
            await store_item(user_id, part_number, "state")
        else:
            await store_item(user_id, f"PART_{part_number}", "state")

        result = await get_random_question(part_number, category_name, mode_type_name)

        if not result or "question" not in result:
            await callback_query.answer("Invalid part selection. Please try again.")
            return

        question = result.get("question")

        await store_item(user_id, question, "question")
        await send_part(callback_query.message, part_number, question, mode_type_name)

        audio_base64 = result.get("audio_base64")
        if audio_base64:
            await audio_sender(callback_query, audio_base64)

        # try:
        #     category_name = await get_item(user_id, "category")
        #     gif_url = await fetch_tenor_gif(category_name)
        #     if gif_url:
        #         await callback_query.message.answer_animation(gif_url)
        # except Exception as gif_error:
        #     logging.error(f"Error in audio_sender: {gif_error}", exc_info=True)
    except Exception as e:
        logging.error(f"Error in handle_part_selection callback: {e}", exc_info=True)
        await callback_query.answer("An error occurred while processing your request.")


@dp.message(F.voice)
async def handle_user_answer(message: Message):
    """Handle the user's answer (voice only), send to Kafka, send to OpenAI"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    duration = message.voice.duration

    can_send, limit_message = await can_send_voice(user_id)
    if not can_send:
        await callback_query.message.answer(limit_message)
        return

    if await get_streaming_status(chat_id) == b'in_progress':
        await message.answer("<i>⏳ Please wait until your previous message is finished!</i>")
        return

    if duration > 120:
        await message.answer("🚫 Voice message too long! Maximum allowed is 2 minutes.")
        return

    current_state = await get_item(user_id, "state")
    category_name = await get_item(user_id, "category")
    mode_type_name = await get_item(user_id, "type")

    async def process_voice(state: SpeakingExamState, part_number: int):
        try:
            is_chance = await db.get_user_attribute(user_id, "full_speaking")
            if not is_chance:
                await db.update_voice_count(user_id)
            await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            transcribed_text = await transcribe_voice_message(message)
            await store_item(user_id, transcribed_text, f"transcribed_text_part_{part_number}")

            await store_questions_full_speaking(message, user_id, chat_id, category_name, part_number + 1, mode_type_name)
            await store_item(user_id, state, "state")
        except Exception as e:
            logging.error(f"Error in process_voice: {e}")
            await message.answer("An error occurred while processing your request.")
    
    async def process_voice_multilevel(state: MultilevelSpeakingFullState, part_number: int):
        try:
            is_chance = await db.get_user_attribute(user_id, "full_speaking")
            if not is_chance:
                await db.update_voice_count(user_id)
            await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

            transcribed_text = await transcribe_voice_message(message)
            await store_item(user_id, transcribed_text, f"transcribed_text_part_{part_number}")

            await store_questions_full_speaking_multilevel(message, user_id, chat_id, category_name, part_number, mode_type_name)
            await store_item(user_id, state, "state")
        except Exception as e:
            logging.error(f"Error in process_voice: {e}")
            await message.answer("An error occurred while processing your request.")

    if current_state == SpeakingExamState.FULL_SPEAKING:

        if not (9 <= duration <= 31):
            await message.answer("⏱️ Part 1 answer must be between 10 and 30 seconds.")
            return

        await process_voice(SpeakingExamState.PART_2, 1)
        return

    if current_state == SpeakingExamState.PART_2:

        if not (59 <= duration <= 121):
            await message.answer("⏱️ Part 2 answer must be between 60 and 120 seconds.")
            return

        await process_voice(SpeakingExamState.PART_3, 2)
        return
    
    if current_state == MultilevelSpeakingFullState.FULL_SPEAKING_MULTILEVEL:

        if not (9 <= duration <= 31):
            await message.answer("⏱️ Part 1.1 answer must be between 10 and 30 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_1_1_Q2, 2)
        return

    if current_state == MultilevelSpeakingFullState.PART_1_1_Q2:

        if not (9 <= duration <= 31):
            await message.answer("⏱️ Part 1.2 answer must be between 10 and 30 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_1_1_Q3, 3)
        return
    
    if current_state == MultilevelSpeakingFullState.PART_1_1_Q3:

        if not (9 <= duration <= 31):
            await message.answer("⏱️ Part 1.3 answer must be between 10 and 30 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_1_2_Q1, 4)
        return
    
    if current_state == MultilevelSpeakingFullState.PART_1_2_Q1:

        if not (14 <= duration <= 46):
            await message.answer("⏱️ Part 2.1 answer must be between 15 and 45 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_1_2_Q2, 5)
        return
    
    if current_state == MultilevelSpeakingFullState.PART_1_2_Q2:

        if not (9 <= duration <= 31):
            await message.answer("⏱️ Part 2.2 answer must be between 10 and 30 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_1_2_Q3, 6)
        return
    
    if current_state == MultilevelSpeakingFullState.PART_1_2_Q3:

        if not (9 <= duration <= 31):
            await message.answer("⏱️ Part 2.3 answer must be between 10 and 30 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_2, 7)
        return
    
    if current_state == MultilevelSpeakingFullState.PART_2:

        if not (59 <= duration <= 121):
            await message.answer("⏱️ Part 2 answer must be between 60 and 120 seconds.")
            return

        await process_voice_multilevel(MultilevelSpeakingFullState.PART_3, 8)
        return

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        max_batch_size=157286400,
        max_request_size=157286400
    )
    await producer.start()

    try:

        if current_state == SpeakingExamState.PART_3:

            if not (9 <= duration <= 31):
                await message.answer("⏱️ Part 3 answer must be between 10 and 30 seconds.")
                return

            message_waiting = await message.bot.send_message(chat_id, "Processing your voice message...")
            await set_message(chat_id, message_waiting.message_id)

            transcribed_text_part_3 = await transcribe_voice_message(message)

            part_1_question = await get_item(user_id, "full_speaking_question_1")
            part_2_question = await get_item(user_id, "full_speaking_question_2")
            part_3_question = await get_item(user_id, "full_speaking_question_3")

            transcribed_text_part_1 = await get_item(user_id, "transcribed_text_part_1")
            transcribed_text_part_2 = await get_item(user_id, "transcribed_text_part_2")

            prompt = build_openai_prompt_full_speaking(
                part_1_question, part_2_question, part_3_question,
                transcribed_text_part_1, transcribed_text_part_2, transcribed_text_part_3, mode_type_name
            )
        elif current_state == MultilevelSpeakingFullState.PART_3:

            if not (60 <= duration <= 121):
                await message.answer("⏱️ Part 3 answer must be between 60 and 120 seconds.")
                return

            message_waiting = await message.bot.send_message(chat_id, "Processing your voice message...")
            await set_message(chat_id, message_waiting.message_id)

            transcribed_text_part_8 = await transcribe_voice_message(message)

            part_1_question = await get_item(user_id, "full_speaking_question_1")
            part_2_question = await get_item(user_id, "full_speaking_question_2")
            part_3_question = await get_item(user_id, "full_speaking_question_3")
            part_4_question = await get_item(user_id, "full_speaking_question_4")
            part_5_question = await get_item(user_id, "full_speaking_question_5")
            part_6_question = await get_item(user_id, "full_speaking_question_6")
            part_7_question = await get_item(user_id, "full_speaking_question_7")
            part_8_question = await get_item(user_id, "full_speaking_question_8")

            transcribed_text_part_1 = await get_item(user_id, "transcribed_text_part_1")
            transcribed_text_part_2 = await get_item(user_id, "transcribed_text_part_2")
            transcribed_text_part_3 = await get_item(user_id, "transcribed_text_part_3")
            transcribed_text_part_4 = await get_item(user_id, "transcribed_text_part_4")
            transcribed_text_part_5 = await get_item(user_id, "transcribed_text_part_5")
            transcribed_text_part_6 = await get_item(user_id, "transcribed_text_part_6")
            transcribed_text_part_7 = await get_item(user_id, "transcribed_text_part_7")

            prompt = build_openai_prompt_full_speaking_multilevel(
                part_1_question,
                part_2_question,
                part_3_question,
                part_4_question,
                part_5_question,
                part_6_question,
                part_7_question,
                part_8_question,
                transcribed_text_part_1,
                transcribed_text_part_2,
                transcribed_text_part_3,
                transcribed_text_part_4,
                transcribed_text_part_5,
                transcribed_text_part_6,
                transcribed_text_part_7,
                transcribed_text_part_8,
                mode_type_name
            )
        else:
            question = await get_item(user_id, "question")
            part_num = await get_item(user_id, "state")

            if str(part_num) == "PART_1" and not (9 <= duration <= 31):
                await message.answer("⏱️ Part 1 answer must be between 10 and 30 seconds.")
                return
            elif str(part_num) == "PART_2" and not (59 <= duration <= 121):
                await message.answer("⏱️ Part 2 answer must be between 60 and 120 seconds.")
                return
            elif str(part_num) == "PART_3" and not (9 <= duration <= 31) and mode_type_name == "ielts":
                await message.answer("⏱️ Part 3 answer must be between 10 and 30 seconds.")
                return
            elif str(part_num) == "PART_3" and not (59 <= duration <= 121) and mode_type_name == "multilevel":
                await message.answer("⏱️ Part 3 answer must be between 60 and 120 seconds.")
                return

            message_waiting = await message.bot.send_message(chat_id, "Processing your voice message...")
            await set_message(chat_id, message_waiting.message_id)

            transcribed_text_part_3 = await transcribe_voice_message(message)

            prompt = build_openai_prompt(question, transcribed_text_part_3, part_num, mode_type_name)

        is_chance = await db.get_user_attribute(user_id, "full_speaking")
        is_paid = await db.get_user_attribute(user_id, "is_paid")
        daily_voice_count = await db.get_user_daily_count(user_id)
        if not is_chance:
            if not is_paid and daily_voice_count >= 2:
                await message.bot.send_message(
                    chat_id,
                    "You can only practice twice for free. Upgrade to premium for unlimited practice."
                )
                await producer.stop()
                return
        else:
            await db.set_user_attribute(user_id, "full_speaking", False)

        await db.update_voice_count(user_id)

        await set_streaming_status(chat_id, "in_progress")
        await producer.send(KAFKA_TOPIC, f"{chat_id}_{user_id}:{prompt}".encode('utf-8'))
        await producer.flush()

    finally:
        await producer.stop()


async def consume_kafka_message():
    """Consume Kafka messages to ensure user gets response before next question"""
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="telegram_messages_group_bot",
        fetch_max_bytes=157286400
    )
    await consumer.start()

    try:
        pass
    finally:
        await consumer.stop()
