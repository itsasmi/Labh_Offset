import sqlite3
import pandas as pd

conn = sqlite3.connect('labh_offset.db')
df = pd.read_sql_query("SELECT party_code, party_name FROM parties WHERE party_name LIKE '%labh%'", conn)
print(df)
