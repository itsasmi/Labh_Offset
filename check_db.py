import sqlite3
import json

conn = sqlite3.connect('labh_offset.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM inward ORDER BY id DESC LIMIT 5")
rows = cursor.fetchall()

print("INWARD ENTRIES:")
for r in rows:
    print(dict(r))

cursor.execute("SELECT * FROM jobs ORDER BY job_id DESC LIMIT 5")
job_rows = cursor.fetchall()
print("\nJOBS:")
for r in job_rows:
    print(dict(r))

conn.close()
