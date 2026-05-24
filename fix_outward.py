import sqlite3

def fix():
    conn = sqlite3.connect('labh_offset.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Update outward entries from jobs
    cursor.execute("""
        UPDATE outward
        SET
            job_name = COALESCE(NULLIF((SELECT job_name FROM jobs WHERE jobs.job_id = outward.job_id), ''), '[Untitled Job]'),
            party_code = COALESCE((SELECT party_code FROM jobs WHERE jobs.job_id = outward.job_id), outward.party_code),
            paper_code = COALESCE((SELECT paper_code FROM jobs WHERE jobs.job_id = outward.job_id), outward.paper_code),
            paper_size = COALESCE((SELECT paper_size FROM jobs WHERE jobs.job_id = outward.job_id), outward.paper_size),
            used_sheets = COALESCE((SELECT total_sheets FROM jobs WHERE jobs.job_id = outward.job_id), outward.used_sheets)
    """)
    
    # Fix party names
    cursor.execute("""
        UPDATE outward
        SET party_name = COALESCE((SELECT party_name FROM parties WHERE parties.party_code = outward.party_code), '[Unknown Party]')
    """)
    
    # Fix paper names
    cursor.execute("""
        UPDATE outward
        SET paper_name = COALESCE(
            (SELECT description FROM paper_master WHERE paper_master.paper_code = outward.paper_code),
            (SELECT gsm_desc FROM jobs WHERE jobs.job_id = outward.job_id),
            'Unknown Paper'
        )
    """)
    
    # Fix 'Unknown' job names that were already literal 'Unknown' in the db
    cursor.execute("""
        UPDATE outward
        SET job_name = '[Untitled Job]'
        WHERE job_name = 'Unknown' OR job_name IS NULL OR job_name = ''
    """)

    conn.commit()
    
    # Let's count how many have used_sheets = 0
    cursor.execute("SELECT count(*) as c FROM outward WHERE used_sheets = 0 OR used_sheets IS NULL")
    res = cursor.fetchone()
    print("0 sheets records:", res['c'])

    conn.close()

if __name__ == '__main__':
    fix()
