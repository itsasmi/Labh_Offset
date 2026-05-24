import sqlite3
conn = sqlite3.connect('labh_offset.db')
cur = conn.cursor()

print("Inward per paper for amdatu:")
cur.execute("SELECT paper_code, SUM(total_sheets) FROM inward WHERE party_code='amdatu' GROUP BY paper_code")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\nOutward per paper for amdatu:")
cur.execute("SELECT paper_code, SUM(used_sheets) FROM outward WHERE party_code='amdatu' GROUP BY paper_code")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")

conn.close()
