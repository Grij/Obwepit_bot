import asyncio
from aiogram import Bot
from config import BOT_TOKEN

async def test_bot():
    bot = Bot(token=BOT_TOKEN)
    try:
        chat = await bot.get_chat('@obwepit_kyiv')
        print(f"Chat found: {chat.title}")
        admins = await bot.get_chat_administrators('@obwepit_kyiv')
        bot_member = await bot.get_me()
        is_admin = any(admin.user.id == bot_member.id for admin in admins)
        print(f"Is bot admin? {is_admin}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(test_bot())
