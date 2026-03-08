"""
Feedback Bot "Діма Альварес" (@Obwepit_bot)
Пересилає повідомлення юзерів у групу підтримки.
Адміни відповідають через Reply → бот надсилає відповідь юзеру.
"""

import asyncio
import json
import logging
import os
import os
from datetime import datetime, timedelta

import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

FEEDBACK_BOT_TOKEN = os.getenv("FEEDBACK_BOT_TOKEN")
SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", "0"))
POST_SIGNATURE_LINK = os.getenv("POST_SIGNATURE_LINK", "https://t.me/obwepit")
DB_NAME = "data/feedback.db"
UPLOADS_DIR = "data/uploads"

bot = Bot(token=FEEDBACK_BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FEEDBACK] %(message)s")
logger = logging.getLogger(__name__)


async def init_db():
    """Створення таблиць при старті."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_msg_id INTEGER UNIQUE,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback_blacklist (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                banned_by TEXT,
                banned_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                direction TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                status TEXT DEFAULT 'pending',
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                media_path TEXT,
                media_type TEXT,
                channels TEXT NOT NULL,
                scheduled_at DATETIME,
                pin_after BOOLEAN DEFAULT 0,
                signature TEXT,
                status TEXT DEFAULT 'pending',
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Спроба додати нову колонку delete_after (для сумісності з існуючою БД)
        try:
            await db.execute("ALTER TABLE scheduled_posts ADD COLUMN delete_after INTEGER DEFAULT 0")
        except Exception:
            pass
            
        await db.execute('''
            CREATE TABLE IF NOT EXISTS posted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                chat_id TEXT,
                message_id INTEGER,
                delete_at DATETIME
            )
        ''')
        await db.commit()
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    logger.info("Database initialized")


async def is_banned(user_id: int) -> bool:
    """Перевірка чи юзер у чорному списку."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT 1 FROM feedback_blacklist WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None


async def save_user(user):
    """Зберігає/оновлює юзера в базі feedback_users."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO feedback_users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        ''', (user.id, user.username, user.first_name, user.last_name))
        await db.commit()


# --- Команда /start (приватний чат) ---
@router.message(Command("start"), F.chat.type == "private")
async def cmd_start(message: Message):
    if await is_banned(message.from_user.id):
        return
    
    await save_user(message.from_user)
    
    await message.answer(
        "👋 <b>Привіт!</b>\n\n"
        "Я — бот зворотного зв'язку мережі <b>ОБЩЕПІТ</b>.\n\n"
        "Напишіть ваше питання, пропозицію або скаргу — "
        "і наша команда обов'язково відповість! 💬",
        parse_mode=ParseMode.HTML
    )


# --- Команда /chatid (для визначення ID чату підтримки) ---
@router.message(Command("chatid"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_chatid(message: Message):
    await message.reply(f"ℹ️ Chat ID цієї групи: <code>{message.chat.id}</code>", parse_mode=ParseMode.HTML)


# --- Команда /ban (в групі підтримки) ---
@router.message(Command("ban"), F.chat.id == SUPPORT_CHAT_ID)
async def cmd_ban(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.reply("Використання: /ban <user_id> [причина]")
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await message.reply("❌ user_id повинен бути числом")
        return
    
    reason = args[2] if len(args) > 2 else "Без причини"
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO feedback_blacklist (user_id, reason, banned_by) VALUES (?, ?, ?)",
            (user_id, reason, message.from_user.first_name)
        )
        await db.commit()
    
    await message.reply(f"🚫 Юзер <code>{user_id}</code> заблоковано.\nПричина: {reason}", parse_mode=ParseMode.HTML)
    
    # Повідомити юзера
    try:
        await bot.send_message(user_id, "🚫 Вас заблоковано у боті зворотного зв'язку.")
    except Exception:
        pass


# --- Команда /unban (в групі підтримки) ---
@router.message(Command("unban"), F.chat.id == SUPPORT_CHAT_ID)
async def cmd_unban(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Використання: /unban <user_id>")
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await message.reply("❌ user_id повинен бути числом")
        return
    
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM feedback_blacklist WHERE user_id = ?", (user_id,))
        await db.commit()
    
    await message.reply(f"✅ Юзер <code>{user_id}</code> розблоковано.", parse_mode=ParseMode.HTML)


# --- Приватні повідомлення → Форвард у групу ---
@router.message(F.chat.type == "private")
async def handle_user_message(message: Message):
    user_id = message.from_user.id
    
    # Зберігаємо юзера
    await save_user(message.from_user)
    
    # Перевірка бану
    if await is_banned(user_id):
        await message.answer("🚫 Вас заблоковано. Зверніться до адміністрації іншим способом.")
        return
    
    if SUPPORT_CHAT_ID == 0:
        logger.warning("SUPPORT_CHAT_ID not set! Cannot forward message.")
        await message.answer("⚠️ Бот ще не налаштований. Спробуйте пізніше.")
        return
    
    try:
        # Пересилаємо оригінальне повідомлення в групу підтримки
        forwarded = await message.forward(SUPPORT_CHAT_ID)
        
        # Зберігаємо маппінг
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR REPLACE INTO feedback_messages (group_msg_id, user_id, username, first_name) VALUES (?, ?, ?, ?)",
                (forwarded.message_id, user_id, message.from_user.username, message.from_user.first_name)
            )
            await db.execute(
                "INSERT INTO feedback_stats (user_id, direction) VALUES (?, 'incoming')",
                (user_id,)
            )
            await db.commit()
        
        await message.answer("✅ Ваше повідомлення надіслано! Очікуйте відповіді.")
        logger.info(f"Forwarded message from {user_id} to support chat")
        
    except Exception as e:
        logger.error(f"Failed to forward message: {e}")
        await message.answer("❌ Помилка при надсиланні. Спробуйте пізніше.")


# --- Reply в групі → Відповідь юзеру ---
@router.message(F.chat.id == SUPPORT_CHAT_ID, F.reply_to_message)
async def handle_admin_reply(message: Message):
    # Ігноруємо команди
    if message.text and message.text.startswith("/"):
        return
    
    replied_msg_id = message.reply_to_message.message_id
    
    # Шукаємо юзера за message_id
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT user_id, first_name FROM feedback_messages WHERE group_msg_id = ?",
            (replied_msg_id,)
        )
        row = await cursor.fetchone()
    
    if not row:
        # Може бути reply на заголовок, спробуємо шукати по сусідньому повідомленню
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            # Шукаємо найближчий маппінг (± 1 message)
            cursor = await db.execute(
                "SELECT user_id, first_name FROM feedback_messages WHERE group_msg_id BETWEEN ? AND ? ORDER BY group_msg_id DESC LIMIT 1",
                (replied_msg_id - 1, replied_msg_id + 1)
            )
            row = await cursor.fetchone()
    
    if not row:
        await message.reply("⚠️ Не вдалося визначити юзера. Відповідайте Reply на пересланому повідомленні.")
        return
    
    user_id = row['user_id']
    user_name = row['first_name']
    
    try:
        # Надсилаємо відповідь юзеру (органічно, без префіксів)
        if message.text:
            await bot.send_message(user_id, message.text)
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption or '')
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption=message.caption or '')
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption or '')
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id)
        elif message.sticker:
            await bot.send_sticker(user_id, message.sticker.file_id)
        else:
            await message.forward(user_id)
        
        # Логуємо статистику
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO feedback_stats (user_id, direction) VALUES (?, 'outgoing')",
                (user_id,)
            )
            await db.commit()
        
        await message.reply(f"✅ Відповідь надіслано юзеру {user_name}")
        logger.info(f"Reply sent to user {user_id} by {message.from_user.first_name}")
        
    except Exception as e:
        logger.error(f"Failed to send reply to {user_id}: {e}")
        await message.reply(f"❌ Не вдалося надіслати відповідь: {e}")


async def process_pending_broadcasts():
    """Фоновий процес: перевіряє 'pending' розсилки та відправляє їх."""
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM feedback_broadcasts WHERE status = 'pending' LIMIT 1")
                broadcast = await cursor.fetchone()

            if broadcast:
                broadcast_id = broadcast['id']
                text = broadcast['text']
                logger.info(f"Processing broadcast #{broadcast_id}: {text[:50]}...")

                # Встановлюємо статус 'sending'
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE feedback_broadcasts SET status = 'sending' WHERE id = ?", (broadcast_id,))
                    await db.commit()

                # Отримуємо всіх юзерів
                async with aiosqlite.connect(DB_NAME) as db:
                    db.row_factory = aiosqlite.Row
                    cursor = await db.execute("SELECT user_id FROM feedback_users")
                    users = await cursor.fetchall()

                sent = 0
                failed = 0

                for user in users:
                    try:
                        await bot.send_message(user['user_id'], text)
                        sent += 1
                    except Exception as e:
                        logger.warning(f"Failed to send to {user['user_id']}: {e}")
                        failed += 1
                    await asyncio.sleep(0.05)  # Anti-flood

                # Оновлюємо статус
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute(
                        "UPDATE feedback_broadcasts SET status = 'done', sent_count = ?, failed_count = ? WHERE id = ?",
                        (sent, failed, broadcast_id)
                    )
                    await db.commit()

                logger.info(f"Broadcast #{broadcast_id} done: {sent} sent, {failed} failed")

        except Exception as e:
            logger.error(f"Broadcast processor error: {e}")

        await asyncio.sleep(10)


async def process_scheduled_posts():
    """Фоновий процес: відправляє заплановані пости по каналах."""
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM scheduled_posts 
                    WHERE status = 'pending' 
                    AND (scheduled_at IS NULL OR scheduled_at <= datetime('now'))
                    LIMIT 1
                """)
                post = await cursor.fetchone()

            if post:
                post_id = post['id']
                text = post['text']
                media_path = post['media_path']
                media_type = post['media_type']
                channels_json = post['channels']
                pin_after = post['pin_after']
                signature = post['signature'] or ''
                # Використовуємо .keys() безпечно або get
                delete_after = 0
                if 'delete_after' in post.keys():
                    delete_after = post['delete_after'] or 0

                logger.info(f"Processing post #{post_id}: {text[:50]}...")

                # Встановлюємо статус 'sending'
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("UPDATE scheduled_posts SET status = 'sending' WHERE id = ?", (post_id,))
                    await db.commit()

                # Формуємо текст з підписом
                full_text = text
                if signature:
                    full_text = f"{text}\n\n{signature}"

                channels = json.loads(channels_json)
                sent = 0
                failed = 0

                for chat_id in channels:
                    try:
                        # Спроба конвертувати в int, якщо це не @username
                        try:
                            target_chat = int(chat_id)
                        except ValueError:
                            target_chat = chat_id

                        msg = None
                        if media_path and media_type == 'photo' and os.path.exists(media_path):
                            from aiogram.types import FSInputFile
                            photo = FSInputFile(media_path)
                            msg = await bot.send_photo(
                                chat_id=target_chat, photo=photo,
                                caption=full_text, parse_mode=ParseMode.HTML
                            )
                        elif media_path and media_type == 'video' and os.path.exists(media_path):
                            from aiogram.types import FSInputFile
                            video = FSInputFile(media_path)
                            msg = await bot.send_video(
                                chat_id=target_chat, video=video,
                                caption=full_text, parse_mode=ParseMode.HTML
                            )
                        else:
                            msg = await bot.send_message(
                                chat_id=target_chat, text=full_text,
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True
                            )

                        # Пінімо повідомлення
                        if pin_after and msg:
                            try:
                                await bot.pin_chat_message(
                                    chat_id=target_chat,
                                    message_id=msg.message_id,
                                    disable_notification=True
                                )
                            except Exception as pe:
                                logger.warning(f"Failed to pin in {chat_id}: {pe}")

                        # Планування видалення
                        if msg and delete_after > 0:
                            delete_dt_str = (datetime.now() + timedelta(hours=delete_after)).strftime("%Y-%m-%d %H:%M:%S")
                            async with aiosqlite.connect(DB_NAME) as db:
                                await db.execute(
                                    "INSERT INTO posted_messages (post_id, chat_id, message_id, delete_at) VALUES (?, ?, ?, ?)",
                                    (post_id, str(target_chat), msg.message_id, delete_dt_str)
                                )
                                await db.commit()

                        sent += 1
                    except Exception as e:
                        logger.warning(f"Failed to post to {chat_id}: {e}")
                        failed += 1
                    await asyncio.sleep(0.5)

                # Оновлюємо статус
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute(
                        "UPDATE scheduled_posts SET status = 'done', sent_count = ?, failed_count = ? WHERE id = ?",
                        (sent, failed, post_id)
                    )
                    await db.commit()

                logger.info(f"Post #{post_id} done: {sent} sent, {failed} failed")

        except Exception as e:
            logger.error(f"Post processor error: {e}")

        await asyncio.sleep(15)


async def process_deletions():
    """Фоновий процес: видаляє старі повідомлення за розкладом delete_at."""
    while True:
        try:
            async with aiosqlite.connect(DB_NAME) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM posted_messages 
                    WHERE delete_at <= datetime('now', 'localtime')
                """)
                messages = await cursor.fetchall()

            for msg in messages:
                _id = msg['id']
                chat_id = msg['chat_id']
                message_id = msg['message_id']
                
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    logger.info(f"Auto-deleted message {message_id} from {chat_id}")
                except Exception as e:
                    logger.warning(f"Failed to auto-delete msg {message_id} in {chat_id}: {e}")
                
                async with aiosqlite.connect(DB_NAME) as db:
                    await db.execute("DELETE FROM posted_messages WHERE id = ?", (_id,))
                    await db.commit()
                
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Deletions processor error: {e}")

        await asyncio.sleep(30)


async def main():
    await init_db()
    logger.info(f"Feedback bot starting... SUPPORT_CHAT_ID={SUPPORT_CHAT_ID}")

    # Видаляємо старий webhook (Livegram)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook deleted, starting polling")

    # Запускаємо фонові процеси
    asyncio.create_task(process_pending_broadcasts())
    asyncio.create_task(process_scheduled_posts())
    asyncio.create_task(process_deletions())
    logger.info("Background processors started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
