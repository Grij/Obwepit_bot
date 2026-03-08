from telegram import Update
from telegram.ext import ContextTypes
from src.utils.logger import logger
from src.database import db
from src.user.monitor import monitor

class MessageHandler:
    def __init__(self, spam_detector, flood_detector, fake_detector, rule_engine, executor):
        self.spam_detector = spam_detector
        self.flood_detector = flood_detector
        self.fake_detector = fake_detector
        self.rule_engine = rule_engine
        self.executor = executor

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_chat:
            return
            
        chat = update.effective_chat
        user = update.effective_user
        msg = update.message
        
        # Pre-checks
        if user.is_bot and user.id != context.bot.id:
            # Let other bots live unless specific rules apply, but generally ignore system 
            pass
            
        is_admin = False
        try:
            member = await chat.get_member(user.id)
            if member.status in ['creator', 'administrator']:
                is_admin = True
        except Exception:
            pass
            
        # Detectors
        text = msg.text or msg.caption or ""
        
        # 1. Flood
        flood_res = self.flood_detector.detect(user.id)
        
        # 2. Spam
        spam_res = await self.spam_detector.detect(text)
        
        # 3. Fake Distribution
        fake_res = self.fake_detector.detect(user.id, text)
        
        # Monitor record
        await monitor.record_message({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "is_bot": user.is_bot
        }, msg.message_id, text)

        # Rule Matching
        matched_rules = self.rule_engine.find_matching_rules(spam_res, fake_res, flood_res)
        
        actions_to_take = []
        applied_rules = []
        for rule in matched_rules:
            if self.rule_engine.should_apply_rule(rule, user.id, is_admin):
                actions_to_take.extend(rule.get("actions", []))
                applied_rules.append(rule.get("name"))
                
        # Execution
        if actions_to_take:
            logger.info(f"Applying rules {applied_rules} to user {user.id}")
            await self.executor.execute(actions_to_take, msg, user.id, chat.id)
            
            # Log incident
            reason = ", ".join(applied_rules)
            await db.log_incident(
                user.id, 
                "moderation_action", 
                "high" if "ban" in [a.get("action") for a in actions_to_take] else "medium", 
                str([a.get("action") for a in actions_to_take]), 
                reason
            )
