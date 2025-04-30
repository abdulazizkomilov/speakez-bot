import sys
import asyncio
import logging
import middlewares, filters, handlers  # noqa # isort:skip
import sentry_sdk

from sentry_sdk.integrations.logging import LoggingIntegration

from loader import dp, bot
from data.config import SENTRY_URL
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands

sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.ERROR
)

sentry_sdk.init(
    dsn=SENTRY_URL,
    traces_sample_rate=1.0,
    environment="production",
)


async def on_startup(dispatcher):
    await on_startup_notify(dispatcher)


async def main() -> None:
    await set_default_commands(bot)
    await dp.start_polling(bot, on_startup=on_startup)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
