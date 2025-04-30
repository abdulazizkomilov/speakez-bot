from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from utils.db_api.database import Database
from data.config import (
    telegram_token, KAFKA_SERVER, KAFKA_PORT,
    REDIS_SERVER, REDIS_PORT
)

db = Database()
bot = Bot(token=telegram_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
KAFKA_URL = f"{KAFKA_SERVER}:{KAFKA_PORT}"
REDIS_URL = f"redis://{REDIS_SERVER}:{REDIS_PORT}"
