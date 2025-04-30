import json
import asyncio
import base64
import os
import io
import logging
from google.cloud import texttospeech

import io
import logging
import asyncio
from google import genai
from google.cloud import texttospeech
from data.config import GOOGLE_API_KEY
from google.generativeai.types.generation_types import GenerationConfigDict
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError


tts_client = texttospeech.TextToSpeechClient.from_service_account_file(
    "<google api key json file>"
)

categories = {}



semaphore = asyncio.Semaphore(5)

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

async def generate_audio_from_text(prompt: str, retries=3, backoff=5) -> str:
    """Asynchronous wrapper for _generate_audio_sync with retry on 429."""
    loop = asyncio.get_running_loop()
    async with semaphore:
        for attempt in range(retries):
            try:
                buffer = await loop.run_in_executor(None, _generate_audio_sync, prompt)
                audio_bytes = buffer.read()
                return base64.b64encode(audio_bytes).decode("utf-8")

            except ResourceExhausted as e:
                logging.error(f"❌ Quota hit: {e}. Retrying in {backoff} seconds...")
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff

            except Exception as e:
                logging.error(f"❌ Error generating audio: {str(e)}")
                return None

        logging.error(f"❌ Failed to generate audio after {retries} retries.")
        return None

async def process_in_chunks(tasks, chunk_size=10, delay=0.5):
    results = []
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk)
        results.extend(chunk_results)
        print(f"✅ Completed chunk {i // chunk_size + 1}")
        await asyncio.sleep(delay)
    return results

async def generate_questions_for_category(category, questions):
    category_path = f"questions/multilevel/part_2/{category}"
    os.makedirs(category_path, exist_ok=True)

    tasks = [generate_audio_from_text(question) for question in questions]
    audio_results = await process_in_chunks(tasks, chunk_size=5, delay=15)

    for idx, (question, audio_base64) in enumerate(zip(questions, audio_results), start=1):
        file_path = os.path.join(category_path, f"q_{idx}.json")

        data = {
            "question": question,
            "audio_base64": audio_base64 or "ERROR_FETCHING_AUDIO"
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"✅ Saved: {file_path}")

async def generate_all_questions():
    tasks = [generate_questions_for_category(category, questions) for category, questions in categories.items()]
    await process_in_chunks(tasks, chunk_size=5, delay=15)
    print("✅ Barcha savollar yaratildi!")

if __name__ == "__main__":
    asyncio.run(generate_all_questions())

