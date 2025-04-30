import logging

from data.config import admins


async def on_startup_notify(dp):
    for admin in admins:
        try:
            await dp.bot.send_message(admin, "Bot is ready!")

        except Exception as err:
            logging.exception(err)
