import sqlite3
conn = sqlite3.connect('ibvap.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'correlation%'")
tables = cursor.fetchall()
for t in tables:
    print(t)
conn.close()