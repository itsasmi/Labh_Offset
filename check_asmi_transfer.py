import sqlite3
import pandas as pd

conn = sqlite3.connect('labh_offset.db')
query = """
SELECT id, date, supplier_name, paper_code, paper_desc, paper_size, total_sheets, created_at 
FROM inward 
WHERE stock_type = 'company' 
  AND supplier_name LIKE '%asmi%' 
ORDER BY created_at DESC 
LIMIT 5
"""
df = pd.read_sql_query(query, conn)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(df)
