import os
import asyncio
import signal
from dotenv import load_dotenv
from src.database import db
from src.bot import TelegramBot
from src.utils.logger import logger

load_dotenv()

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        return

    # Initialize DB
    await db.init()

    # Create Bot
    bot = TelegramBot(token)
    
    # Setup graceful shutdown
    stop_event = asyncio.Event()

    def handle_sigterm(*args):
        logger.info("Received stop signal")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        await bot.start()
        await stop_event.wait()
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
