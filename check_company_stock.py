import sqlite3
import pandas as pd

conn = sqlite3.connect('labh_offset.db')
df = pd.read_sql_query("SELECT * FROM inward WHERE stock_type = 'company'", conn)
print(f"Total company records: {len(df)}")
print(df.head())
