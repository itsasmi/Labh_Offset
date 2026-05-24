import pandas as pd
import sqlite3

# Query Excel Entry Sheet
df_entry = pd.read_excel('Latest_data.xlsx', sheet_name='Entry', header=1)
# Clean columns
df_entry.columns = [str(c).strip() for c in df_entry.columns]
# Find amdatu and 300gul
if 'CLIENT CODE' in df_entry.columns:
    party_col = 'CLIENT CODE'
elif 'PARTY CODE' in df_entry.columns:
    party_col = 'PARTY CODE'
else:
    party_col = None

if 'PAPER CODE' in df_entry.columns:
    paper_col = 'PAPER CODE'
else:
    paper_col = None

if party_col and paper_col:
    df_amdatu = df_entry[(df_entry[party_col] == 'amdatu') & (df_entry[paper_col] == '300gul')]
    if 'TOTAL SHEET' in df_entry.columns:
        total_sheets = df_amdatu['TOTAL SHEET'].sum()
    elif 'TOTAL SHEETS' in df_entry.columns:
        total_sheets = df_amdatu['TOTAL SHEETS'].sum()
    else:
        total_sheets = "Missing TOTAL SHEETS column"
    print("Excel ENTRY Sheet Outward Sum for amdatu/300gul:", total_sheets)
else:
    print("Could not find party or paper code in Entry sheet.")

# Query DB Jobs Table
conn = sqlite3.connect('labh_offset.db')
cur = conn.cursor()
cur.execute("SELECT SUM(total_sheets) FROM jobs WHERE party_code='amdatu' AND paper_code='300gul'")
res = cur.fetchone()[0]
print("DB Jobs Table total_sheets for amdatu/300gul:", res)

cur.execute("SELECT SUM(used_sheets) FROM outward WHERE party_code='amdatu' AND paper_code='300gul'")
res = cur.fetchone()[0]
print("DB Outward Table used_sheets for amdatu/300gul:", res)
