import io
import re
import ffmpeg
import base64
import asyncio
import logging
import redis.asyncio as redis

from data import config
from mutagen.oggopus import OggOpus
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from aiogram.types import BufferedInputFile
from aiogram.enums import ParseMode, ChatAction
# from utils.openai_api.open_ai import generate_streamed_response
from utils.gemini.gemini import generate_gemini_streamed_response, generate_audio_from_text

from loader import bot, db, REDIS_URL, KAFKA_URL
from utils.redis import get_message
# from utils.openai_api.open_ai import generate_tts_response
from keyboards.inline.speaking import modes_keyboard

TOKEN = config.telegram_token
KAFKA_BOOTSTRAP_SERVERS = KAFKA_URL
KAFKA_TOPIC = config.KAFKA_TOPIC

MAX_MESSAGE_LENGTH = 4096
MIN_UPDATE_INTERVAL = 0.3
MAX_UPDATE_INTERVAL = 1.0

redis_client = redis.from_url(REDIS_URL)

user_locks = {}

logging.info("Bot main started logging")
print("Bot main started print")


async def set_streaming_status(chat_id, status):
    """Set the streaming status in Redis"""
    await redis_client.set(f"streaming:{chat_id}", status)


async def expire_streaming_status(chat_id):
    """Expire the streaming status in Redis"""
    await redis_client.expire(f"streaming:{chat_id}", 60)


async def send_voice_message(user_id: int, chat_id: int, full_text: str):
    try:
        # is_paid = await db.get_user_attribute(user_id, "is_paid")

        if True:
            sent_message = await bot.send_message(chat_id, "Sending voice...")
            await bot.send_chat_action(chat_id=chat_id, action="upload_voice")

            voice_ogg_buffer = await generate_audio_from_text(full_text)

            await bot.send_voice(
                chat_id,
                voice=BufferedInputFile(voice_ogg_buffer.getvalue(), filename="voice.ogg")
            )

            await bot.delete_message(chat_id, sent_message.message_id)

    except Exception as e:
        logging.error(f"Error sending voice: {e}")


async def edit_streaming_response(user_id: int, chat_id: int, prompt: str):
    """Send a streaming response with buffered text updates."""
    if chat_id not in user_locks:
        user_locks[chat_id] = asyncio.Lock()

    if user_locks[chat_id].locked():
        await bot.send_message(
            chat_id,
            "<i>⏳ Please wait until your previous message is finished!</i>",
            parse_mode="HTML"
        )
        return

    async with user_locks[chat_id]:
        sent_message = await bot.send_message(chat_id, "Processing...")
        message_id = sent_message.message_id
        full_text = ""
        last_sent_text = ""
        stop_streaming = False

        def clean_text(text: str) -> str:
            """Remove * and ** from the text."""
            return re.sub(r"\*+", "", text)

        try:
            waiting_message_id = await get_message(chat_id)
            if waiting_message_id:
                await bot.delete_message(chat_id, waiting_message_id)
        except Exception as e:
            logging.warning(f"Failed to delete waiting message: {e}")

        await set_streaming_status(chat_id, "in_progress")

        async def send_or_edit_message():
            """Edit or send new messages when text exceeds limits."""
            nonlocal last_sent_text, message_id

            cleaned_text = clean_text(full_text)

            if cleaned_text == last_sent_text:
                return

            parts = split_message(cleaned_text)
            try:
                await bot.edit_message_text(
                    text=parts[0],  # noqa
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode=ParseMode.HTML
                )
                last_sent_text = parts[0]  # noqa

                for part in parts[1:]:
                    new_message = await bot.send_message(
                        chat_id,
                        part,
                        parse_mode=ParseMode.HTML
                    )
                    message_id = new_message.message_id
                    last_sent_text = part

            except Exception as e:
                if "message is not modified" not in str(e):
                    logging.error(f"Error updating message: {e}")

        async def update_message():
            """Update message content at regular intervals."""
            while not stop_streaming:
                await asyncio.sleep(get_update_interval(len(full_text)))
                await send_or_edit_message()

        update_task = asyncio.create_task(update_message())

        try:
            async for chunk in generate_gemini_streamed_response(prompt):
                if chunk:
                    full_text += chunk

            stop_streaming = True
            await update_task

            if full_text and full_text != last_sent_text:
                await send_or_edit_message()

        except Exception as e:
            logging.warning(f"Failed to edit message: {e}")
        finally:
            cleaned_text = clean_text(full_text)
            await send_voice_message(user_id, chat_id, cleaned_text)

            await bot.send_message(
                chat_id,
                "📌 <b>Choose one of the speaking modes:</b>",
                reply_markup=modes_keyboard
            )

    await set_streaming_status(chat_id, "done")
    await expire_streaming_status(chat_id)


def split_message(message: str) -> list[str]:
    """Split a message into chunks of max length."""
    return [
        message[i:i + MAX_MESSAGE_LENGTH]
        for i in range(0, len(message), MAX_MESSAGE_LENGTH)  # noqa
    ]


def get_update_interval(length: int) -> float:
    if length < 1000:
        return 0.3
    elif length < 3000:
        return 0.6
    return 1.0


async def wait_for_kafka_startup(consumer, retries=6):
    for i in range(retries):
        try:
            await consumer.start()
            logging.info("✅ Kafka consumer started successfully.")
            return
        except KafkaConnectionError:
            wait_time = 2 ** i
            logging.warning(f"⏳ Kafka not ready, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    raise RuntimeError("❌ Kafka did not start in time.")


async def consume_messages():
    logging.info(f"Kafka bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="telegram_messages_group_main",
        fetch_max_bytes=157286400,
        session_timeout_ms=12000,
        heartbeat_interval_ms=3000,
        auto_offset_reset="latest"
    )

    try:
        await wait_for_kafka_startup(consumer)
        
        async for msg in consumer:
            try:
                chat_and_user_id, text = msg.value.decode("utf-8").split(":", 1)
                chat_id, user_id = chat_and_user_id.split("_", 1)
                asyncio.create_task(edit_streaming_response(int(user_id), int(chat_id), text))
            except Exception as parse_err:
                logging.error(f"⚠️ Error parsing or processing message: {parse_err}")

    except Exception as e:
        logging.exception("🔥 Unexpected error in Kafka message loop")

    finally:
        await consumer.stop()
        logging.info("🛑 Kafka consumer stopped.")


async def main():
    try:
        await consume_messages()
    except Exception as e:
        logging.exception(f"❗ Fatal error in main: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.exception("Unhandled exception in asyncio loop")
