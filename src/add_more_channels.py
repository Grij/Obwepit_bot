import sqlite3
db = sqlite3.connect("data/users.db")
channels = [
    ('@obwepit_kyiv', 'Общепіт Київ', 'https://t.me/obwepit_kyiv'),
    ('@barista_family_kh', 'Barista Family Харків', 'https://t.me/barista_family_kh'),
    ('@restofamily_kh', 'Restofamily Харків', 'https://t.me/restofamily_kh'),
    ('@obwepit_kh', 'Общепіт Харків', 'https://t.me/obwepit_kh')
]
for chat_id, title, link in channels:
    db.execute("INSERT OR IGNORE INTO channels (chat_id, title, link) VALUES (?, ?, ?)", (chat_id, title, link))
db.commit()
print("Regional channels added successfully!")
