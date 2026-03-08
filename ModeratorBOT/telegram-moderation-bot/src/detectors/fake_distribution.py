from dataclasses import dataclass
from src.detectors.base import BaseDetector
import hashlib
from src.utils.cache import cache

@dataclass
class FakeDistributionResult:
    is_fake: bool
    detection_type: str
    similar_messages_count: int

class FakeDistributionDetector(BaseDetector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.fake_config = config.get("fake_distribution", {})
        self.referral_domains = self.fake_config.get("referral_domains", [])
        self.copy_threshold = self.fake_config.get("copy_threshold", 5)

    def _check_referral_links(self, text: str) -> bool:
        text_lower = text.lower()
        for domain in self.referral_domains:
            if domain in text_lower:
                return True
        return False

    def _check_message_copy(self, user_id: int, text: str) -> int:
        if len(text) < 20: 
            return 0
            
        # Create a hash of the text (ignoring case and whitespace)
        normalized_text = "".join(text.lower().split())
        msg_hash = hashlib.md5(normalized_text.encode('utf-8')).hexdigest()
        
        cache.record_message_hash(msg_hash, user_id)
        return cache.get_hash_count(msg_hash)

    def detect(self, user_id: int, message: str) -> FakeDistributionResult:
        if not message:
            return FakeDistributionResult(False, "none", 0)

        # 1. Referral links
        if self._check_referral_links(message):
            return FakeDistributionResult(True, "referral", 0)

        # 2. Copied content
        copy_count = self._check_message_copy(user_id, message)
        if copy_count >= self.copy_threshold:
            return FakeDistributionResult(True, "copied", copy_count)

        return FakeDistributionResult(False, "none", 0)
