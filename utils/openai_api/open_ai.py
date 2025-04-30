import logging
import itertools

from data import config
from openai import AsyncOpenAI, RateLimitError

api_keys = itertools.cycle(config.openai_api_keys)

client = AsyncOpenAI(api_key=next(api_keys))

if config.openai_api_base:
    client.base_url = config.openai_api_base


async def generate_streamed_response(prompt: str):
    try:
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content  # noqa
                if content:
                    yield content
    except RateLimitError:
        logging.warning("Rate limit reached. Switching API key...")
        client.api_key = next(api_keys)
        async for content in generate_streamed_response(prompt):
            yield content
    except Exception as e:
        raise ValueError(f"Error generating response: {str(e)}")


async def transcribe_audio(audio_file) -> str:
    try:
        with open(audio_file, "rb") as file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=file
            )
            return response.text or ""
    except RateLimitError:
        logging.warning("Rate limit reached. Switching API key...")
        client.api_key = next(api_keys)
        return await transcribe_audio(audio_file)
    except Exception as e:
        raise ValueError(f"Error transcribing audio: {str(e)}")


async def generate_tts_response(text: str) -> bytes:
    try:
        response = await client.audio.speech.create(
            model="gpt-4o-mini-tts",
            input=text,
            voice="alloy",
            response_format="opus"
        )

        return response.content
    except RateLimitError:
        logging.warning("Rate limit reached. Switching API key...")
        client.api_key = next(api_keys)
        return await generate_tts_response(text)
    except Exception as e:
        raise ValueError(f"Error generating TTS response: {str(e)}")
