from aiogram.types import BotCommand


async def set_default_commands(bot):
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/modes", description="Select your mode"),
        BotCommand(command="/premium", description="Upgrade to premium"),
        BotCommand(command="/status", description="Get Status"),
        BotCommand(command="/invite", description="Invite friends"),
        BotCommand(command="/promocode", description="Using promocode"),
        BotCommand(command="/help", description="Get help"),
        BotCommand(command="/send_msg_to_admin", description="Send Message to admin"),
        BotCommand(command="/developer", description="Developer")
    ]
    await bot.set_my_commands(commands)
