import logging

from aiogram import F
from datetime import datetime, timezone, timedelta
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from loader import dp, db
from utils.commons import send_start_voice
from keyboards.inline.speaking import invite_func


@dp.message(CommandStart())
async def command_start_handler(message: Message, command: CommandStart) -> None:
    """Handles the /start command"""
    try:
        user_id = message.from_user.id
        full_name = message.from_user.full_name
        referred_by = command.args
        referred_by = int(referred_by) if referred_by and referred_by.isdigit() else None

        user_data = await db.user_collection.find_one({"_id": user_id})

        if not user_data:
            if referred_by and referred_by != user_id:
                await db.user_collection.update_one(
                    {"_id": referred_by},
                    {"$inc": {"invited_users": 1}}
                )
                await db.user_collection.update_one(
                    {"_id": user_id},
                    {"$set": {"referred_by": referred_by}}
                )

        welcome_message = (
            f"👋 <b>Welcome, {message.from_user.full_name}!</b>\n\n"
            "I'm here to help you <b>enhance your IELTS skills</b> through guided practice and "
            "full mock exams. Whether you're preparing for the test or just looking to improve, "
            "I've got you covered!\n\n"
            "✨ <b>Available Commands:</b>\n\n"
            "📌 /modes - Switch between practice modes\n"
            "📌 /premium - Upgrade to Premium for more benefits\n"
            "📌 /help - Get help using the bot\n\n"
            "🔹 <b>Usage Limits:</b>\n"
            "   - 🆓 Free Users: <b>3 voice messages per day</b>\n"
            "   - 🌟 Premium Users: <b>25 voice messages per day</b>\n\n"
            "🚀 Let's start practicing and boost your IELTS score! 😊"
        )

        await message.answer(welcome_message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        await send_start_voice(message)
    except Exception as e:
        logging.error(f"Error in /start command: {e}")
        await message.answer("An error occurred while processing your request.")


@dp.message(Command(commands=["status"]))
async def get_daily_count_command(message: Message):
    """Get the daily voice usage status"""
    try:
        user_id = message.from_user.id
        user_data = await db.user_collection.find_one({"_id": user_id})

        if not user_data:
            await message.answer("⚠️ You are not registered in the system.")
            return

        daily_count = user_data.get("daily_voice_count", 0)
        last_voice_date = user_data.get("last_voice_date")
        is_paid = user_data.get("is_paid", False)
        payment_date = user_data.get("payment_date")
        payment_valid_date = user_data.get("payment_valid_date")

        if last_voice_date and last_voice_date.date() < datetime.now(timezone.utc).date():
            daily_count = 0

        now = datetime.now(timezone.utc)
        if payment_valid_date:
            if isinstance(payment_valid_date, str):  # noqa
                payment_valid_date = datetime.fromisoformat(payment_valid_date)
            if payment_valid_date.tzinfo is None:
                payment_valid_date = payment_valid_date.replace(tzinfo=timezone.utc)

            if now > payment_valid_date:
                is_paid = False
                await db.user_collection.update_one(
                    {"_id": user_id},
                    {"$set": {"is_paid": False}}
                )

        free_limit = 3
        premium_limit = 25
        max_limit = premium_limit if is_paid else free_limit

        remaining = max(max_limit - daily_count, 0)

        if is_paid:
            payment_status = (
                f"💎 *Premium User*\n"
                f"🗓️ *Payment Date:* {payment_date.strftime('%Y-%m-%d') if payment_date else 'Unknown'}\n"
                f"🔹 *Valid Until:* {payment_valid_date.strftime('%Y-%m-%d') if payment_valid_date else 'Unknown'}"
            )
        else:
            payment_status = "🆓 *Free User*\n🔹 Upgrade to premium for more\n benefits: /premium"

        response = (
            f"📊 *Voice Usage Status*\n\n"
            f"🎙️ *Used today:* {daily_count}/{max_limit}\n"
            f"🔹 *Remaining:* {remaining}\n\n"
            f"{payment_status}"
        )

        await message.answer(response, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error in /status command: {e}")
        await message.answer("⚠️ An error occurred while processing your request.")


@dp.callback_query(F.data == "coming_soon")
async def coming_soon_callback(callback_query: CallbackQuery):
    await callback_query.answer("🚧 This feature is coming soon! Stay tuned.", show_alert=True)


@dp.message(Command(commands=["invite"]))
async def invite_command_handler(message: Message):
    """Send an invite link for users to share"""
    try:
        user_id = message.from_user.id
        bot_username = "speakez_robot"
        invite_link = f"https://t.me/{bot_username}?start={user_id}"

        user_data = await db.user_collection.find_one({"_id": user_id})
        invited_count = user_data.get("invited_users", 0)

        invite_text = (
            "🎉 *Invite Your Friends & Get Premium!*\n\n"
            "Earn *1 week of Premium* for every *20 users* you invite.\n"
            "Share your personal invite link and start earning rewards! 💎\n\n"
            f"👥 *Users Invited So Far:* {invited_count}\n\n"
            "Keep sharing and enjoy exclusive benefits! 🚀\n\n"
            f"Click to copy the offer link: `{invite_link}`"
        )

        if invited_count >= 20:

            now = datetime.utcnow()
            premium_until = now + timedelta(weeks=1)

            await db.user_collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "is_paid": True, 
                        "payment_type": "premium", 
                        "payment_date": now, 
                        "payment_valid_date": premium_until
                    },
                    "$inc": {"invited_users": -20}
                }
            )

            await message.answer(
                "🎉 Congratulations! You've earned 1 week of Premium for inviting 20 users! 🚀"
                "\n\nEnjoy all the premium features! 🎁"
            )

        keyboard = invite_func(invite_link)
        await message.answer(invite_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e:
        logging.error(f"Error in /invite command: {e}")
        await message.answer("⚠️ An error occurred while generating your invite link.")


@dp.message(Command(commands=["developer"]))
async def show_developer_info(message: Message):
    text = (
        "👨‍💻 <b>Bot Developer Information:</b>\n\n"
        "📛 Name: <b>Abdulaziz Kamilov</b>\n"
        "📬 Telegram: <b>@abdulaziz9963</b>\n\n"
        "<i>Agar sizga bot kerak bo‘lsa yoki hamkorlik qilmoqchi bo‘lsangiz, bemalol murojaat qiling!</i> 😊"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)
