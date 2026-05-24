import pandas as pd

df = pd.read_excel('Latest_data.xlsx', sheet_name='Entry', header=0)
job_col = "JOB NO." if "JOB NO." in df.columns else "JOB NO"
df = df[pd.to_numeric(df[job_col], errors='coerce').notna()]
df[job_col] = df[job_col].astype(int)

job_ids = [51, 58, 59, 173, 174, 175, 176, 357, 571, 575, 686, 731, 809]
res = df[df[job_col].isin(job_ids)][[job_col, 'PARTY CODE', 'PAPER CODE', 'Paper Sheet']]
print(res.to_string())
