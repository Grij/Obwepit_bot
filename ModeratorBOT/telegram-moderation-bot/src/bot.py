from telegram.ext import Application, CommandHandler, MessageHandler as TGMessageHandler, filters
from src.handlers.message_handler import MessageHandler
from src.handlers.admin_commands import (
    cmd_status, cmd_ban, cmd_mute, cmd_rules, 
    cmd_blacklist_add, cmd_blacklist_remove, cmd_blacklist_list, cmd_blacklist, cmd_stats
)
from src.detectors.spam_detector import SpamDetector
from src.detectors.flood_detector import FloodDetector
from src.detectors.fake_distribution import FakeDistributionDetector
from src.rules.engine import RuleEngine
from src.actions.executor import ActionExecutor
from src.utils.logger import logger
import yaml

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(self.token).build()
        
        # Load config
        with open("config/config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            
        # Initialize components
        self.spam_detector = SpamDetector(self.config)
        self.flood_detector = FloodDetector(self.config)
        self.fake_detector = FakeDistributionDetector(self.config)
        self.rule_engine = RuleEngine()
        self.executor = ActionExecutor(self.app.bot, self.config)
        
        self.msg_handler = MessageHandler(
            spam_detector=self.spam_detector,
            flood_detector=self.flood_detector,
            fake_detector=self.fake_detector,
            rule_engine=self.rule_engine,
            executor=self.executor
        )

    def _setup_handlers(self):
        # Admin Commands
        self.app.add_handler(CommandHandler("status", cmd_status))
        self.app.add_handler(CommandHandler("ban", cmd_ban))
        self.app.add_handler(CommandHandler("mute", cmd_mute))
        self.app.add_handler(CommandHandler("rules", cmd_rules))
        self.app.add_handler(CommandHandler("blacklist_add", cmd_blacklist_add))
        self.app.add_handler(CommandHandler("blacklist_remove", cmd_blacklist_remove))
        self.app.add_handler(CommandHandler("blacklist_list", cmd_blacklist_list))
        self.app.add_handler(CommandHandler("blacklist", cmd_blacklist))
        self.app.add_handler(CommandHandler("stats", cmd_stats))
        
        # Message Handler
        self.app.add_handler(TGMessageHandler(filters.ALL & ~filters.COMMAND, self.msg_handler.handle))

    async def start(self):
        logger.info("Starting ModeratorBOT...")
        self._setup_handlers()
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("Bot is polling for updates...")

    async def stop(self):
        logger.info("Stopping ModeratorBOT...")
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
