import io
import json
import random
import requests
import httpx
import base64
import ffmpeg
import logging

from datetime import datetime, timezone
from aiogram.enums import ParseMode, ChatAction
from aiogram.types import Message, BufferedInputFile

from loader import db
from data.config import PAYMENT_URL, TENOR_API_KEY
from keyboards.default.speaking import mode_type

PREMIUM_PLANS = {
    "monthly": 25000,
    "weekly": 8000
}

CLIENT_KEY = "speakz_client"
GIF_LIMIT = 50


async def fetch_tenor_gif(search_query: str):
    try:
        """Fetch a random GIF from Tenor based on a search query."""
        url = f"https://tenor.googleapis.com/v2/search?key={TENOR_API_KEY}&client_key={CLIENT_KEY}&q={search_query}&limit={GIF_LIMIT}"
        response = requests.get(url)

        if response.status_code == 200:
            gif_results = json.loads(response.content).get("results", [])
            gif_count = len(gif_results)

            if gif_count > 0:
                random_index = random.randint(1, gif_count) - 1
                return gif_results[random_index]["media_formats"]["gif"]["url"]
        return None
    except Exception as e:
        logging.error(f"Error in fetch_tenor_gif: {e}")


async def send_start_voice(message):
    try:
        with open("questions/start.json", "r") as file:
            audio_data = json.load(file)
        audio_base64 = audio_data.get("audio_base64")
        if audio_base64:
            audio_bytes = base64.b64decode(audio_base64)
            audio_buffer = io.BytesIO(audio_bytes)  # noqa
            await message.bot.send_voice(
                message.chat.id,
                BufferedInputFile(audio_buffer.read(), filename="welcome.ogg")
            )
            await message.bot.send_message(
                message.chat.id,
                "📌 <b>Choose one of these categories:</b>",
                reply_markup=mode_type
            )
    except Exception as e:
        logging.error(f"Error in send_start_voice: {e}")


async def send_ogg_voice(message, audio_base64):
    if not audio_base64:
        logging.error("audio_base64 is empty!")
        return

    try:
        audio_bytes = base64.b64decode(audio_base64)
        audio_buffer = io.BytesIO(audio_bytes)  # noqa
        audio_buffer.seek(0)

        header = audio_buffer.read(4)
        audio_buffer.seek(0)

        if header.startswith(b"RIFF"):  # noqa
            input_audio = io.BytesIO(audio_bytes)  # noqa
            output_audio = io.BytesIO()

            out, _ = (
                ffmpeg
                .input("pipe:0")
                .output("pipe:1", format="ogg", acodec="libopus", audio_bitrate="64k")
                .run(input=input_audio.read(), capture_stdout=True, capture_stderr=True)
            )

            output_audio.write(out)
            output_audio.seek(0)

            audio_bytes = output_audio.read()

        audio_input = BufferedInputFile(audio_bytes, filename="voice.ogg")

        await message.bot.send_voice(
            chat_id=message.chat.id,
            voice=audio_input
        )

    except Exception as audio_error:
        logging.error(f"Failed to send voice: {audio_error}", exc_info=True)


async def can_send_voice(user_id: int) -> tuple[bool, str | None]:
    """Check if the user can send a voice message and return a message if the limit is reached."""
    try:
        is_paid = await db.get_user_attribute(user_id, "is_paid")
        payment_valid_date = await db.get_user_attribute(user_id, "payment_valid_date")

        if is_paid is None:
            return False, "🚫 You are not registered in the system."

        now = datetime.now(timezone.utc)

        if is_paid and payment_valid_date:
            if isinstance(payment_valid_date, str):  # noqa
                payment_valid_date = datetime.fromisoformat(payment_valid_date)

            if payment_valid_date.tzinfo is None:
                payment_valid_date = payment_valid_date.replace(tzinfo=timezone.utc)

            if now > payment_valid_date:
                is_paid = False
                await db.user_collection.update_one(
                    {"_id": user_id},
                    {"$set": {"is_paid": False}}
                )

        max_voice_limit = 25 if is_paid else 3
        daily_voice_count = await db.get_user_daily_count(user_id)

        if daily_voice_count >= max_voice_limit:
            return False, f"📣 You have reached the daily limit of {max_voice_limit} voice messages."

        return True, None

    except Exception as e:
        logging.error(f"Error in can_send_voice: {e}")
        return False, "⚠️ An error occurred while checking your voice message limit."


async def send_part(message: Message, part_number: int, question: str, mode_type_name: str):
    """Send the part question to the user"""
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        await message.edit_text(
            f"{mode_type_name.upper()} Speaking Part {part_number} ```Question:\n{question}```",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logging.error(f"Error in send_part: {e}, part_number: {part_number}, question: {question}")
        await message.answer("Failed to send the part question.")


async def init_payment(user_id: int, amount: int) -> dict:
    url = PAYMENT_URL
    payload = {
        "user_id": user_id,
        "amount": amount,
        "payment_method": "payme"
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{url}/api/payme/init/", json=payload)
            data = response.json()

            if response.status_code == 200 and "payment_url" in data:
                return data
            else:
                logging.error(f"Payme API error: {data}")
                return {"error": "Payment initialization failed"}
    except httpx.HTTPStatusError as e:
        logging.error(f"Error in init_payment: HTTP error: {e.response.status_code} - {e.response.text}")
        return {"error": "Server returned an error"}
    except httpx.RequestError as e:
        logging.error(f"Error in init_payment: Request error: {e}")
        return {"error": "Failed to connect to server"}
