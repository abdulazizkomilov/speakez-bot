import logging

from datetime import datetime, timezone, timedelta
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from loader import dp, db, bot
from data.config import admins
from aiogram.enums import ParseMode
from states.admin import SendMessageState
from utils.celery import send_message_to_admin
from keyboards.inline.admin import admin_keyboard
from states.broadcast import (
    BroadcastState, BroadcastUserState
)


async def get_user_statistics():
    try:
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_users = await db.user_collection.count_documents({})
        
        users_joined_today = await db.user_collection.count_documents(
            {"first_seen": {"$gte": today}}
        )
        
        active_users_last_24hrs = await db.user_collection.count_documents(
            {"last_interaction": {"$gte": now - timedelta(days=1)}}
        )
        
        active_users_last_3days = await db.user_collection.count_documents(
            {"last_interaction": {"$gte": now - timedelta(days=3)}}
        )
        
        premium_users = await db.user_collection.count_documents({"is_paid": True})

        return total_users, users_joined_today, active_users_last_24hrs, active_users_last_3days, premium_users
    except Exception as e:
        logging.error(f"Error in get_user_statistics: {e}")
        return 0, 0, 0, 0, 0


@dp.message(Command(commands=["owner_panel"]))
async def show_admin_panel(message: Message):
    """
    Display admin panel with inline buttons if the user is an admin.
    """
    if message.from_user.id not in admins:
        return await message.answer("❌ You are not authorized to access the admin panel.")

    try:
        text = (
            "👤 <b>Admin Panel:</b>\n\n"
            "/broadcast_msg_users - Send message to users\n\n"
            "/broadcast_msg_user - Send message to a specific user\n\n"
        )
        await message.answer(
            text,
            reply_markup=admin_keyboard,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logging.exception("Error in /owner_panel command")
        await message.answer("❌ An error occurred while processing your request.")


@dp.callback_query(F.data == "get_all_users_statistics")
async def handle_get_user_statistics(callback: CallbackQuery):
    """
    Handle the 'Get User Statistics' button click.
    """
    try:
        if callback.from_user.id not in admins:
            await callback.answer("❌ You are not authorized to access this information.")
            return

        total_users, users_joined_today, active_users_last_24hrs, active_users_last_3days, premium_users = await get_user_statistics()

        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=(
                f"👥 Total Users: {total_users}\n\n"
                f"📅 Users Joined Today: {users_joined_today}\n\n"
                f"🌟 Active Users (Last 24 hours): {active_users_last_24hrs}\n\n"
                f"🔄 Active Users (Last 3 days): {active_users_last_3days}\n\n"
                f"💎 Premium Users: {premium_users}\n"
            ),
        )
    except Exception as e:
        logging.error(f"Error in get_user_statistics callback: {e}")
        await callback.answer("An error occurred while processing your request.")


@dp.message(Command("send_msg_to_admin"))
async def ask_for_message(message: Message, state: FSMContext):
    """
    Step 1: Ask the user to enter a message to send to the admin.
    """
    try:
        await message.answer("📝 *Write your message to the admin:*", parse_mode="Markdown")
        await state.set_state(SendMessageState.waiting_for_message)
    except Exception as e:
        logging.error(f"Error in /send_msg_to_admin command: {e}")
        await message.answer("An error occurred while processing your request.")


@dp.message(SendMessageState.waiting_for_message)
async def process_admin_message(message: Message, state: FSMContext):
    """
    Step 2: Process the user's message and send it to the admin via Celery.
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "N/A"
        user_message = message.text

        if not user_message:
            await message.answer("⚠️ Please send a valid text message.")
            return

        send_message_to_admin.delay(user_id, username, user_message)

        await message.answer("✅ Your message has been sent to the admin.")
        await state.clear()
    except Exception as e:
        logging.error(f"Error in process_admin_message: {e}")
        await message.answer("⚠️ Failed to process the message.")
        await state.clear()


@dp.callback_query(F.data == "get_users_count")
async def handle_get_users_count(callback: CallbackQuery):
    """
    Handle the 'Number of Users' button click.
    """
    try:
        if callback.from_user.id not in admins:
            await callback.answer("❌ You are not authorized to access this information.")
            return

        user_count = await db.get_all_users_count()
        premium_users = await db.get_all_premium_users_count()

        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=f"👥 Total Users: {user_count}\n\n🌟 Premium Users: {premium_users}",
        )
    except Exception as e:
        logging.error(f"Error in get_users_count callback: {e}")
        await callback.answer("An error occurred while processing your request.")


@dp.message(Command("broadcast_msg_users"))
async def ask_broadcast_message(message: Message, state: FSMContext):
    if message.from_user.id not in admins:
        await message.answer("❌ You are not authorized to use this command.")
        return

    await message.answer("📣 Please type the message to broadcast to all users:")
    await state.set_state(BroadcastState.waiting_for_broadcast_message)


@dp.message(Command("broadcast_msg_user"))
async def ask_broadcast_single_user(message: Message, state: FSMContext):
    if message.from_user.id not in admins:
        await message.answer("❌ You are not authorized to use this command.")
        return

    await message.answer("📣 Please provide the user ID of the recipient:")
    await state.set_state(BroadcastUserState.waiting_for_user_id)


@dp.message(BroadcastState.waiting_for_broadcast_message)
async def send_broadcast(message: Message, state: FSMContext):
    text_to_send = message.text
    await state.clear()

    try:
        all_users = await db.user_collection.find({}, {"_id": 1}).to_list(None)
        success = 0
        failed = 0

        for user in all_users:
            try:
                await bot.send_message(chat_id=user["_id"], text=text_to_send)
                success += 1
            except Exception as e:
                failed += 1
                logging.warning(f"Failed to send message to user {user['_id']}: {e}")

        await message.answer(f"✅ Broadcast completed.\nSent: {success}\nFailed: {failed}")
    except Exception as e:
        logging.error(f"Broadcast error: {e}")
        await message.answer("❌ An error occurred during the broadcast.")


@dp.message(BroadcastUserState.waiting_for_user_id)
async def get_user_id(message: Message, state: FSMContext):
    user_id = message.text.strip()
    
    if not user_id.isdigit():
        await message.answer("❌ Invalid user ID. Please enter a valid user ID.")
        return

    await state.update_data(user_id=user_id)

    await message.answer("📣 Please type the message to send to this user:")
    await state.set_state(BroadcastUserState.waiting_for_broadcast_message)


@dp.message(BroadcastUserState.waiting_for_broadcast_message)
async def send_broadcast_to_user(message: Message, state: FSMContext):
    text_to_send = message.text

    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    
    await state.clear()

    formatted_text = (
        "📢 <b>Message from Admin:</b>\n\n"
        f"{text_to_send}"
    )

    try:
        await bot.send_message(
            chat_id=int(user_id),
            text=formatted_text,
            parse_mode="HTML"
        )

        await message.answer(
            f"✅ Message successfully sent to user <code>{user_id}</code>.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error sending message to user {user_id}: {e}")
        await message.answer("❌ An error occurred while sending the message.")
