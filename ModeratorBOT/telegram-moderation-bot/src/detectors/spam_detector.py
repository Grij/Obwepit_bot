from dataclasses import dataclass
from typing import Optional, Dict, Any
import re
from src.detectors.base import BaseDetector
from src.utils.logger import logger
from src.database import db

@dataclass
class SpamDetectionResult:
    is_spam: bool
    confidence: float
    reason: str
    details: Dict[str, Any]

class SpamDetector(BaseDetector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.spam_config = config.get("spam_detector", {})
        self.whitelisted_urls = self.spam_config.get("whitelisted_urls", [])

    async def _check_blacklist(self, text: str) -> Optional[SpamDetectionResult]:
        text_lower = text.lower()
        blacklist_words = await db.get_all_blacklist_words()
        for word in blacklist_words:
            if word.lower() in text_lower:
                return SpamDetectionResult(
                    is_spam=True,
                    confidence=1.0,
                    reason="blacklist_match",
                    details={"matched_word": word}
                )
        return None

    def _check_urls(self, text: str) -> Optional[SpamDetectionResult]:
        # Check for whitelisted URLs first to bypass if matched exactly
        for w_url in self.whitelisted_urls:
            if w_url in text:
                return None # Allow if it's a whitelisted URL
                
        patterns = self.spam_config.get("url_patterns", [])
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return SpamDetectionResult(
                    is_spam=True,
                    confidence=0.9,
                    reason="suspicious_urls",
                    details={"matched_pattern": pattern}
                )
        return None

    def _check_bot_patterns(self, text: str) -> Optional[SpamDetectionResult]:
        patterns = self.spam_config.get("bot_patterns", [])
        text_lower = text.lower()
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return SpamDetectionResult(
                    is_spam=True,
                    confidence=0.8,
                    reason="bot_pattern",
                    details={"matched_pattern": pattern}
                )
        return None

    def _check_caps(self, text: str) -> Optional[SpamDetectionResult]:
        if len(text) < 10:
            return None
        
        caps_count = sum(1 for c in text if c.isupper())
        letters_count = sum(1 for c in text if c.isalpha())
        
        if letters_count > 0:
            ratio = caps_count / letters_count
            threshold = self.spam_config.get("caps_threshold", 0.5)
            if ratio >= threshold:
                return SpamDetectionResult(
                    is_spam=True,
                    confidence=0.7,
                    reason="all_caps",
                    details={"caps_ratio": ratio}
                )
        return None

    async def detect(self, message: str) -> SpamDetectionResult:
        if not message:
            return SpamDetectionResult(False, 0.0, "none", {})

        # Run checks in order of priority/cost
        result = await self._check_blacklist(message)
        if result: return result

        result = self._check_urls(message)
        if result: return result

        result = self._check_bot_patterns(message)
        if result: return result

        result = self._check_caps(message)
        if result: return result

        return SpamDetectionResult(False, 0.0, "none", {})
