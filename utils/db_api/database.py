import uuid
import logging
from typing import Optional, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from data.config import mongodb_uri, models


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db = self.client["chatgpt_telegram_bot"]

        self.user_collection = self.db["user"]
        self.dialog_collection = self.db["dialog"]

    async def check_if_user_exists(self, user_id: int, raise_exception: bool = False):
        """Check if user exists in the database"""
        try:
            count = await self.user_collection.count_documents({"_id": user_id})
            if count > 0:
                return True
            if raise_exception:
                raise ValueError(f"User {user_id} does not exist")
            return False
        except Exception as e:
            logging.error(f"Failed to check if user exists: {e}")

    async def add_new_user(
            self,
            user_id: int,
            chat_id: int,
            username: str = "",
            first_name: str = "",
            last_name: str = "",
    ):
        user_dict = {
            "_id": user_id,
            "chat_id": chat_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "last_interaction": datetime.now(),
            "first_seen": datetime.now(),
            "current_dialog_id": None,
            "current_chat_mode": "assistant",
            "current_model": models["available_text_models"][0],
            "n_used_tokens": {},
            "is_paid": False,
            "payment_date": None,
            "payment_valid_date": None,
            "payment_type": "free",
            "daily_voice_count": 0,
            "full_speaking": 1,
            "last_voice_date": None,
            "used_promo_codes": [],
            "invited_users": 0,
            "referred_by": None,
        }

        if not await self.check_if_user_exists(user_id):
            await self.user_collection.insert_one(user_dict)
    
    async def get_user(self, user_id: int) -> dict:
        return await self.user_collection.find_one({"_id": user_id}) or {}

    async def start_new_dialog(self, user_id: int):
        """Start a new dialog for the user"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)

            dialog_id = str(uuid.uuid4())
            dialog_dict = {
                "_id": dialog_id,
                "user_id": user_id,
                "chat_mode": await self.get_user_attribute(user_id, "current_chat_mode"),
                "start_time": datetime.now(),
                "model": await self.get_user_attribute(user_id, "current_model"),
                "messages": []
            }

            # Add new dialog
            await self.dialog_collection.insert_one(dialog_dict)

            # Update user's current dialog
            await self.user_collection.update_one(
                {"_id": user_id},
                {"$set": {"current_dialog_id": dialog_id}}
            )

            return dialog_id
        except Exception as e:
            logging.error(f"Failed to start new dialog: {e}")

    async def get_user_attribute(self, user_id: int, key: str):
        """Get user attribute from the database"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)
            user_dict = await self.user_collection.find_one({"_id": user_id})

            return user_dict.get(key, None)
        except Exception as e:
            logging.error(f"Failed to get user attribute: {e}")

    async def set_user_attribute(self, user_id: int, key: str, value: Any):
        """Set user attribute in the database"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)
            await self.user_collection.update_one(
                {"_id": user_id}, {"$set": {key: value}}
            )
        except Exception as e:
            logging.error(f"Failed to set user attribute: {e}")

    async def update_n_used_tokens(self, user_id: int, model: str, n_input_tokens: int, n_output_tokens: int):
        """Update the number of tokens used by the user for a specific model"""
        try:
            n_used_tokens_dict = await self.get_user_attribute(user_id, "n_used_tokens")

            if model in n_used_tokens_dict:
                n_used_tokens_dict[model]["n_input_tokens"] += n_input_tokens
                n_used_tokens_dict[model]["n_output_tokens"] += n_output_tokens
            else:
                n_used_tokens_dict[model] = {
                    "n_input_tokens": n_input_tokens,
                    "n_output_tokens": n_output_tokens
                }

            await self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens_dict)
        except Exception as e:
            logging.error(f"Failed to update n_used_tokens: {e}")

    async def get_dialog_messages(self, user_id: int, dialog_id: Optional[str] = None):
        """Get messages in the current dialog"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)

            if dialog_id is None:
                dialog_id = await self.get_user_attribute(user_id, "current_dialog_id")

            dialog_dict = await self.dialog_collection.find_one(
                {"_id": dialog_id, "user_id": user_id}
            )
            return dialog_dict["messages"]
        except Exception as e:
            logging.error(f"Failed to get dialog messages: {e}")

    async def set_dialog_messages(self, user_id: int, dialog_messages: list, dialog_id: Optional[str] = None):
        """Set messages in the current dialog"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)

            if dialog_id is None:
                dialog_id = await self.get_user_attribute(user_id, "current_dialog_id")

            await self.dialog_collection.update_one(
                {"_id": dialog_id, "user_id": user_id},
                {"$set": {"messages": dialog_messages}}
            )
        except Exception as e:
            logging.error(f"Failed to set dialog messages: {e}")

    async def get_all_users_count(self):
        return await self.user_collection.count_documents({})

    async def get_all_premium_users_count(self):
        """Get all number of premium users"""
        return await self.user_collection.count_documents({"is_paid": True})

    async def get_all_users_info(self):
        """Get information about all users"""
        try:
            all_users_info = []

            async for user in self.user_collection.find():
                full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                username = user.get('username', '')
                user_id = user.get('_id', '')

                user_info = {
                    'full_name': full_name,
                    'username': username,
                    'user_id': user_id
                }

                all_users_info.append(user_info)

            return all_users_info
        except Exception as e:
            logging.error(f"Failed to get all users info: {e}")

    async def get_active_users_count(self, last_days=7):
        """Get count of users active in last N days"""
        try:
            date_threshold = datetime.now() - timedelta(days=last_days)
            return await self.user_collection.count_documents({
                "last_interaction": {"$gte": date_threshold}
            })
        except Exception as e:
            logging.error(f"Failed to get active users count: {e}")

    async def get_total_messages_count(self):
        """Get total number of messages in all dialogs"""
        try:
            pipeline = [
                {"$unwind": "$messages"},
                {"$count": "total"}
            ]
            result = await self.dialog_collection.aggregate(pipeline).to_list(length=1)
            return 0 if not result else result[0]["total"]
        except Exception as e:
            logging.error(f"Failed to get total messages count: {e}")
            return 0

    async def update_user_last_interaction(self, user_id: int):
        """Update user's last interaction time"""
        try:
            await self.user_collection.update_one(
                {"_id": user_id},
                {"$set": {"last_interaction": datetime.now()}}
            )
        except Exception as e:
            logging.error(f"Failed to update user last interaction: {e}")

    async def update_user_info(self, user_id: int, chat_id: int, username: str = "", first_name: str = "",
                               last_name: str = ""):
        """Update user information if changed"""
        try:
            update_data = {
                "chat_id": chat_id,
                "last_interaction": datetime.now()
            }

            if username:
                update_data["username"] = username
            if first_name:
                update_data["first_name"] = first_name
            if last_name:
                update_data["last_name"] = last_name

            await self.user_collection.update_one(
                {"_id": user_id},
                {"$set": update_data},
                upsert=True
            )
        except Exception as e:
            logging.error(f"Failed to update user info: {e}")

    async def reset_voice_count_if_needed(self, user_id: int):
        """Reset daily voice message count if needed"""
        try:
            user = await self.user_collection.find_one({"_id": user_id})
            last_reset = user.get("last_voice_reset", datetime.min)
            if last_reset.date() < datetime.now().date():
                await self.user_collection.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "daily_voice_count": 0,
                            "last_voice_reset": datetime.now()
                        }
                    }
                )
        except Exception as e:
            logging.error(f"Failed to reset voice count: {e}")

    async def set_paid(self, user_id: int):
        """Set user as paid for one month"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)

            payment_date = datetime.now()

            await self.user_collection.update_one(
                {"_id": user_id},
                {"$set": {
                    "is_paid": True,
                    "payment_date": payment_date
                }}
            )
        except Exception as e:
            logging.error(f"Failed to set user as paid: {e}")

    async def update_voice_count(self, user_id: int):
        """Update daily voice message count"""
        try:
            await self.check_if_user_exists(user_id, raise_exception=True)

            user = await self.user_collection.find_one({"_id": user_id})
            last_voice_date = user.get("last_voice_date")
            daily_voice_count = user.get("daily_voice_count", 0)

            today = datetime.now().date()

            if last_voice_date is None or last_voice_date.date() != today:
                daily_voice_count = 0

            daily_voice_count += 1

            await self.user_collection.update_one(
                {"_id": user_id},
                {"$set": {
                    "daily_voice_count": daily_voice_count,
                    "last_voice_date": datetime.now()
                }}
            )
        except Exception as e:
            logging.error(f"Failed to update voice count: {e}")

    async def get_user_daily_count(self, user_id: int) -> int:
        """Get the daily voice message count for a user."""
        try:
            user = await self.user_collection.find_one({"_id": user_id})

            if not user:
                return 0

            last_voice_date = user.get("last_voice_date")
            daily_voice_count = user.get("daily_voice_count", 0)

            today = datetime.now().date()

            if last_voice_date is None or last_voice_date.date() != today:
                return 0

            return daily_voice_count
        except Exception as e:
            logging.error(f"Failed to get user daily voice count: {e}")
            return 0
