import redis.asyncio as redis
import logging

from loader import REDIS_URL

redis_client = redis.from_url(REDIS_URL)


async def set_streaming_status(chat_id, status):
    try:
        await redis_client.set(f"streaming:{chat_id}", status, ex=200)
    except Exception as e:
        logging.error(f"Failed to set streaming status: {e}")


async def get_streaming_status(chat_id):
    try:
        return await redis_client.get(f"streaming:{chat_id}")
    except Exception as e:
        logging.error(f"Failed to get streaming status: {e}")


async def set_message(chat_id, message_id):
    try:
        await redis_client.set(f"message:{chat_id}", f"{message_id}", ex=500)
    except Exception as e:
        logging.error(f"Failed to set status: {e}")


async def get_message(chat_id):
    try:
        return await redis_client.get(f"message:{chat_id}")
    except Exception as e:
        logging.error(f"Failed to get status: {e}")


async def store_item(user_id, item, value):
    try:
        await redis_client.set(f"user:{user_id}:{value}", item, ex=500)
    except Exception as e:
        logging.error(f"Failed to store {value}: {e}")


async def get_item(user_id, value):
    try:
        question = await redis_client.get(f"user:{user_id}:{value}")
        return question.decode() if question else None
    except Exception as e:
        logging.error(f"Failed to retrieve {value}: {e}")
        return None


async def delete_item(user_id, value):
    try:
        await redis_client.delete(f"user:{user_id}:{value}")
    except Exception as e:
        logging.error(f"Failed to delete user {value}: {e}")
