import sqlite3
conn = sqlite3.connect('ibvap.db')
cursor = conn.cursor()
cursor.execute('SELECT sql FROM sqlite_master WHERE type="index" AND tbl_name="evidence_verifications"')
rows = cursor.fetchall()
for r in rows:
    print(r[0])