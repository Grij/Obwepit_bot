import asyncio
import aiosqlite

DB_NAME = "data/users.db"

async def update_channels():
    async with aiosqlite.connect(DB_NAME) as db:
        # Add type column if it doesn't exist
        try:
            await db.execute("ALTER TABLE channels ADD COLUMN type TEXT DEFAULT 'канал'")
        except Exception:
            pass # Already exists

        # Clear existing channels
        await db.execute("DELETE FROM channels")

        new_channels = [
            ("Общепіт Дніпро", "@obwepit_dnipro", "чат"),
            ("Харків Вакансії", "@obwepit", "канал"),
            ("Общепіт Київ", "@obwepit_kyiv", "чат"),
            ("Barista Family Харків", "@barista_family_kh", "чат"),
            ("Restofamily Харків", "@restofamily_kh", "чат"),
            ("Общепіт Харків", "@obwepit_kh", "чат"),
            ("Black List Dnipro", "@BlackList_Dnipro", "канал"),
            ("Black List Kyiv", "@BlackList_Obwepit_Kyiv", "канал"),
            ("Black List Харків", "@BlackListObwepit", "канал"),
        ]

        for title, chat_id, ctype in new_channels:
            link = f"https://t.me/{chat_id.replace('@', '')}"
            await db.execute(
                "INSERT INTO channels (chat_id, title, link, is_active, type) VALUES (?, ?, ?, 1, ?)",
                (chat_id, title, link, ctype)
            )
        
        await db.commit()
    print("Channels updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_channels())
