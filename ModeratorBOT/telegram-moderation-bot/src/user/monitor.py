from src.database import db
from src.utils.logger import logger
from src.utils.cache import cache

class UserMonitor:
    def __init__(self):
        pass

    async def record_message(self, user: dict, message_id: int, text: str):
        # 1. Update user profile/count
        await db.add_or_update_user({
            "user_id": user.get("id"),
            "username": user.get("username"),
            "first_name": user.get("first_name"),
            "is_bot": user.get("is_bot")
        })
        
        # 2. Record message
        await db.log_message(user.get("id"), message_id, text)
        
        # 3. Add to recent activity cache for flood detection
        cache.add_user_activity(user.get("id"))

    async def add_warning(self, user_id: int, reason: str):
        # Already handled inside db.log_incident but could have extra logic here
        pass

    async def get_user_stats(self, user_id: int):
        return await db.get_user_stats(user_id)

monitor = UserMonitor()
