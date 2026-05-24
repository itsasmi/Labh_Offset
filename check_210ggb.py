import sqlite3
conn = sqlite3.connect('labh_offset.db')
cur = conn.cursor()
cur.execute("SELECT SUM(total_sheets) FROM inward WHERE paper_code='210ggb' AND paper_size='23x36' AND stock_type='party'")
print('Inward:', cur.fetchone())
cur.execute("SELECT SUM(used_sheets) FROM outward WHERE paper_code='210ggb' AND paper_size='23x36' AND stock_type='party'")
print('Outward:', cur.fetchone())
