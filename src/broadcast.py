import asyncio
import aiosqlite
from aiogram import Bot
from config import BOT_TOKEN
from db import DB_NAME

async def main():
    bot = Bot(token=BOT_TOKEN)
    message_text = "Працювати в ресторані це СВЯТЕ ДІЛО для кожного з нас ))"
    
    success_count = 0
    fail_count = 0
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Отримуємо всіх користувачів з бази даних
        async with db.execute("SELECT user_id, first_name FROM users") as cursor:
            async for row in cursor:
                user_id = row[0]
                first_name = row[1] or "Користувач"
                
                try:
                    await bot.send_message(chat_id=user_id, text=message_text)
                    print(f"✅ Надіслано користувачу: {first_name} ({user_id})")
                    success_count += 1
                    await asyncio.sleep(0.05) # невелика пауза щоб не потрапити під спам-фільтр телеграму (ліміт ~30 повідомлень/сек)
                except Exception as e:
                    print(f"❌ Помилка надсилання користувачу {first_name} ({user_id}): {e}")
                    fail_count += 1
                    
    print("\n--- Результати розсилки ---")
    print(f"✅ Успішно надіслано: {success_count}")
    print(f"❌ Помилок: {fail_count}")
    
    # Закриваємо сесію бота
    await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
