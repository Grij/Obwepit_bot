import sqlite3
db = sqlite3.connect("data/users.db")
db.execute("DELETE FROM channels WHERE chat_id = '-1001339503523'")
db.commit()
print("Deleted dup")
