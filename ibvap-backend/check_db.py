import sqlite3
conn = sqlite3.connect('ibvap.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
rows = cursor.fetchall()
for r in rows:
    print(r[0])