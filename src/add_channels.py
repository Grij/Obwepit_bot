import sqlite3
db = sqlite3.connect("data/users.db")
db.execute("INSERT OR IGNORE INTO channels (chat_id, title, link) VALUES ('@obwepit_dnipro', 'Общепіт Дніпро', 'https://t.me/obwepit_dnipro'), ('@obwepit', 'Общепіт (Головний)', 'https://t.me/obwepit')")
db.commit()
print("Channels added successfully!")
