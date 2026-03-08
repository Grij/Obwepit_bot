import json
from typing import List, Dict, Any
from src.utils.logger import logger
from src.detectors.spam_detector import SpamDetectionResult
from src.detectors.flood_detector import FloodDetectionResult
from src.detectors.fake_distribution import FakeDistributionResult

class RuleEngine:
    def __init__(self, rules_path="config/rules.json"):
        self.rules_path = rules_path
        self.rules = []
        self.load_rules()

    def load_rules(self):
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.rules = sorted(data.get("rules", []), key=lambda x: x.get("priority", 0), reverse=True)
            logger.info(f"Loaded {len(self.rules)} moderation rules.")
        except Exception as e:
            logger.error(f"Failed to load rules from {self.rules_path}: {e}")

    def find_matching_rules(self, 
                            spam_res: SpamDetectionResult, 
                            fake_res: FakeDistributionResult, 
                            flood_res: FloodDetectionResult) -> List[Dict]:
        matched = []
        for rule in self.rules:
            cond = rule.get("condition", {})
            detector_name = cond.get("detector")
            field = cond.get("field")
            op = cond.get("operator")
            val = cond.get("value")

            matches = False
            
            if detector_name == "spam" and spam_res:
                actual_val = getattr(spam_res, field, None)
                if op == "equals" and actual_val == val:
                    matches = True
            elif detector_name == "flood" and flood_res:
                actual_val = getattr(flood_res, field, None)
                if op == "equals" and actual_val == val:
                    matches = True
            elif detector_name == "fake" and fake_res:
                actual_val = getattr(fake_res, field, None)
                if op == "equals" and actual_val == val:
                    matches = True
            
            if matches:
                 matched.append(rule)
                 
        return matched

    def should_apply_rule(self, rule: Dict, user_id: int, is_admin: bool) -> bool:
        if is_admin:
            return False
            
        # Additional exception logic could be added here (e.g whitelisted user IDs)
        exceptions = rule.get("exceptions", {})
        if user_id in exceptions.get("user_ids", []):
            return False
            
        return True
