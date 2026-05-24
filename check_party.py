import sqlite3
conn = sqlite3.connect('labh_offset.db')
cur = conn.cursor()
cur.execute("SELECT party_code, job_id, status FROM jobs WHERE job_id=1024")
print('Job 1024 party:', cur.fetchone())
cur.execute("SELECT party_code, id, total_sheets FROM inward WHERE paper_code='210ggb' AND paper_size='23x36' AND stock_type='party'")
print('Inward party:', cur.fetchall())
