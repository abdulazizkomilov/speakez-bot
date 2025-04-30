import logging
import aiofiles
import asyncio
import json
import base64
import io

from aiogram import F
from aiogram.types import BufferedInputFile
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup
)

from loader import dp
from utils.commons import PREMIUM_PLANS, init_payment


@dp.message(Command("premium"))
async def get_premium(message: Message):
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Haftalik (8,000 so‘m)", callback_data="weekly")],
            [InlineKeyboardButton(text="📆 Oylik (25,000 so‘m)", callback_data="monthly")],
            # [InlineKeyboardButton(text="⭐️ Premium demo", callback_data="premium_demo")]
        ])

        premium_text = (
            "✨ *Premium obuna tariflari:*\n\n"
            "📅 *Haftalik — 8,000 so‘m*\n"
            "   🗣️ Kuniga 25 ta speaking audio xabar\n"
            "   ✅ OpenAI javobining audiovarianti ham mavjud\n\n"
            "📆 *Oylik — 25,000 so‘m*\n"
            "   🗣️ Kuniga 25 ta speaking audio xabar\n"
            "   ✅ OpenAI javobining audiovarianti ham mavjud"
        )

        await message.answer(
            premium_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logging.error(f"Error in premium command: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko‘ring.")


@dp.callback_query(F.data.in_(["weekly", "monthly"]))
async def process_payment(call: CallbackQuery):
    try:
        plan_type = call.data
        amount = PREMIUM_PLANS.get(plan_type, 0)

        if amount == 0 or amount < 0:
            await call.answer("❌ Xato: To'lov miqdori noto‘g‘ri.", show_alert=True)
            return

        user_id = call.from_user.id

        await call.answer("🔄 To‘lov uchun havola yaratilyapti...")

        payment_data = await init_payment(user_id, amount)

        if "payment_url" in payment_data:
            payment_url = payment_data["payment_url"]
            order_id = payment_data["order_id"]

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Payme orqali to‘lash", url=payment_url)]
            ])

            await call.message.answer(
                f"✅ *To‘lov yaratildi!*\n"
                f"🆔 *Buyurtma ID:* `{order_id}`\n"
                f"💰 *Miqdor:* `{amount}` so‘m\n"
                f"🔗 *To‘lov qilish uchun:* [Payme orqali to‘lash]({payment_url})",
                parse_mode="Markdown",
                disable_web_page_preview=True,
                reply_markup=keyboard
            )
        else:
            await call.message.answer("❌ To‘lovni boshlashda xatolik yuz berdi. Keyinroq urinib ko‘ring.")
    except Exception as e:
        logging.error(f"Error in process_payment: {e}")
        await call.message.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko‘ring.")


@dp.callback_query(F.data == "premium_demo")
async def premium_demo_call(call: CallbackQuery):
    try:
        user_id = call.from_user.id
        file_path = "./response.json"

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            question_data = json.loads(await f.read())
            open_ai_response = question_data.get("full_text", "Unknown response")
            audio_base64 = question_data.get("audio_base64", None)

        # Simulated IELTS Part 2 question
        await call.answer("Sending...")

        await call.message.answer(
            "🎤 **Part 2 Question:**\n\nHow can schools better prepare students for the real world?")
        await asyncio.sleep(1)

        user_text = (
            "🗣 **Candidate's Part 2 Response:**\n\n"
            "Well, I think schools can do a better job by teaching more useful things for daily life. "
            "For example, students should learn how to save money, make a budget, or even cook simple food. "
            "These are skills we need after we leave school, but many students don’t know how to do them.\n\n"
            "Also, I think working in teams is important. In most jobs, people have to work with others. "
            "So, schools should give students more group projects, so they learn how to share ideas and solve problems together.\n\n"
            "Another thing is about jobs. Many students don’t know what job they want to do. Schools can help by giving more "
            "information about different jobs, or maybe let students visit workplaces to see what it's like.\n\n"
            "And finally, I think students should learn how to deal with stress. Life can be hard sometimes, and learning how to "
            "stay calm or ask for help is also very important.\n\n"
            "So yeah, I think schools need to teach more life skills, not just academic subjects."
        )
        await call.message.answer(user_text)
        await asyncio.sleep(1)

        # OpenAI's detailed evaluation
        await call.message.answer(open_ai_response)

        try:
            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                audio_buffer = io.BytesIO(audio_bytes)
                await call.bot.send_voice(
                    call.message.chat.id,
                    BufferedInputFile(audio_buffer.read(), filename="demo.ogg")
                )

        except Exception as e:
            logging.error(f"Error in send_start_voice: {e}")

    except Exception as e:
        logging.error("Error in premium_demo callback: ", exc_info=True)
        await call.message.answer("An error occurred while processing your request.")
