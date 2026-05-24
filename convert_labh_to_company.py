import sqlite3

def run_conversion():
    conn = sqlite3.connect('labh_offset.db')
    cur = conn.cursor()
    
    # Party codes that represent the company
    company_codes = ("amdlab", "amdlag", "amdlabh")
    placeholders = ','.join(['?'] * len(company_codes))
    
    # 1. Update Inward
    cur.execute(f"UPDATE inward SET stock_type = 'company' WHERE party_code IN ({placeholders})", company_codes)
    inward_updated = cur.rowcount
    
    # 2. Update Outward
    cur.execute(f"UPDATE outward SET stock_type = 'company' WHERE party_code IN ({placeholders})", company_codes)
    outward_updated = cur.rowcount
    
    # 3. Update Jobs paper_source
    cur.execute(f"UPDATE jobs SET paper_source = 'company' WHERE party_code IN ({placeholders})", company_codes)
    jobs_updated = cur.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Conversion complete!")
    print(f"- Inward records updated: {inward_updated}")
    print(f"- Outward records updated: {outward_updated}")
    print(f"- Jobs updated: {jobs_updated}")

if __name__ == "__main__":
    run_conversion()
