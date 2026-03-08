from telegram import Update
from telegram.ext import ContextTypes
from src.utils.logger import logger
from src.database import db

async def is_admin(update: Update) -> bool:
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except Exception:
        return False

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    await update.message.reply_text("ModeratorBOT is online and actively verifying messages.")

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
        
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to ban the user.")
        return
        
    target_user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        reason = " ".join(context.args) if context.args else "Admin requested"
        await db.log_incident(target_user.id, "manual_ban", "high", "ban", reason)
        await update.message.reply_text(f"User {target_user.first_name} banned.")
    except Exception as e:
        err = str(e)
        if "Participant_id_invalid" in err:
            await update.message.reply_text("Не вдалося забанити: користувач уже недоступний у цьому чаті.")
        else:
            await update.message.reply_text(f"Failed: {e}")

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
        
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message to mute the user.")
        return
        
    target_user = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    try:
        duration = int(context.args[0]) if context.args else 300
    except (TypeError, ValueError):
        await update.message.reply_text("Usage: /mute <seconds>. Example: /mute 300")
        return
    
    from telegram import ChatPermissions
    import datetime
    perms = ChatPermissions(can_send_messages=False)
    until = datetime.datetime.now() + datetime.timedelta(seconds=duration)
    
    try:
        await context.bot.restrict_chat_member(chat_id, target_user.id, permissions=perms, until_date=until)
        await db.log_incident(target_user.id, "manual_mute", "medium", "mute", f"Muted for {duration}s")
        await update.message.reply_text(f"User {target_user.first_name} muted for {duration} seconds.")
    except Exception as e:
        await update.message.reply_text(f"Failed: {e}")
        
async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
        
    # We could theoretically retrieve the rules from the rule_engine instance via a global or app context
    await update.message.reply_text("Rules engine active. Check system logs for full rule dump.")

async def cmd_blacklist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /blacklist_add <word or phrase>")
        return
    
    word = " ".join(context.args)
    success = await db.add_blacklist_word(word, update.effective_user.id)
    if success:
        await update.message.reply_text(f"✅ Added '{word}' to the global blacklist.")
    else:
        await update.message.reply_text(f"⚠️ '{word}' is already in the blacklist.")

async def cmd_blacklist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /blacklist_remove <word or phrase>")
        return
    
    word = " ".join(context.args)
    success = await db.remove_blacklist_word(word)
    if success:
        await update.message.reply_text(f"✅ Removed '{word}' from the global blacklist.")
    else:
        await update.message.reply_text(f"⚠️ '{word}' was not found in the blacklist.")

async def cmd_blacklist_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    
    words = await db.get_all_blacklist_words()
    if not words:
        await update.message.reply_text("The global blacklist is empty.")
    else:
        word_list = "\n".join([f"- {w}" for w in words])
        await update.message.reply_text(f"📜 Global Blacklist:\n{word_list}")


async def cmd_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias command for UX: /blacklist add|remove|list ..."""
    if not await is_admin(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/blacklist add <word or phrase>\n"
            "/blacklist remove <word or phrase>\n"
            "/blacklist list"
        )
        return

    action = context.args[0].lower()
    context.args = context.args[1:]

    if action == "add":
        await cmd_blacklist_add(update, context)
        return
    if action in ("remove", "rm", "del", "delete"):
        await cmd_blacklist_remove(update, context)
        return
    if action == "list":
        await cmd_blacklist_list(update, context)
        return

    await update.message.reply_text("Unknown action. Use: add, remove, list.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    
    # Simple stats fetch showing total deleted for today
    import aiosqlite
    from datetime import datetime
    today = datetime.now().date().isoformat()
    
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Get total for today across all chats
        cursor = await conn.execute("SELECT SUM(deleted_count) as total FROM daily_stats WHERE date = ?", (today,))
        row = await cursor.fetchone()
        total_today = row['total'] if row and row['total'] else 0
        
        # Get per-chat breakdown
        cursor = await conn.execute("SELECT chat_id, deleted_count FROM daily_stats WHERE date = ?", (today,))
        rows = await cursor.fetchall()
        
    stats_msg = f"📊 **Daily Stats ({today}):**\n\nTotal messages deleted: {total_today}\n\n"
    if rows:
        for r in rows:
            stats_msg += f"- Chat ID `{r['chat_id']}`: {r['deleted_count']} deleted\n"
    else:
        stats_msg += "No messages silently deleted today."
        
    await update.message.reply_text(stats_msg, parse_mode="Markdown")
