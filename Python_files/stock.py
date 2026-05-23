from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional, List
from database import get_db
from models import Inward, Outward, Party, PaperMaster
from schemas import StockBalance, StockCheckResponse, LedgerEntry, DashboardStats

router = APIRouter(prefix="/api", tags=["Stock"])

@router.get("/stock/check", response_model=StockCheckResponse)
def check_stock(
    paper_code:  str             = Query(...),
    paper_size:  str             = Query(...),
    stock_type:  str             = Query(...),
    qty:         int             = Query(...),
    party_code:  Optional[str]   = Query(None),
    db: Session = Depends(get_db)
):
    """
    Live stock check called during job entry.
    Returns available balance and whether it covers the requested qty.
    """
    # Sum all inward for this paper+size+type
    inward_q = db.query(func.coalesce(func.sum(Inward.total_sheets), 0)).filter(
        Inward.paper_code == paper_code,
        Inward.paper_size == paper_size,
        Inward.stock_type == stock_type,
    )
    if stock_type == "party" and party_code:
        inward_q = inward_q.filter(Inward.party_code == party_code.lower())
    total_in = inward_q.scalar() or 0

    # Sum all outward for this paper+size+type
    outward_q = db.query(func.coalesce(func.sum(Outward.used_sheets), 0)).filter(
        Outward.paper_code == paper_code,
        Outward.paper_size == paper_size,
        Outward.stock_type == stock_type,
    )
    if stock_type == "party" and party_code:
        outward_q = outward_q.filter(Outward.party_code == party_code.lower())
    total_out = outward_q.scalar() or 0

    balance    = total_in - total_out
    available  = balance > 0
    sufficient = balance >= qty

    if balance <= 0:
        msg = f"No stock available for this paper + size combination"
    elif not sufficient:
        msg = f"Only {balance:,} sheets available — job needs {qty:,} (shortfall of {qty - balance:,} sheets)"
    else:
        msg = f"{balance:,} sheets available — sufficient for this job ✓"

    return StockCheckResponse(
        available  = available,
        balance    = balance,
        sufficient = sufficient,
        message    = msg,
    )

@router.get("/stock", response_model=List[StockBalance])
def get_stock_register(
    stock_type:  Optional[str] = Query(None),
    party_code:  Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Full stock register — computed live from inward and outward tables."""
    sql = text("""
        SELECT
            i.party_code,
            p.party_name,
            i.paper_code,
            pm.description  AS paper_desc,
            i.paper_size,
            i.stock_type,
            SUM(i.total_sheets)                          AS total_inward,
            COALESCE(SUM(o.used_sheets), 0)              AS total_outward,
            SUM(i.total_sheets) - COALESCE(SUM(o.used_sheets), 0) AS balance
        FROM inward i
        LEFT JOIN parties p ON i.party_code = p.party_code
        LEFT JOIN paper_master pm ON i.paper_code = pm.paper_code
        LEFT JOIN outward o
            ON  i.party_code  = o.party_code
            AND i.paper_code  = o.paper_code
            AND i.paper_size  = o.paper_size
            AND i.stock_type  = o.stock_type
        WHERE (:stock_type IS NULL OR i.stock_type = :stock_type)
          AND (:party_code IS NULL OR i.party_code = :party_code)
        GROUP BY i.party_code, i.paper_code, i.paper_size, i.stock_type
        ORDER BY balance ASC
    """)
    rows = db.execute(sql, {"stock_type": stock_type, "party_code": party_code}).fetchall()
    result = []
    for r in rows:
        result.append(StockBalance(
            party_code    = r.party_code,
            party_name    = r.party_name,
            paper_code    = r.paper_code,
            paper_desc    = r.paper_desc,
            paper_size    = r.paper_size,
            stock_type    = r.stock_type,
            total_inward  = r.total_inward or 0,
            total_outward = r.total_outward or 0,
            balance       = r.balance or 0,
            is_negative   = (r.balance or 0) < 0,
        ))
    return result

@router.get("/stock/party/{party_code}", response_model=List[LedgerEntry])
def get_party_ledger(party_code: str, db: Session = Depends(get_db)):
    """
    Full chronological transaction history for one party.
    Equivalent to the 'atul enterprise' sheet in your Excel.
    Returns inward + outward entries merged and sorted by date,
    with a running balance after each row.
    """
    entries = []

    inwards = db.query(Inward).filter(
        Inward.party_code == party_code.lower(),
        Inward.stock_type == "party"
    ).order_by(Inward.date).all()

    outwards = db.query(Outward).filter(
        Outward.party_code == party_code.lower(),
        Outward.stock_type == "party"
    ).order_by(Outward.date).all()

    # Merge and sort by date
    all_txns = []
    for i in inwards:
        all_txns.append(("inward", i.date, None, None, i.supplier_name, i.paper_code, i.paper_desc, i.paper_size, i.total_sheets))
    for o in outwards:
        all_txns.append(("outward", o.date, o.job_id, o.job_name, None, o.paper_code, o.paper_name, o.paper_size, o.used_sheets))
    all_txns.sort(key=lambda x: x[1])

    running = 0
    for txn in all_txns:
        typ, date, job_id, job_name, supplier, pcode, pdesc, psize, sheets = txn
        if typ == "inward":
            running += sheets
        else:
            running -= sheets
        entries.append(LedgerEntry(
            type            = typ,
            date            = date,
            job_id          = job_id,
            job_name        = job_name,
            supplier        = supplier,
            paper_code      = pcode,
            paper_desc      = pdesc,
            paper_size      = psize,
            sheets          = sheets,
            running_balance = running,
        ))
    return entries

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    from models import Job
    from datetime import date
    today = date.today().isoformat()
    today_jobs       = db.query(Job).filter(Job.date == today, Job.status != "deleted").count()
    pending_jobs     = db.query(Job).filter(Job.status == "pending").count()
    in_progress_jobs = db.query(Job).filter(Job.status == "in_progress").count()

    # Count negative party stock balances
    sql = text("""
        SELECT COUNT(*) FROM (
            SELECT i.party_code, i.paper_code, i.paper_size,
                   SUM(i.total_sheets) - COALESCE(SUM(o.used_sheets),0) AS bal
            FROM inward i
            LEFT JOIN outward o ON i.party_code=o.party_code AND i.paper_code=o.paper_code
                AND i.paper_size=o.paper_size AND i.stock_type=o.stock_type
            WHERE i.stock_type='party'
            GROUP BY i.party_code, i.paper_code, i.paper_size
            HAVING bal < 0
        )
    """)
    low_party = db.execute(sql).scalar() or 0

    sql2 = text("""
        SELECT COUNT(*) FROM (
            SELECT i.paper_code, i.paper_size,
                   SUM(i.total_sheets) - COALESCE(SUM(o.used_sheets),0) AS bal
            FROM inward i
            LEFT JOIN outward o ON i.paper_code=o.paper_code AND i.paper_size=o.paper_size
                AND i.stock_type=o.stock_type
            WHERE i.stock_type='company'
            GROUP BY i.paper_code, i.paper_size
            HAVING bal < 500
        )
    """)
    low_company = db.execute(sql2).scalar() or 0

    return DashboardStats(
        today_jobs             = today_jobs,
        pending_jobs           = pending_jobs,
        in_progress_jobs       = in_progress_jobs,
        low_party_stock_count  = low_party,
        low_company_stock_count= low_company,
    )
