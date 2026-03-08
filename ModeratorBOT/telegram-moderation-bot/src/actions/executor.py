from src.utils.logger import logger
from src.database import db
import asyncio

class ActionExecutor:
    def __init__(self, bot_instance, config: dict):
        self.bot = bot_instance
        self.action_config = config.get("actions", {})

    async def execute(self, actions: list, update_msg_obj, user_id: int, chat_id: int):
        # Sort actions by delay so quick actions (delete) happen before longer ones (report)
        actions = sorted(actions, key=lambda a: a.get("delay", 0))
        
        for action in actions:
            action_name = action.get("action")
            delay = action.get("delay", 0)
            
            if delay > 0:
                await asyncio.sleep(delay)
                
            config_params = self.action_config.get(action_name, {})
            
            try:
                if action_name == "delete":
                    await self.delete_message(chat_id, update_msg_obj.message_id)
                elif action_name == "warn":
                    msg = config_params.get("message", "Warning.")
                    await self.warn_user(chat_id, user_id, update_msg_obj.from_user.first_name, msg)
                elif action_name == "mute":
                    duration = config_params.get("duration", 300)
                    await self.mute_user(chat_id, user_id, duration)
                elif action_name == "restrict":
                    duration = config_params.get("duration", 3600)
                    await self.restrict_user(chat_id, user_id, duration)
                elif action_name == "remove":
                    await self.remove_user(chat_id, user_id)
                elif action_name == "ban":
                    await self.ban_user(chat_id, user_id)
            except Exception as e:
                logger.error(f"Execution error for rule action {action_name}: {e}")

    async def delete_message(self, chat_id: int, message_id: int):
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            await db.increment_daily_stats(chat_id)
            logger.info(f"[ACTION] Deleted message {message_id} in {chat_id}")
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")

    async def warn_user(self, chat_id: int, user_id: int, first_name: str, message: str):
        try:
            mention = f"<a href='tg://user?id={user_id}'>{first_name}</a>"
            await self.bot.send_message(
                chat_id=chat_id, 
                text=f"{mention}, {message}", 
                parse_mode="HTML"
            )
            logger.info(f"[ACTION] Warned user {user_id}")
        except Exception:
            pass

    async def mute_user(self, chat_id: int, user_id: int, duration: int):
        from telegram import ChatPermissions
        perms = ChatPermissions(can_send_messages=False)
        try:
            # For simplicity, passing time won't use exact unix format here but python-telegram-bot handles timedelta/datetime
            import datetime
            until = datetime.datetime.now() + datetime.timedelta(seconds=duration)
            await self.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=perms, until_date=until)
            logger.info(f"[ACTION] Muted user {user_id} for {duration}s")
        except Exception as e:
            logger.error(f"Failed to mute user {user_id}: {e}")
            
    async def restrict_user(self, chat_id: int, user_id: int, duration: int):
        from telegram import ChatPermissions
        perms = ChatPermissions(
            can_send_messages=True, 
            can_send_media_messages=False, 
            can_send_other_messages=False, 
            can_add_web_page_previews=False
        )
        try:
            import datetime
            until = datetime.datetime.now() + datetime.timedelta(seconds=duration)
            await self.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=perms, until_date=until)
            logger.info(f"[ACTION] Restricted user {user_id}")
        except Exception:
            pass

    async def remove_user(self, chat_id: int, user_id: int):
        try:
            await self.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            # Unban right after to just "kick", unless we want a permaban
            await self.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"[ACTION] Kicked user {user_id}")
        except Exception:
            pass

    async def ban_user(self, chat_id: int, user_id: int):
        try:
            await self.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            logger.info(f"[ACTION] Permanently banned user {user_id} in chat {chat_id}")
        except Exception as e:
            logger.warning(f"Could not ban user {user_id}: {e}")
