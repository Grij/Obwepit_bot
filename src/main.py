import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import router
from db import init_db, DB_NAME
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiosqlite

async def collect_channel_stats(bot: Bot):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT chat_id FROM channels WHERE is_active = 1") as cursor:
            async for row in cursor:
                chat_id = row[0]
                try:
                    count = await bot.get_chat_member_count(chat_id)
                    await db.execute('''
                        INSERT INTO channel_stats (chat_id, subscribers_count)
                        VALUES (?, ?)
                    ''', (chat_id, count))
                except Exception as e:
                    logging.error(f"Failed to get members for {chat_id}: {e}")
        await db.commit()

async def process_pending_broadcasts(bot: Bot):
    async with aiosqlite.connect(DB_NAME) as db:
        # Шукаємо розсилки зі статусом pending
        cursor = await db.execute("SELECT id, text FROM broadcasts WHERE status = 'pending'")
        broadcasts = await cursor.fetchall()
        
        for b_id, text in broadcasts:
            # Оновлюємо статус на in_progress
            await db.execute("UPDATE broadcasts SET status = 'in_progress' WHERE id = ?", (b_id,))
            await db.commit()
            
            success_count = 0
            fail_count = 0
            
            # Робимо розсилку
            async with db.execute("SELECT user_id FROM users") as user_cursor:
                async for row in user_cursor:
                    user_id = row[0]
                    try:
                        await bot.send_message(chat_id=user_id, text=text)
                        success_count += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        fail_count += 1
                        
            # Завершуємо розсилку
            await db.execute('''
                UPDATE broadcasts 
                SET status = 'completed', sent_count = ?, failed_count = ?
                WHERE id = ?
            ''', (success_count, fail_count, b_id))
            await db.commit()

async def main():
    await init_db()  # Ініціалізація бази даних
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Запускаємо планувальник
    scheduler = AsyncIOScheduler()
    scheduler.add_job(collect_channel_stats, 'interval', hours=4, args=[bot])
    scheduler.add_job(process_pending_broadcasts, 'interval', minutes=1, args=[bot])
    scheduler.start()
    
    dp.include_router(router)
    
    print("Бот 'Общепіт' успішно запущений!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
