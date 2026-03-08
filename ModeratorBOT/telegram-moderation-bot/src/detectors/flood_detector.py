from dataclasses import dataclass
from src.detectors.base import BaseDetector
from src.utils.cache import cache
import time

@dataclass
class FloodDetectionResult:
    is_flood: bool
    level: str
    action: str
    duration: int = 0

class FloodDetector(BaseDetector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.flood_config = config.get("flood_detector", {})
        self.levels = sorted(self.flood_config.get("levels", []), key=lambda x: x.get("messages", 0), reverse=True)

    def detect(self, user_id: int) -> FloodDetectionResult:
        cache.add_user_activity(user_id)
        activity = cache.get_user_activity(user_id)
        now = time.time()
        
        # timestamps are stored as datetime, we need them converted to check windows
        activity_timestamps = [t.timestamp() for t in activity]

        for level in self.levels:
            window = level.get("window", 60)
            threshold = level.get("messages", 10)
            
            recent_count = sum(1 for t in activity_timestamps if now - t <= window)
            
            if recent_count >= threshold:
                return FloodDetectionResult(
                    is_flood=True,
                    level=level.get("name", "warning"),
                    action=level.get("action", "delete"),
                    duration=level.get("duration", 0)
                )

        return FloodDetectionResult(False, "none", "none")
