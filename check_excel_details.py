import pandas as pd

print("---- INWARD PAPER (EXCEL) ----")
df_in = pd.read_excel('Latest_data.xlsx', sheet_name='inward paper', header=1)
df_in.columns = [str(c).strip() for c in df_in.columns]
df_in_filtered = df_in[(df_in['CLIENT IDE'] == 'amdatu') & (df_in['PAPER CODE'] == '300gul')]
print(df_in_filtered[['CLIENT IDE', 'PAPER CODE', 'TOTAL SHEETS']].to_string())
print("Excel INWARD Sum:", df_in_filtered['TOTAL SHEETS'].sum())

print("\n---- OUTWARD PAPER (EXCEL) ----")
df_out = pd.read_excel('Latest_data.xlsx', sheet_name='outward paper', header=1)
df_out.columns = [str(c).strip() for c in df_out.columns]
df_out_filtered = df_out[(df_out['PARTY CODE'] == 'amdatu') & (df_out['PAPER CODE'] == '300gul')]
print(df_out_filtered[['PARTY CODE', 'PAPER CODE', 'USED SHEET']].to_string())
print("Excel OUTWARD Sum:", df_out_filtered['USED SHEET'].sum())
