from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional, List
from database import get_db
from models import Inward, Outward, Party, PaperMaster
from schemas import StockBalance, StockCheckResponse, LedgerEntry, DashboardStats, InwardOut

router = APIRouter(prefix="/api", tags=["Stock"])


@router.get("/stock/available")
def get_available_stock(
    stock_type: str             = Query(...),
    party_code: Optional[str]   = Query(None),
    db: Session = Depends(get_db)
):
    sql = text("""
        SELECT
            main.paper_code,
            COALESCE(pm.description, main.paper_desc, main.paper_code) AS paper_desc,
            main.paper_size,
            COALESCE(pm.gsm, 0) AS gsm,
            (
                SELECT COALESCE(SUM(total_sheets), 0)
                FROM inward i2
                WHERE (i2.party_code = main.party_code OR (i2.party_code IS NULL AND main.party_code IS NULL))
                  AND i2.paper_code = main.paper_code
                  AND i2.paper_size = main.paper_size
                  AND i2.stock_type = main.stock_type
                  AND i2.status = 'received'
            ) AS total_in,
            (
                SELECT COALESCE(SUM(o2.used_sheets), 0)
                FROM outward o2
                WHERE o2.paper_code = main.paper_code
                  AND o2.paper_size = main.paper_size
                  AND o2.stock_type = main.stock_type
                  AND (
                    (main.stock_type = 'party' AND o2.party_code = main.party_code)
                    OR 
                    (main.stock_type = 'company')
                  )
            ) AS total_out
        FROM (
            SELECT DISTINCT party_code, paper_code, paper_desc, paper_size, stock_type
            FROM inward
            WHERE status = 'received'
            UNION
            SELECT DISTINCT party_code, paper_code, paper_name, paper_size, stock_type
            FROM outward
        ) main
        LEFT JOIN paper_master pm ON main.paper_code = pm.paper_code
        WHERE main.stock_type = :stock_type
          AND (:party_code IS NULL OR main.party_code = :party_code)
        GROUP BY main.paper_code, main.paper_size
        HAVING (total_in - total_out) > 0
        ORDER BY paper_desc, main.paper_size
    """)
    
    rows = db.execute(sql, {
        "stock_type": stock_type, 
        "party_code": party_code.lower() if party_code else None
    }).fetchall()

    result = []
    for r in rows:
        result.append({
            "paper_code": r.paper_code,
            "paper_desc": r.paper_desc,
            "paper_size": r.paper_size,
            "gsm":        r.gsm,
            "balance":    r.total_in - r.total_out,
        })
    return result

def get_stock_balance(db: Session, paper_code: str, paper_size: str, stock_type: str, party_code: Optional[str] = None) -> int:
    """Helper to get current sheet balance for any paper + size + type combo."""
    p_code = paper_code.lower() if paper_code else ""
    p_size = paper_size.lower().replace(" ", "") if paper_size else ""
    
    # Sum all inward
    inward_q = db.query(func.coalesce(func.sum(Inward.total_sheets), 0)).filter(
        func.lower(Inward.paper_code) == p_code,
        func.lower(func.replace(Inward.paper_size, ' ', '')) == p_size,
        Inward.stock_type == stock_type,
        Inward.status == "received"
    )
    if stock_type == "party" and party_code:
        inward_q = inward_q.filter(func.lower(Inward.party_code) == party_code.lower())
    total_in = inward_q.scalar() or 0

    # Sum all outward
    outward_q = db.query(func.coalesce(func.sum(Outward.used_sheets), 0)).filter(
        func.lower(Outward.paper_code) == p_code,
        func.lower(func.replace(Outward.paper_size, ' ', '')) == p_size,
        Outward.stock_type == stock_type,
    )
    if stock_type == "party" and party_code:
        outward_q = outward_q.filter(func.lower(Outward.party_code) == party_code.lower())
    total_out = outward_q.scalar() or 0

    return total_in - total_out


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
    balance = get_stock_balance(db, paper_code, paper_size, stock_type, party_code)
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
    paper_code:  Optional[str] = Query(None),
    available_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Full stock register — computed live from inward and outward tables."""
    sql = text("""
        SELECT
            main.party_code,
            COALESCE(p.party_name, 'COMPANY') AS party_name,
            main.paper_code,
            COALESCE(pm.description, main.paper_desc, main.paper_code) AS paper_desc,
            main.paper_size,
            main.stock_type,
            (
                SELECT COALESCE(SUM(total_sheets), 0)
                FROM inward i2
                WHERE (i2.party_code = main.party_code OR (i2.party_code IS NULL AND main.party_code IS NULL))
                  AND i2.paper_code = main.paper_code
                  AND i2.paper_size = main.paper_size
                  AND i2.stock_type = main.stock_type
                  AND i2.status = 'received'
            ) AS total_inward,
            (
                SELECT COALESCE(SUM(total_sheets), 0)
                FROM inward i3
                WHERE (i3.party_code = main.party_code OR (i3.party_code IS NULL AND main.party_code IS NULL))
                  AND i3.paper_code = main.paper_code
                  AND i3.paper_size = main.paper_size
                  AND i3.stock_type = main.stock_type
                  AND i3.status = 'pending'
            ) AS pending_inward,
            (
                SELECT COALESCE(SUM(o2.used_sheets), 0)
                FROM outward o2
                WHERE o2.paper_code = main.paper_code
                  AND o2.paper_size = main.paper_size
                  AND o2.stock_type = main.stock_type
                  AND (
                    (main.stock_type = 'party' AND o2.party_code = main.party_code)
                    OR 
                    (main.stock_type = 'company')
                  )
            ) AS total_outward
        FROM (
            SELECT DISTINCT party_code, paper_code, paper_desc, paper_size, stock_type
            FROM inward
            UNION
            SELECT DISTINCT party_code, paper_code, paper_name, paper_size, stock_type
            FROM outward
        ) main
        LEFT JOIN parties p ON main.party_code = p.party_code
        LEFT JOIN paper_master pm ON main.paper_code = pm.paper_code
        WHERE (:stock_type IS NULL OR main.stock_type = :stock_type)
          AND (:party_code IS NULL OR main.party_code = :party_code)
          AND (:paper_code IS NULL OR main.paper_code LIKE :paper_code)
        ORDER BY paper_desc ASC
    """)
    rows = db.execute(sql, {"stock_type": stock_type, "party_code": party_code, "paper_code": f"%{paper_code}%" if paper_code else None}).fetchall()
    result = []
    for r in rows:
        bal = r.total_inward - r.total_outward
        if available_only and bal <= 0:
            continue
        result.append(StockBalance(
            party_code    = r.party_code,
            party_name    = r.party_name,
            paper_code    = r.paper_code,
            paper_desc    = r.paper_desc,
            paper_size    = r.paper_size,
            stock_type    = r.stock_type,
            total_inward  = r.total_inward,
            total_outward = r.total_outward,
            pending_inward= r.pending_inward,
            balance       = bal,
            is_negative   = bal < 0,
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
        Inward.stock_type == "party",
        Inward.status == "received"
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

@router.patch("/inward/{inward_id}/status")
def update_inward_status(inward_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    """Mark a pending inward entry as 'received'."""
    item = db.query(Inward).filter(Inward.id == inward_id).first()
    if not item:
        return {"error": "Entry not found"}
    item.status = status
    db.commit()

    if status == "received":
        try:
            from routers.inward import auto_activate_pending_jobs
            auto_activate_pending_jobs(db, item)
        except Exception as e:
            import traceback
            print(f"Auto-activation check failed on status patch: {e}")
            traceback.print_exc()

    return {"message": f"Entry marked as {status}"}

@router.get("/stock/pending", response_model=List[InwardOut])
def get_pending_inward(db: Session = Depends(get_db)):
    """List all inward entries that haven't arrived yet."""
    return db.query(Inward).filter(Inward.status == "pending").order_by(Inward.date).all()

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
                   SUM(i.total_sheets) - COALESCE((
                       SELECT SUM(o.used_sheets) FROM outward o
                       WHERE o.party_code = i.party_code AND o.paper_code = i.paper_code
                         AND o.paper_size = i.paper_size AND o.stock_type = 'party'
                   ), 0) AS bal
            FROM inward i
            WHERE i.stock_type='party' AND i.status='received'
            GROUP BY i.party_code, i.paper_code, i.paper_size
            HAVING bal < 0
        )
    """)
    low_party = db.execute(sql).scalar() or 0

    sql2 = text("""
        SELECT COUNT(*) FROM (
            SELECT i.paper_code, i.paper_size,
                   SUM(i.total_sheets) - COALESCE((
                       SELECT SUM(o.used_sheets) FROM outward o
                       WHERE o.paper_code = i.paper_code AND o.paper_size = i.paper_size
                         AND o.stock_type = 'company'
                   ), 0) AS bal
            FROM inward i
            WHERE i.stock_type='company' AND i.status='received'
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
