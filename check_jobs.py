import sqlite3
import pandas as pd

conn = sqlite3.connect('labh_offset.db')
df = pd.read_sql("SELECT job_id, date, job_name, ream, sheet_per_ream, loose_sheets, total_sheets FROM jobs WHERE party_code='amdatu' AND paper_code='300gul'", conn)
print(df.to_string())
conn.close()
