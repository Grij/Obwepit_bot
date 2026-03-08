import sqlite3
db = sqlite3.connect("data/users.db")
db.execute("UPDATE approvals SET chat_id = '@obwepit_dnipro' WHERE chat_id = '-1001352745030'")
db.commit()
print("Fixed historical approvals.")
