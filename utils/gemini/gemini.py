import io
import os
import logging
import asyncio
import ffmpeg
from google import genai
from pydub import AudioSegment
from google.cloud import texttospeech
from google.cloud import speech
from aiogram.types import Message, Voice
from data.config import GOOGLE_API_KEY
from google.generativeai.types.generation_types import GenerationConfigDict
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError

client = genai.Client(api_key=GOOGLE_API_KEY)

tts_client = texttospeech.TextToSpeechClient.from_service_account_file(
    "<google api key json file>"
)

speech_client = speech.SpeechClient.from_service_account_file(
    "<google api key json file>"
)

MODEL_ID = "gemini-2.0-flash-lite"

MAX_PROMPT_CHARS = 12000


async def convert_ogg_to_wav(input_path: str, output_path: str, sample_rate: int):
    def _convert():
        ffmpeg.input(input_path).output(output_path, ac=1, ar=sample_rate, format='wav').run(overwrite_output=True)
    await asyncio.to_thread(_convert)

async def load_audio_segment(path: str):
    return await asyncio.to_thread(AudioSegment.from_wav, path)

async def export_chunk_to_wav_bytes(chunk: AudioSegment) -> bytes:
    chunk = chunk.set_frame_rate(48000).set_channels(1).set_sample_width(2)
    buffer = io.BytesIO()
    await asyncio.to_thread(chunk.export, buffer, format="wav")
    return buffer.getvalue()

async def recognize_speech(audio_bytes: bytes, sample_rate_hertz: int, language_code: str) -> str:
    audio_google = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate_hertz,
        language_code=language_code,
        audio_channel_count=1,
        enable_separate_recognition_per_channel=False
    )

    def _recognize():
        return speech_client.recognize(config=config, audio=audio_google)

    try:
        response = await asyncio.to_thread(_recognize)
        return " ".join(result.alternatives[0].transcript for result in response.results)
    except GoogleAPIError as api_err:
        logging.error(f"Google API error: {api_err}", exc_info=True)
    except Exception as err:
        logging.error(f"Unexpected error: {err}", exc_info=True)
    return ""

async def transcribe_audio_with_google(file_path: str, sample_rate_hertz: int = 48000, language_code: str = "en-US") -> str:
    wav_path = file_path.replace(".ogg", ".wav")
    chunk_length_ms = 59000  # ~59 seconds
    try:
        await convert_ogg_to_wav(file_path, wav_path, sample_rate_hertz)
        audio = await load_audio_segment(wav_path)
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

        full_transcript = ""

        for i, chunk in enumerate(chunks):
            audio_bytes = await export_chunk_to_wav_bytes(chunk)
            chunk_text = await recognize_speech(audio_bytes, sample_rate_hertz, language_code)
            full_transcript += chunk_text + " "

        return full_transcript.strip()

    except Exception as e:
        logging.error(f"Google STT error: {e}", exc_info=True)
        return ""

    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

async def transcribe_voice_message(message):
    """Transcribe Telegram voice message using Google STT"""
    file_path = None
    try:
        voice = message.voice
        file_id = voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = f"./audio_{message.chat.id}_{message.message_id}_{message.from_user.id}.ogg"
        await message.bot.download_file(file.file_path, file_path)

        transcribed_text = await transcribe_audio_with_google(file_path)
        return transcribed_text or "Sorry, I couldn't understand that."

    except Exception as e:
        logging.error(f"Failed to transcribe voice message with Google STT: {e}", exc_info=True)
        return None

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


# async def transcribe_audio_with_google(file_path: str, sample_rate_hertz: int = 48000, language_code: str = "en-US") -> str:
#     """Transcribe long audio using Google Cloud Speech-to-Text by splitting it into ≤60s chunks."""
#     wav_path = file_path.replace(".ogg", ".wav")
#     chunk_length_ms = 59000  # 60 seconds

#     try:
#         # Convert .ogg to .wav using ffmpeg
#         ffmpeg.input(file_path).output(wav_path, ac=1, ar=sample_rate_hertz, format='wav').run(overwrite_output=True)

#         # Load the wav file
#         audio = AudioSegment.from_wav(wav_path)

#         # Split into chunks
#         chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

#         full_transcript = ""

#         for i, chunk in enumerate(chunks):
#             chunk = chunk.set_frame_rate(sample_rate_hertz).set_channels(1).set_sample_width(2)

#             with io.BytesIO() as buffer:
#                 chunk.export(buffer, format="wav")
#                 audio_bytes = buffer.getvalue()

#             audio_google = speech.RecognitionAudio(content=audio_bytes)
#             config = speech.RecognitionConfig(
#                 encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
#                 sample_rate_hertz=sample_rate_hertz,
#                 language_code=language_code,
#                 audio_channel_count=1,
#                 enable_separate_recognition_per_channel=False
#             )

#             try:
#                 response = speech_client.recognize(config=config, audio=audio_google)
#                 chunk_text = " ".join(result.alternatives[0].transcript for result in response.results)
#                 full_transcript += chunk_text + " "
#             except GoogleAPIError as api_err:
#                 logging.error(f"Google API error on chunk {i + 1}: {api_err}", exc_info=True)
#             except Exception as err:
#                 logging.error(f"Unexpected error on chunk {i + 1}: {err}", exc_info=True)

#         return full_transcript.strip()

#     except Exception as e:
#         logging.error(f"Google STT error: {e}", exc_info=True)
#         return ""

#     finally:
#         if os.path.exists(wav_path):
#             os.remove(wav_path)


# async def transcribe_voice_message(message):
#     """Transcribe Telegram voice message using Google STT"""
#     file_path = None
#     try:
#         voice = message.voice
#         file_id = voice.file_id
#         file = await message.bot.get_file(file_id)
#         file_path = f"./audio_{message.chat.id}_{message.message_id}_{message.from_user.id}.ogg"
#         await message.bot.download_file(file.file_path, file_path)

#         transcribed_text = await transcribe_audio_with_google(file_path)
#         return transcribed_text or "Sorry, I couldn't understand that."

#     except Exception as e:
#         logging.error(f"Failed to transcribe voice message with Google STT: {e}", exc_info=True)
#         return None

#     finally:
#         if file_path and os.path.exists(file_path):
#             os.remove(file_path)


def chunk_prompt(text: str, max_chunk_len: int = MAX_PROMPT_CHARS):
    """Split a long prompt into logical chunks."""
    chunks = []
    while len(text) > max_chunk_len:
        split_point = text.rfind("\n", 0, max_chunk_len)
        if split_point == -1:
            split_point = max_chunk_len
        chunks.append(text[:split_point].strip())
        text = text[split_point:].strip()
    chunks.append(text)
    return chunks


async def generate_gemini_streamed_response(prompt: str):
    """Fetch streamed response from Gemini AI model with safe prompt handling."""
    try:
        if len(prompt) > MAX_PROMPT_CHARS:
            logging.warning(f"Prompt too long ({len(prompt)} chars). Trimming or chunking...")
            chunks = chunk_prompt(prompt)
            prompt = "\n\n---\n\n".join(chunks[:2])
            logging.info(f"Trimmed prompt to {len(prompt)} chars")

        stream = await client.aio.models.generate_content_stream(
            model=MODEL_ID,
            contents=prompt
        )

        async for chunk in stream:
            if chunk.text:
                yield chunk.text

    except ResourceExhausted:
        logging.warning("Rate limit reached. Retrying...")
        async for content in generate_gemini_streamed_response(prompt):
            yield content

    except GoogleAPIError as e:
        logging.error(f"Google API Error: {str(e)}")
        raise ValueError(f"Google API Error: {str(e)}")

    except Exception as e:
        logging.error(f"Unexpected error during Gemini generation: {str(e)}", exc_info=True)
        raise ValueError(f"Unexpected Error: {str(e)}")


def _generate_audio_sync(prompt: str) -> io.BytesIO:
    synthesis_input = texttospeech.SynthesisInput(text=prompt)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Chirp3-HD-Aoede"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
        effects_profile_id=["small-bluetooth-speaker-class-device"],
        pitch=0,
        speaking_rate=1
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    if not response.audio_content:
        raise ValueError("TTS response contains no audio data.")

    buffer = io.BytesIO(response.audio_content)
    buffer.name = "voice.ogg"
    buffer.seek(0)
    return buffer

async def generate_audio_from_text(prompt: str) -> io.BytesIO:
    loop = asyncio.get_running_loop()
    try:
        buffer = await loop.run_in_executor(None, _generate_audio_sync, prompt)
        return buffer
    except Exception as e:
        logging.error(f"Error generating audio: {str(e)}")
        raise ValueError(f"Unexpected Error: {str(e)}")
