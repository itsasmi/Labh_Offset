import pandas as pd

df_entry = pd.read_excel('Latest_data.xlsx', sheet_name='Entry', header=0)
job_col_entry = "JOB NO." if "JOB NO." in df_entry.columns else "JOB NO"
df_entry = df_entry[pd.to_numeric(df_entry[job_col_entry], errors='coerce').notna()]
df_entry[job_col_entry] = df_entry[job_col_entry].astype(int)

df_entry['PARTY CODE'] = df_entry['PARTY CODE'].astype(str).str.lower().str.strip()
df_entry['PAPER CODE'] = df_entry['PAPER CODE'].astype(str).str.lower().str.strip()

entry_jobs = df_entry[(df_entry['PARTY CODE'] == 'amdatu') & (df_entry['PAPER CODE'] == '300gul')]
entry_job_ids = set(entry_jobs[job_col_entry])

df_outward = pd.read_excel('Latest_data.xlsx', sheet_name='outward paper', header=1)
df_outward = df_outward[pd.to_numeric(df_outward["JOB NO."], errors='coerce').notna()]
df_outward["JOB NO."] = df_outward["JOB NO."].astype(int)

df_outward['PARTY CODE'] = df_outward['PARTY CODE'].astype(str).str.lower().str.strip()
df_outward['PAPER CODE'] = df_outward['PAPER CODE'].astype(str).str.lower().str.strip()

outward_jobs = df_outward[(df_outward['PARTY CODE'] == 'amdatu') & (df_outward['PAPER CODE'] == '300gul')]
outward_job_ids = set(outward_jobs["JOB NO."])

print("Jobs in Entry sheet but NOT in outward paper sheet:")
missing_in_outward = entry_job_ids - outward_job_ids
for j in missing_in_outward:
    row = entry_jobs[entry_jobs[job_col_entry] == j].iloc[0]
    print(f"  Job {j}: {row['JOB NAME']} (Sheets: {row['Paper Sheet']})")

print(f"\nTotal Outward in Entry for amdatu 300gul: {entry_jobs['Paper Sheet'].sum()}")
print(f"Total Outward in outward paper sheet for amdatu 300gul: {outward_jobs['USED SHEET'].sum()}")
