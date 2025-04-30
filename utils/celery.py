import asyncio
import logging

from celery import Celery
from data.config import celery_broker_url, celery_result_backend, admins
from aiogram.enums import ParseMode

from loader import bot, db

celery_app = Celery(
    'celery_tasks',
    broker=celery_broker_url,
    backend=celery_result_backend,
    include=['utils.celery']
)

celery_app.autodiscover_tasks(['utils'])

CELERY_COMMON_CONFIG = {
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'broker_connection_retry_on_startup': True,
    'task_acks_late': True,
    'worker_prefetch_multiplier': 1,
    'task_routes': {
        '*': {'queue': 'celery'}
    }
}

celery_app.conf.update(**CELERY_COMMON_CONFIG)


def get_or_create_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "no current event loop" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop


@celery_app.task(name="utils.celery_app.add_user_to_database")
def add_user_to_database(user_id, chat_id, username, first_name, last_name):
    try:
        loop = get_or_create_event_loop()
        loop.run_until_complete(
            db.add_new_user(user_id, chat_id, username, first_name, last_name)
        )
    except Exception as e:
        logging.error(f"Error in celery: Adding user to database: {e}")


@celery_app.task(name="utils.celery_app.check_user_exists")
def check_user_exists(user_id, chat_id, username, first_name, last_name):
    """Background task to check if a user exists in the database, then add or update"""
    try:
        loop = get_or_create_event_loop()
        user_exists = loop.run_until_complete(
            db.check_if_user_exists(user_id)
        )

        if not user_exists:
            add_user_to_database.delay(user_id, chat_id, username, first_name, last_name)
        else:
            update_user_info_in_database.delay(user_id, chat_id, username, first_name, last_name)

        update_user_last_interaction_in_db.delay(user_id)

    except Exception as e:
        logging.error(f"Error in celery: Checking user existence in database: {e}")


@celery_app.task(name="utils.celery_app.update_user_info_in_database")
def update_user_info_in_database(user_id, chat_id, username, first_name, last_name):
    try:
        loop = get_or_create_event_loop()
        loop.run_until_complete(
            db.update_user_info(user_id, chat_id, username, first_name, last_name)
        )
    except Exception as e:
        logging.error(f"Error in celery: Updating user info in database: {e}")


@celery_app.task(name="utils.celery_app.update_user_last_interaction_in_db")
def update_user_last_interaction_in_db(user_id):
    try:
        loop = get_or_create_event_loop()
        loop.run_until_complete(
            db.update_user_last_interaction(user_id)
        )
    except Exception as e:
        logging.error(f"Error in celery: Updating user last interaction in database: {e}")


@celery_app.task(name="utils.celery_app.send_message_to_admin")
def send_message_to_admin(user_id, username, message):
    async def send():
        try:
            for admin in admins:
                admin_message = (
                    f"📩 <b>New Message from User</b>\n\n"
                    f"👤 <b>Username:</b> {username if username else 'N/A'}\n"
                    f"🆔 <b>User ID:</b> {user_id}\n\n"
                    f"📨 <b>Message:</b>\n{message}"
                )
                await bot.send_message(chat_id=admin, text=admin_message, parse_mode=ParseMode.HTML)
        except Exception as e:
            logging.error(f"Error in celery: Sending message to admin: {e}")

    loop = get_or_create_event_loop()
    loop.run_until_complete(send())


@celery_app.task(name="utils.celery_app.send_invite_notification_to_referrer")
def send_invite_notification_to_referrer(referrer_id, new_user_id):
    """Send notification to the referrer when a new user registers using their invite link"""
    async def send():
        try:
            referrer_data = await db.get_user(referrer_id)
            referrer_chat_id = referrer_data.get("chat_id")
            new_user_data = await db.get_user(new_user_id)

            new_user_username = new_user_data.get("username")
            if not new_user_username:
                new_user_username = f"{new_user_data.get('first_name', 'Unknown')} {new_user_data.get('last_name', '')}".strip() or "Unknown User"

            message = (
                f"🎉 You have a new referral!\n\n"
                f"User {new_user_username} has registered using your invite link!\n"
                f"Keep inviting more users and earn more rewards! 🚀"
            )
            
            await bot.send_message(referrer_chat_id, message)

        except Exception as e:
            logging.error(f"Error in celery: Sending invite notification to referrer: {e}")

    loop = get_or_create_event_loop()
    loop.run_until_complete(send())
