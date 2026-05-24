import sqlite3
import pandas as pd
conn = sqlite3.connect('labh_offset.db')
print("--- OUTWARDS WITH STOCK_TYPE='company' ---")
outwards = pd.read_sql_query("SELECT job_id, party_code, job_name, paper_code, paper_size, used_sheets, stock_type FROM outward WHERE stock_type='company'", conn)
print(outwards)
print("--- JOBS WITH PAPER_SOURCE='company' ---")
jobs = pd.read_sql_query("SELECT job_id, party_code, job_name, paper_code, paper_size, total_sheets, paper_source FROM jobs WHERE paper_source='company'", conn)
print(jobs)
