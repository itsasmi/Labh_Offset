import sqlite3
import pprint
conn = sqlite3.connect('labh_offset.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
query = '''
SELECT * FROM inward LIMIT 10;
'''
c.execute(query)
rows = c.fetchall()
for r in rows:
    print(dict(r))
