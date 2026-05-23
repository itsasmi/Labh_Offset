"""
migrate.py — Labh Offset Excel → SQLite Migration
===================================================
Run this ONCE to import all historical data from your Excel file into the
SQLite database.

HOW TO RUN (copy-paste into terminal):
    python migrate.py

Requirements:
    pip install pandas openpyxl

What this script does (in order):
    Step 1  → Creates the SQLite database file (labh_offset.db)
    Step 2  → Creates all tables
    Step 3  → Imports parties (clients)
    Step 4  → Imports paper master (paper types)
    Step 5  → Imports operators
    Step 6  → Imports all jobs (5978 rows)
    Step 7  → Imports lamination details
    Step 8  → Imports punching details
    Step 9  → Imports inward register (1953 rows)
    Step 10 → Imports outward register (3995 rows)
    Step 11 → Prints a final summary report

After running, you will have: labh_offset.db  (your complete database)
"""

import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
EXCEL_FILE = "Latest_data.xlsx"
DB_FILE    = "labh_offset.db"

# ── HELPERS ───────────────────────────────────────────────────────────────────

def clean(val, default=None):
    """Convert NaN / None / blank to None, else return stripped string."""
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except Exception:
        pass
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "nat") else default

def to_int(val, default=None):
    """Safely convert to int."""
    try:
        f = float(val)
        if pd.isna(f):
            return default
        return int(f)
    except Exception:
        return default

def to_float(val, default=None):
    """Safely convert to float."""
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except Exception:
        return default

def to_date(val, default=None):
    """Convert Excel date to ISO string YYYY-MM-DD."""
    if val is None:
        return default
    try:
        if pd.isna(val):
            return default
    except Exception:
        pass
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return default

def normalize_paper_source(val):
    """Normalize the messy paper source column to 'party' or 'company'."""
    if val is None:
        return "party"
    v = str(val).strip().lower()
    if v in ("labh", "l", "company", "comp"):
        return "company"
    return "party"  # default — party, Party, PARTY, PARY, s, CTCP all → party

def normalize_printing(val):
    """Normalize printing type."""
    if val is None:
        return "s/s"
    v = str(val).strip().lower()
    if "f+b" in v or "f+b" in v:
        return "f+b"
    if "f/b" in v:
        return "f/b"
    if "b/s" in v or "b/f" in v:
        return "b/s"
    if "f/s" in v:
        return "f/s"
    return v or "s/s"

def log(msg):
    print(f"  {msg}")

# ── CREATE DATABASE & TABLES ──────────────────────────────────────────────────

def create_tables(conn):
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS parties (
        party_code  TEXT PRIMARY KEY,
        party_name  TEXT NOT NULL,
        phone       TEXT,
        email       TEXT,
        address     TEXT,
        is_active   INTEGER NOT NULL DEFAULT 1,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS paper_master (
        paper_code  TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        gsm         INTEGER,
        category    TEXT,
        is_active   INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS operators (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        role        TEXT,
        is_active   INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS jobs (
        job_id          INTEGER PRIMARY KEY,
        date            TEXT NOT NULL,
        year            INTEGER,
        month           INTEGER,
        party_code      TEXT NOT NULL,
        party_name      TEXT NOT NULL,
        job_name        TEXT NOT NULL,
        paper_code      TEXT,
        paper_size      TEXT,
        gsm_desc        TEXT,
        ream            INTEGER,
        sheet_per_ream  INTEGER,
        loose_sheets    INTEGER,
        total_sheets    INTEGER,
        cut_size        TEXT,
        qty             INTEGER,
        cut_part        INTEGER,
        printing        TEXT,
        pulling         TEXT,
        set_no          INTEGER DEFAULT 1,
        plate_size      TEXT,
        plate_process   TEXT,
        operator_name   TEXT,
        pulling_charge  TEXT,
        bill_no         TEXT,
        ctcp_bill_no    TEXT,
        job_remark      TEXT,
        paper_source    TEXT NOT NULL DEFAULT 'party',
        status          TEXT NOT NULL DEFAULT 'done',
        is_waiting_for_paper INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS lam_jobs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id          INTEGER NOT NULL REFERENCES jobs(job_id),
        process         TEXT,
        size            TEXT,
        agency_name     TEXT,
        operator_name   TEXT,
        side            TEXT,
        pulling         INTEGER,
        op_amount       REAL,
        op_pay          REAL
    );

    CREATE TABLE IF NOT EXISTS punch_jobs (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id  INTEGER NOT NULL REFERENCES jobs(job_id),
        dye     TEXT,
        size    TEXT,
        gsm     TEXT,
        qty     INTEGER,
        agency  TEXT,
        pay     REAL
    );

    CREATE TABLE IF NOT EXISTS inward (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ch_no           INTEGER,
        sr_no           INTEGER,
        date            TEXT NOT NULL,
        dch_no          TEXT,
        supplier_name   TEXT,
        paper_code      TEXT,
        paper_desc      TEXT,
        paper_size      TEXT,
        ream            INTEGER,
        sheet_per_ream  INTEGER,
        loose_sheets    INTEGER,
        total_sheets    INTEGER NOT NULL,
        party_code      TEXT,
        stock_type      TEXT NOT NULL DEFAULT 'party',
        notes           TEXT,
        status          TEXT NOT NULL DEFAULT 'received',
        created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS outward (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id      INTEGER NOT NULL UNIQUE REFERENCES jobs(job_id),
        date        TEXT NOT NULL,
        sr_no       INTEGER,
        party_code  TEXT NOT NULL,
        party_name  TEXT NOT NULL,
        job_name    TEXT NOT NULL,
        paper_code  TEXT,
        paper_name  TEXT,
        paper_size  TEXT,
        used_sheets INTEGER NOT NULL,
        stock_type  TEXT NOT NULL DEFAULT 'party'
    );

    CREATE TABLE IF NOT EXISTS config (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    INSERT OR IGNORE INTO config (key, value) VALUES
        ('shop_name',           'Labh Offset'),
        ('low_stock_threshold', '500'),
        ('pin_hash',            ''),
        ('migrated_at',         datetime('now'));
    """)
    conn.commit()
    log("All tables created.")

# ── STEP 3: PARTIES ───────────────────────────────────────────────────────────

def import_parties(conn, df_entry):
    cur = conn.cursor()
    cur.execute("DELETE FROM parties")

    # Collect from Entry sheet
    seen = {}
    for _, row in df_entry.iterrows():
        code = clean(row.get("PARTY CODE"))
        name = clean(row.get("PARTY NAME"))
        if code and name:
            code = code.strip().lower()
            if code not in seen:
                seen[code] = name

    # Also collect from Paper Stock client list
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        df_ps = pd.read_excel(xl, sheet_name="Paper Stock", header=None)
        for _, row in df_ps.iterrows():
            code = clean(row.iloc[0])
            name = clean(row.iloc[1])
            if code and name and len(code) > 2 and code.lower() not in ("client code", "nan"):
                code = code.strip().lower()
                if code not in seen:
                    seen[code] = name
    except Exception as e:
        log(f"  Note: Could not read Paper Stock for extra parties: {e}")

    rows = [(code, name) for code, name in seen.items()]
    cur.executemany(
        "INSERT OR IGNORE INTO parties (party_code, party_name) VALUES (?, ?)",
        rows
    )
    conn.commit()
    log(f"Parties imported: {len(rows)}")

# ── STEP 4: PAPER MASTER ──────────────────────────────────────────────────────

def import_paper_master(conn, df_entry):
    cur = conn.cursor()
    cur.execute("DELETE FROM paper_master")

    seen = {}
    for _, row in df_entry.iterrows():
        code = clean(row.get("PAPER CODE"))
        desc = clean(row.get("GSM"))
        if code and desc:
            code = code.strip().lower()
            if code not in seen:
                # Extract numeric GSM from description e.g. "300 gsm art card" → 300
                gsm = None
                m = re.match(r"(\d+)", desc)
                if m:
                    gsm = int(m.group(1))
                seen[code] = (desc, gsm)

    # Also from Paper Stock paper codes list
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        df_ps = pd.read_excel(xl, sheet_name="Paper Stock", header=None)
        for _, row in df_ps.iterrows():
            code = clean(row.iloc[3])
            desc = clean(row.iloc[4])
            if code and desc and len(code) > 2 and str(code).lower() not in ("paper code code", "item code", "nan"):
                code = code.strip().lower()
                if code not in seen:
                    gsm = None
                    m = re.match(r"(\d+)", str(desc))
                    if m:
                        gsm = int(m.group(1))
                    seen[code] = (str(desc), gsm)
    except Exception as e:
        log(f"  Note: Could not read Paper Stock for extra paper codes: {e}")

    # NEW: Also collect from Inward Register sheet to ensure codes exist
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        df_iw = pd.read_excel(xl, sheet_name="inward paper", header=1)
        for _, row in df_iw.iterrows():
            code = clean(row.get("PAPER CODE"))
            desc = clean(row.get("PAPER SUPPLIER NAME2"))
            if code:
                code = code.strip().lower()
                if code not in seen:
                    gsm = None
                    if desc:
                        m = re.match(r"(\d+)", str(desc))
                        if m: gsm = int(m.group(1))
                    seen[code] = (str(desc) if desc else code, gsm)
    except Exception as e:
        log(f"  Note: Could not read Inward Register for extra paper codes: {e}")

    rows = [(code, desc, gsm) for code, (desc, gsm) in seen.items()]
    cur.executemany(
        "INSERT OR IGNORE INTO paper_master (paper_code, description, gsm) VALUES (?, ?, ?)",
        rows
    )
    conn.commit()
    log(f"Paper codes imported: {len(rows)}")

# ── STEP 5: OPERATORS ─────────────────────────────────────────────────────────

def import_operators(conn, df_entry):
    cur = conn.cursor()
    cur.execute("DELETE FROM operators")

    seen = set()
    for col in ["Process Name", "OPERATOR NAME"]:
        if col in df_entry.columns:
            for val in df_entry[col].dropna().unique():
                name = clean(val)
                if name and len(name) > 1:
                    seen.add(name)

    rows = [(name,) for name in sorted(seen)]
    cur.executemany("INSERT OR IGNORE INTO operators (name) VALUES (?)", rows)
    conn.commit()
    log(f"Operators imported: {len(rows)}")

# ── STEP 6: JOBS ──────────────────────────────────────────────────────────────

def import_jobs(conn, df_entry):
    cur = conn.cursor()
    cur.execute("DELETE FROM outward")
    cur.execute("DELETE FROM lam_jobs")
    cur.execute("DELETE FROM punch_jobs")
    cur.execute("DELETE FROM jobs")

    # Filter to only rows with a valid numeric JOB NO
    job_col = "JOB NO." if "JOB NO." in df_entry.columns else "JOB NO"
    df = df_entry[pd.to_numeric(df_entry[job_col], errors="coerce").notna()].copy()
    df[job_col] = pd.to_numeric(df[job_col], errors="coerce").astype(int)
    df = df.drop_duplicates(subset=[job_col])
    df = df.sort_values(job_col)

    rows = []
    for _, r in df.iterrows():
        job_id      = to_int(r.get(job_col))
        date_val    = to_date(r.get("DATE"), "2025-04-01")
        year_val    = to_int(r.get("YEAR"))
        month_val   = to_int(r.get("MO.NT"))
        party_code  = clean(r.get("PARTY CODE"), "unknown")
        party_name  = clean(r.get("PARTY NAME"), "Unknown")
        job_name    = clean(r.get("JOB NAME"), "")
        paper_code  = clean(r.get("PAPER CODE") or r.get("Paper Code"))
        paper_size  = clean(r.get("Paper Size") or r.get("PAPER SIZE"))
        gsm_desc    = clean(r.get("GSM") or r.get("PAPER GSM"))
        ream        = to_int(r.get("ream") or r.get("REAM"))
        spr         = to_int(r.get("par ream") or r.get("SHEET PER REAM"))
        loose       = to_int(r.get("loos") or r.get("LOOSE"))
        total       = to_int(r.get("Paper Sheet") or r.get("TOTAL SHEET"))
        cut_size    = clean(r.get("Size") or r.get("CUT SIZE"))
        qty         = to_int(r.get("Cutting Use") or r.get("QTY"))
        cut_part    = to_int(r.get("Cut Part"))
        printing    = normalize_printing(r.get("paper") or r.get("PRINTING"))  # the printing col is called 'paper' in the sheet
        pulling     = clean(r.get("Pulling") or r.get("PULLING"))
        set_no      = to_int(r.get("Set") or r.get("SET"), 1)
        plate_size  = clean(r.get("plate size") or r.get("Plate size"))
        plate_proc  = clean(r.get("Plate Process") or r.get("Plate Process :"))
        operator    = clean(r.get("Process Name") or r.get("OPERATOR NAME"))
        pull_chg    = clean(r.get("Pulling Charge"))
        bill_no     = clean(r.get("BILL NO.") or r.get("Bill no."))
        ctcp_bill   = clean(r.get("CTCP BILL NO."))
        remark      = clean(r.get("Job Remark") or r.get("REMARKS"))
        # paper_source: from 'Stock' column (party/labh)
        psource     = normalize_paper_source(r.get("Stock"))

        if not job_id:
            continue

        if party_code:
            party_code = party_code.strip().lower()

        rows.append((
            job_id, date_val, year_val, month_val,
            party_code, party_name, job_name,
            paper_code, paper_size, gsm_desc,
            ream, spr, loose, total,
            cut_size, qty, cut_part, printing,
            pulling, set_no, plate_size, plate_proc,
            operator, pull_chg, bill_no, ctcp_bill, remark,
            psource, "done"
        ))

    cur.executemany("""
        INSERT OR REPLACE INTO jobs (
            job_id, date, year, month,
            party_code, party_name, job_name,
            paper_code, paper_size, gsm_desc,
            ream, sheet_per_ream, loose_sheets, total_sheets,
            cut_size, qty, cut_part, printing,
            pulling, set_no, plate_size, plate_process,
            operator_name, pulling_charge, bill_no, ctcp_bill_no, job_remark,
            paper_source, status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    log(f"Jobs imported: {len(rows)}")
    return df  # return for use in lam/punch import

# ── STEP 7: LAMINATION JOBS ───────────────────────────────────────────────────

def import_lam_jobs(conn, df_entry):
    cur = conn.cursor()
    cur.execute("DELETE FROM lam_jobs")

    job_col = "JOB NO." if "JOB NO." in df_entry.columns else "JOB NO"
    df = df_entry[pd.to_numeric(df_entry[job_col], errors="coerce").notna()].copy()
    df[job_col] = pd.to_numeric(df[job_col], errors="coerce").astype(int)

    rows = []
    for _, r in df.iterrows():
        job_id  = to_int(r.get(job_col))
        process = clean(r.get("LAMINATION PROCESS"))
        if not job_id or not process:
            continue
        rows.append((
            job_id,
            process,
            clean(r.get("SIZE")),
            clean(r.get("AGENCY NAME")),
            clean(r.get("OPERATOR NAME")),
            clean(r.get("SIDE")),
            to_int(r.get("PULLING")),
            to_float(r.get("OP AMOUNT")),
            to_float(r.get("OP.PAY")),
        ))

    cur.executemany("""
        INSERT INTO lam_jobs
            (job_id, process, size, agency_name, operator_name, side, pulling, op_amount, op_pay)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    log(f"Lamination jobs imported: {len(rows)}")

# ── STEP 8: PUNCH JOBS ────────────────────────────────────────────────────────

def import_punch_jobs(conn, df_entry):
    cur = conn.cursor()
    cur.execute("DELETE FROM punch_jobs")

    job_col = "JOB NO." if "JOB NO." in df_entry.columns else "JOB NO"
    df = df_entry[pd.to_numeric(df_entry[job_col], errors="coerce").notna()].copy()
    df[job_col] = pd.to_numeric(df[job_col], errors="coerce").astype(int)

    rows = []
    for _, r in df.iterrows():
        job_id = to_int(r.get(job_col))
        dye    = clean(r.get("DYE"))
        agency = clean(r.get("AGENCY"))
        if not job_id or (not dye and not agency):
            continue
        rows.append((
            job_id,
            dye,
            clean(r.get("size")),
            clean(r.get("gsm")),
            to_int(r.get("qty")),
            agency,
            to_float(r.get("PAY")),
        ))

    cur.executemany("""
        INSERT INTO punch_jobs (job_id, dye, size, gsm, qty, agency, pay)
        VALUES (?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    log(f"Punch jobs imported: {len(rows)}")

# ── STEP 9: INWARD REGISTER ───────────────────────────────────────────────────

def import_inward(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM inward")

    xl = pd.ExcelFile(EXCEL_FILE)
    df = pd.read_excel(xl, sheet_name="inward paper", header=1)

    # Filter valid rows (SR. NO. must be numeric)
    df = df[pd.to_numeric(df["SR. NO."], errors="coerce").notna()].copy()

    rows = []
    for _, r in df.iterrows():
        # Get key identifiers
        party_code = clean(r.get("CLIENT IDE") or r.get("CLIENT_IDE"))
        paper_code = clean(r.get("PAPER CODE") or r.get("PAPER_CODE"))
        
        # Skip completely ghost rows (many exist in the excel)
        if not party_code and not paper_code:
            continue
            
        date_val = to_date(r.get("DATE"), "2025-04-01")
        
        # Determine total_sheets
        total_val = None
        # Try finding a column with "TOTAL" and "SHEET"
        for k, v in r.items():
            if "TOTAL" in str(k).upper() and "SHEET" in str(k).upper():
                total_val = to_int(v)
                break
        
        if not total_val:
            # fallback: compute
            ream  = to_int(r.get("REAM"), 0) or 0
            spr   = to_int(r.get("SHEET PER REAM") or r.get("SHEET_PER_REAM")) or 0
            loose = to_int(r.get("LOOSE"), 0) or 0
            total_val = (ream * spr) + loose
            
        if not total_val or total_val <= 0:
            continue

        if party_code:
            party_code = party_code.strip().lower()
            stock_type = "party"
        else:
            # If no client code, it's company-purchased stock
            stock_type = "company"

        paper_desc = clean(r.get("PAPER SUPPLIER NAME2") or r.get("PAPER_SUPPLIER_NAME2"))

        rows.append((
            to_int(r.get("CH NO ") or r.get("CH_NO")),
            to_int(r.get("SR. NO.") or r.get("SR__NO_")),
            date_val,
            clean(r.get("D.CH.NO.") or r.get("D_CH_NO_")),
            clean(r.get("PAPER SUPPLIER NAME") or r.get("PAPER_SUPPLIER_NAME")),
            paper_code.strip().lower() if paper_code else None,
            paper_desc,
            clean(r.get("SIZE")),
            to_int(r.get("REAM")),
            to_int(r.get("SHEET PER REAM") or r.get("SHEET_PER_REAM")),
            to_int(r.get("LOOSE")),
            total_val,
            party_code,
            stock_type,
        ))

    cur.executemany("""
        INSERT INTO inward
            (ch_no, sr_no, date, dch_no, supplier_name,
             paper_code, paper_desc, paper_size,
             ream, sheet_per_ream, loose_sheets, total_sheets,
             party_code, stock_type)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    log(f"Inward entries imported: {len(rows)} (Skipped {len(df) - len(rows)} ghost/invalid rows)")

# ── STEP 10: OUTWARD REGISTER ─────────────────────────────────────────────────

def import_outward(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM outward")

    xl = pd.ExcelFile(EXCEL_FILE)
    df = pd.read_excel(xl, sheet_name="outward paper", header=1)
    df = df[pd.to_numeric(df["JOB NO."], errors="coerce").notna()].copy()
    df["JOB NO."] = pd.to_numeric(df["JOB NO."], errors="coerce").astype(int)
    df = df.drop_duplicates(subset=["JOB NO."])  # one outward per job

    # Get valid job_ids from DB
    valid_jobs = set(r[0] for r in cur.execute("SELECT job_id FROM jobs").fetchall())

    rows = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        job_id = to_int(r.get("JOB NO."))
        if not job_id or job_id not in valid_jobs:
            continue

        party_code = clean(r.get("PARTY CODE"), "unknown")
        if party_code:
            party_code = party_code.strip().lower()

        used = to_int(r.get("USED SHEET")) or 0

        rows.append((
            job_id,
            to_date(r.get("DATE"), "2025-04-01"),
            i,
            party_code,
            clean(r.get("PARTY NAME"), "Unknown"),
            clean(r.get("JOB NAME"), ""),
            clean(r.get("PAPER CODE")),
            clean(r.get("PAPER NAME")),
            clean(r.get("PAPER SIZE")),
            used,
            "party",
        ))

    cur.executemany("""
        INSERT OR IGNORE INTO outward
            (job_id, date, sr_no, party_code, party_name, job_name,
             paper_code, paper_name, paper_size, used_sheets, stock_type)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    log(f"Outward entries imported: {len(rows)}")

# ── STEP 11: SUMMARY REPORT ───────────────────────────────────────────────────

def print_summary(conn):
    cur = conn.cursor()
    tables = ["parties", "paper_master", "operators", "jobs",
              "lam_jobs", "punch_jobs", "inward", "outward"]
    print()
    print("=" * 45)
    print("  MIGRATION COMPLETE — Summary")
    print("=" * 45)
    for t in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:<20} {count:>6} rows")
    print("=" * 45)

    # Stock snapshot
    print()
    print("  Top 5 party stock balances:")
    rows = cur.execute("""
        SELECT i.party_code,
               SUM(i.total_sheets)                         AS inward,
               COALESCE(SUM(o.used_sheets), 0)             AS outward,
               SUM(i.total_sheets) - COALESCE(SUM(o.used_sheets), 0) AS balance
        FROM inward i
        LEFT JOIN outward o
          ON i.party_code = o.party_code
         AND i.paper_code = o.paper_code
         AND i.stock_type = o.stock_type
        WHERE i.stock_type = 'party'
        GROUP BY i.party_code
        ORDER BY ABS(balance) DESC
        LIMIT 5
    """).fetchall()
    for r in rows:
        code = r[0] or "(no party)"
        bal_str = str(r[3])
        flag = " ⚠ NEGATIVE" if r[3] < 0 else ""
        print(f"  {code:<20} balance: {bal_str:>8}{flag}")

    db_size = os.path.getsize(DB_FILE) / 1024
    print()
    print(f"  Database file : {DB_FILE}")
    print(f"  Database size : {db_size:.1f} KB")
    print()

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 45)
    print("  Labh Offset — Migration Script")
    print("=" * 45)

    # Check Excel file exists
    if not os.path.exists(EXCEL_FILE):
        print(f"\n  ERROR: Excel file not found: {EXCEL_FILE}")
        print(f"  Make sure this script is in the SAME FOLDER as the Excel file.")
        print(f"  Then run: python migrate.py")
        return

    print(f"\n  Reading Excel file: {EXCEL_FILE}")

    # Load Entry sheet once — used by multiple steps
    xl = pd.ExcelFile(EXCEL_FILE)
    df_entry = pd.read_excel(xl, sheet_name="Entry", header=0)

    # Connect to SQLite
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    print()
    print("  Step 1 & 2 — Creating database and tables...")
    create_tables(conn)

    print("  Step 3 — Importing parties (clients)...")
    import_parties(conn, df_entry)

    print("  Step 4 — Importing paper master (paper types)...")
    import_paper_master(conn, df_entry)

    print("  Step 5 — Importing operators...")
    import_operators(conn, df_entry)

    print("  Step 6 — Importing jobs (Entry sheet)...")
    import_jobs(conn, df_entry)

    print("  Step 7 — Importing lamination details...")
    import_lam_jobs(conn, df_entry)

    print("  Step 8 — Importing punching details...")
    import_punch_jobs(conn, df_entry)

    print("  Step 9 — Importing inward register...")
    import_inward(conn)

    print("  Step 10 — Importing outward register...")
    import_outward(conn)

    print()
    print("  Step 11 — Generating summary report...")
    print_summary(conn)

    conn.close()

if __name__ == "__main__":
    main()
