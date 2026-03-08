import aiosqlite
import os
import shutil
from datetime import datetime
from src.utils.logger import logger

DB_PATH = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/db.sqlite3").replace("sqlite+aiosqlite:///", "")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    async def init(self):
        logger.info("Initializing database...")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('PRAGMA journal_mode=WAL;')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_bot BOOLEAN,
                    join_date TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    warn_count INTEGER DEFAULT 0,
                    mute_until TIMESTAMP,
                    is_banned BOOLEAN DEFAULT 0,
                    ban_reason TEXT,
                    last_activity TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message_id INTEGER,
                    text TEXT,
                    timestamp TIMESTAMP,
                    is_deleted BOOLEAN DEFAULT 0
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    incident_type TEXT,
                    severity TEXT,
                    action_taken TEXT,
                    reason TEXT,
                    timestamp TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE,
                    chat_id INTEGER,
                    deleted_count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, chat_id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS global_blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT UNIQUE,
                    added_by INTEGER,
                    added_at TIMESTAMP
                )
            ''')
            
            await db.commit()
        logger.info("Database initialized successfully.")

    async def increment_daily_stats(self, chat_id: int):
        today = datetime.now().date().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO daily_stats (date, chat_id, deleted_count)
                VALUES (?, ?, 1)
                ON CONFLICT(date, chat_id) DO UPDATE SET
                    deleted_count = deleted_count + 1
            ''', (today, chat_id))
            await db.commit()

    async def add_blacklist_word(self, word: str, added_by: int):
        word = word.lower().strip()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    INSERT INTO global_blacklist (word, added_by, added_at)
                    VALUES (?, ?, ?)
                ''', (word, added_by, datetime.now()))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_blacklist_word(self, word: str):
        word = word.lower().strip()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('DELETE FROM global_blacklist WHERE word = ?', (word,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_all_blacklist_words(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT word FROM global_blacklist')
            rows = await cursor.fetchall()
            return [row['word'] for row in rows]

    async def add_or_update_user(self, user_data: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO users (user_id, username, first_name, is_bot, join_date, last_activity)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_activity=excluded.last_activity,
                    message_count = message_count + 1
            ''', (
                user_data['user_id'], user_data.get('username'), user_data.get('first_name'),
                user_data.get('is_bot', False), datetime.now(), datetime.now()
            ))
            await db.commit()

    async def log_incident(self, user_id: int, incident_type: str, severity: str, action_taken: str, reason: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO incidents (user_id, incident_type, severity, action_taken, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, incident_type, severity, action_taken, reason, datetime.now()))
            
            if 'warn' in action_taken:
                await db.execute('UPDATE users SET warn_count = warn_count + 1 WHERE user_id = ?', (user_id,))
            if 'ban' in action_taken:
                await db.execute('UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?', (reason, user_id))
                
            await db.commit()
            
    async def log_message(self, user_id: int, message_id: int, text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO user_messages (user_id, message_id, text, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user_id, message_id, text, datetime.now()))
            await db.commit()

    async def get_user_stats(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cursor.fetchone()
            
            if not user:
                return None
            
            cursor = await db.execute('SELECT COUNT(*) as incident_count FROM incidents WHERE user_id = ?', (user_id,))
            incidents = await cursor.fetchone()
            
            user_dict = dict(user)
            user_dict['incident_count'] = incidents['incident_count']
            return user_dict
            
    def backup(self):
        backup_path = f"{self.db_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
        logger.info(f"Creating database backup at {backup_path}")
        try:
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False

db = Database()
