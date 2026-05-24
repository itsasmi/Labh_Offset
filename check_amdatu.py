import sqlite3
conn = sqlite3.connect('labh_offset.db')
cur = conn.cursor()
cur.execute("SELECT SUM(total_sheets) FROM inward WHERE party_code='amdatu'")
print('Inward:', cur.fetchone()[0])
cur.execute("SELECT SUM(used_sheets) FROM outward WHERE party_code='amdatu'")
print('Outward:', cur.fetchone()[0])
conn.close()
