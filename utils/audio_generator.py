import logging
import httpx
import io
import os

from utils.openai_api import open_ai
from data.config import API_URL_SPEECH
from aiogram.types import (
    Message, Voice
)


async def generate_speech_from_tts(text):
    """Send a request to OpenAI TTS API service asynchronously using httpx."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(API_URL_SPEECH, json={"text": text})

        if response.status_code != 200:
            logging.error(f"Failed to generate speech: {response.text}")
            return None

        audio_data = bytes.fromhex(response.json()["audio_data"])
        audio_buffer = io.BytesIO(audio_data)
        audio_buffer.seek(0)

        return audio_buffer

    except httpx.HTTPError as e:
        logging.error(f"Failed to generate speech: {e}")
        return None


async def transcribe_voice_message(message: Message):
    """Transcribe the voice message"""
    file_path = None
    try:
        voice: Voice = message.voice
        file_id = voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = f"./audio_{message.chat.id}_{message.message_id}_{message.from_user.id}.ogg"
        await message.bot.download_file(file.file_path, file_path)
        transcribed_text = await open_ai.transcribe_audio(file_path)

        return transcribed_text
    except Exception as e:
        logging.error(f"Failed to transcribe voice message: {e}")
        return None

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
