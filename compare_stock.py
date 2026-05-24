import pandas as pd
import sqlite3

# Read Excel stock paper sheet
df_excel = pd.read_excel('Latest_data.xlsx', sheet_name='stock paper', header=1)
# Drop rows where 'PARTY CODE' is NaN
df_excel = df_excel.dropna(subset=['PARTY CODE'])

# Convert PARTY CODE to string just in case
df_excel['PARTY CODE'] = df_excel['PARTY CODE'].astype(str).str.strip()

excel_stock = {}
for index, row in df_excel.iterrows():
    party_code = row['PARTY CODE']
    # The Excel might not group by paper code or might just group by party. 
    # Let's see what columns it has. 
    # 'SR.NO.', 'PARTY CODE', 'PARTY NAME', 'PAPER CODE', 'PAPER NAME', 'SIZE', 'INWARD SHEET', 'OUTWARD SHEET', 'BALANCE'
    # Wait, earlier output showed PAPER CODE etc. 
    paper_code = str(row['PAPER CODE']).strip()
    inward = row['INWARD SHEET']
    outward = row['OUTWARD SHEET']
    balance = row['BALANCE']
    excel_stock[(party_code, paper_code)] = {
        'inward': inward,
        'outward': outward,
        'balance': balance
    }

# Read DB stock
conn = sqlite3.connect('labh_offset.db')
cur = conn.cursor()

# Get inward totals per party, paper
cur.execute('''
    SELECT party_code, paper_code, SUM(total_sheets) 
    FROM inward 
    WHERE stock_type = 'party' AND party_code IS NOT NULL
    GROUP BY party_code, paper_code
''')
db_inward = {}
for row in cur.fetchall():
    db_inward[(row[0], row[1])] = row[2]

# Get outward totals per party, paper
cur.execute('''
    SELECT party_code, paper_code, SUM(used_sheets) 
    FROM outward 
    WHERE stock_type = 'party' AND party_code IS NOT NULL
    GROUP BY party_code, paper_code
''')
db_outward = {}
for row in cur.fetchall():
    db_outward[(row[0], row[1])] = row[2]

print("Differences found:")
# Compare Excel to DB
for (party_code, paper_code), excel_data in excel_stock.items():
    db_in = db_inward.get((party_code, paper_code), 0)
    db_out = db_outward.get((party_code, paper_code), 0)
    db_bal = db_in - db_out
    
    if db_in != excel_data['inward'] or db_out != excel_data['outward'] or db_bal != excel_data['balance']:
        print(f"Mismatch for Party: {party_code}, Paper: {paper_code}")
        print(f"  Excel: Inward={excel_data['inward']}, Outward={excel_data['outward']}, Balance={excel_data['balance']}")
        print(f"  DB:    Inward={db_in}, Outward={db_out}, Balance={db_bal}")

# Also check if DB has records not in Excel?
for key in set(db_inward.keys()).union(db_outward.keys()):
    if key not in excel_stock:
        db_in = db_inward.get(key, 0)
        db_out = db_outward.get(key, 0)
        db_bal = db_in - db_out
        if db_bal != 0 or db_in != 0 or db_out != 0:
            print(f"In DB but not in Excel (or zero in Excel): Party {key[0]}, Paper {key[1]}: In={db_in}, Out={db_out}, Bal={db_bal}")

conn.close()
