from datetime import datetime, timedelta
import asyncio

class Cache:
    """
    In-memory cache for user activity, message hashes, and patterns.
    """
    def __init__(self):
        self._user_activity = {} # {user_id: [datetime,...]}
        self._message_hashes = {} # {hash: {"count": N, "users": set(), "expires_at": datetime}}
        self._regex_patterns = {} # {pattern_string: re.Pattern}

    def add_user_activity(self, user_id: int):
        now = datetime.now()
        if user_id not in self._user_activity:
            self._user_activity[user_id] = []
        self._user_activity[user_id].append(now)
        # Cleanup older than 1 hour
        cutoff = now - timedelta(hours=1)
        self._user_activity[user_id] = [t for t in self._user_activity[user_id] if t > cutoff]

    def get_user_activity(self, user_id: int) -> list[datetime]:
        self._cleanup_expired_activity(user_id)
        return self._user_activity.get(user_id, [])

    def _cleanup_expired_activity(self, user_id: int):
        if user_id in self._user_activity:
            cutoff = datetime.now() - timedelta(hours=1)
            self._user_activity[user_id] = [t for t in self._user_activity[user_id] if t > cutoff]

    def record_message_hash(self, msg_hash: str, user_id: int):
        now = datetime.now()
        if msg_hash not in self._message_hashes or self._message_hashes[msg_hash]["expires_at"] < now:
            self._message_hashes[msg_hash] = {
                "count": 0,
                "users": set(),
                "expires_at": now + timedelta(days=1)
            }
        
        self._message_hashes[msg_hash]["count"] += 1
        self._message_hashes[msg_hash]["users"].add(user_id)

    def get_hash_count(self, msg_hash: str) -> int:
        entry = self._message_hashes.get(msg_hash)
        if not entry or entry["expires_at"] < datetime.now():
            return 0
        return entry["count"]

    def cache_regex(self, pattern: str, compiled_regex):
        self._regex_patterns[pattern] = compiled_regex
        
    def get_regex(self, pattern: str):
        return self._regex_patterns.get(pattern)

# Global cache instance
cache = Cache()
