"""
routers/jobs.py
===============
All routes related to jobs:

    GET    /api/jobs              → list jobs (with filters)
    POST   /api/jobs              → create new job (auto-creates outward)
    GET    /api/jobs/{id}         → get full job details
    PUT    /api/jobs/{id}         → update job
    PATCH  /api/jobs/{id}/status  → update job status only
    DELETE /api/jobs/{id}         → soft delete job
    GET    /api/jobs/{id}/card    → job card data as JSON (for UI rendering)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_, cast, String
from datetime import datetime, date, timedelta
from typing import Optional, List

from database import get_db
from models import Job, LamJob, PunchJob, Outward, Inward, Party, PaperMaster
from schemas import (
    JobCreate, JobUpdate, JobOut, JobListItem,
    JobCardData, MessageResponse, StatusUpdate,
    JobActivate, JobActivateResponse
)
from routers.stock import get_stock_balance

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_next_outward_sr(db: Session) -> int:
    """Get the next serial number for the outward register."""
    result = db.query(func.max(Outward.sr_no)).scalar()
    return (result or 0) + 1


def create_outward_for_job(db: Session, job: Job):
    """
    Auto-create an outward entry when a job is saved.
    This is the core business rule — operators never create outward manually.
    """
    # Get paper description for display
    paper_name = job.gsm_desc or ""
    if not paper_name and job.paper_code:
        pm = db.query(PaperMaster).filter(
            PaperMaster.paper_code == job.paper_code
        ).first()
        if pm:
            paper_name = pm.description

    outward = Outward(
        job_id      = job.job_id,
        date        = job.date,
        sr_no       = get_next_outward_sr(db),
        party_code  = job.party_code,
        party_name  = job.party_name,
        job_name    = job.job_name,
        paper_code  = job.paper_code,
        paper_name  = paper_name,
        paper_size  = job.paper_size,
        used_sheets = job.total_sheets or 0,
        stock_type  = job.paper_source,
    )
    db.add(outward)


def sync_outward_for_job(db: Session, job: Job):
    """
    When a job is updated, sync the outward entry to match.
    Called automatically on PUT /api/jobs/{id}
    """
    outward = db.query(Outward).filter(Outward.job_id == job.job_id).first()
    
    if getattr(job, 'is_waiting_for_paper', False):
        if outward:
            db.delete(outward)
        return

    if outward:
        outward.date        = job.date
        outward.party_code  = job.party_code
        outward.party_name  = job.party_name
        outward.job_name    = job.job_name
        outward.paper_code  = job.paper_code
        outward.paper_size  = job.paper_size
        outward.used_sheets = job.total_sheets or 0
        outward.stock_type  = job.paper_source
    else:
        # Outward missing (shouldn't happen, but create it)
        create_outward_for_job(db, job)


# ── GET /api/jobs ─────────────────────────────────────────────────────────────

@router.get("", response_model=List[JobListItem])
def list_jobs(
    time_filter:  Optional[str] = Query(None), # today, last_7, last_30, curr_month, prev_month, curr_year, prev_year
    party_code:   Optional[str] = Query(None),
    status:       Optional[str] = Query(None),
    date_from:    Optional[str] = Query(None),
    date_to:      Optional[str] = Query(None),
    global_query: Optional[str] = Query(None),
    paper_query:  Optional[str] = Query(None),
    operator:     Optional[str] = Query(None),
    has_lam:      Optional[bool] = Query(None),
    has_punch:    Optional[bool] = Query(None),
    plate_size:   Optional[str] = Query(None),
    limit:        int = Query(200),
    page:         int = Query(1),
    db: Session = Depends(get_db)
):
    """
    List jobs with advanced BI-style memory fragment filters.
    Returns compact JobListItem objects.
    """
    q = db.query(Job).options(
        joinedload(Job.lam_job), 
        joinedload(Job.punch_job),
        joinedload(Job.party)
    )

    # Time Filtering Logic
    if time_filter:
        today = date.today()
        if time_filter == "today":
            date_from = today.isoformat()
            date_to   = today.isoformat()
        elif time_filter == "last_7":
            date_from = (today - timedelta(days=7)).isoformat()
            date_to   = today.isoformat()
        elif time_filter == "last_30":
            date_from = (today - timedelta(days=30)).isoformat()
            date_to   = today.isoformat()
        elif time_filter == "curr_month":
            date_from = today.replace(day=1).isoformat()
            date_to   = today.isoformat()
        elif time_filter == "last_3_months":
            date_from = (today - timedelta(days=90)).isoformat()
            date_to   = today.isoformat()
        elif time_filter == "last_6_months":
            date_from = (today - timedelta(days=180)).isoformat()
            date_to   = today.isoformat()
        elif time_filter == "prev_month":
            last_day_prev = today.replace(day=1) - timedelta(days=1)
            date_from = last_day_prev.replace(day=1).isoformat()
            date_to   = last_day_prev.isoformat()
        elif time_filter == "curr_year":
            date_from = date(today.year, 1, 1).isoformat()
            date_to   = today.isoformat()
        elif time_filter == "prev_year":
            date_from = date(today.year - 1, 1, 1).isoformat()
            date_to   = date(today.year - 1, 12, 31).isoformat()
        elif time_filter == "custom":
            pass # Use date_from and date_to from arguments

    if date_from:
        q = q.filter(Job.date >= date_from)
    if date_to:
        q = q.filter(Job.date <= date_to)
        
    if party_code:
        pattern = f"%{party_code}%"
        q = q.filter(
            or_(
                Job.party_code.ilike(pattern),
                Job.party_name.ilike(pattern)
            )
        )
    if status:
        q = q.filter(Job.status == status)
    if operator:
        q = q.filter(Job.operator_name.ilike(f"%{operator}%"))
    if plate_size:
        q = q.filter(Job.plate_size == plate_size)
        
    if has_lam is True:
        q = q.filter(Job.lam_job.has())
    elif has_lam is False:
        q = q.filter(~Job.lam_job.has())
        
    if has_punch is True:
        q = q.filter(Job.punch_job.has())
    elif has_punch is False:
        q = q.filter(~Job.punch_job.has())

    if paper_query:
        pattern = f"%{paper_query}%"
        q = q.filter(
            or_(
                Job.paper_code.ilike(pattern),
                Job.gsm_desc.ilike(pattern),
                Job.paper_size.ilike(pattern)
            )
        )

    if global_query:
      pattern = f"%{global_query}%"
      q = q.filter(
          or_(
              cast(Job.job_id, String).ilike(pattern),
              Job.party_name.ilike(pattern),
              Job.party_code.ilike(pattern),
              Job.job_name.ilike(pattern),
              Job.bill_no.ilike(pattern),
              Job.ctcp_bill_no.ilike(pattern),
              Job.job_remark.ilike(pattern),
              Job.paper_source.ilike(pattern)
          )
      )
        
    jobs = q.order_by(desc(Job.date), desc(Job.job_id)) \
              .offset((page - 1) * limit) \
              .limit(limit) \
              .all()

    # Post-process to fix "Unknown" or missing names using the relationship
    for j in jobs:
        # If party name is Unknown/missing but relationship exists, sync it
        if (j.party_name == "Unknown" or not j.party_name) and j.party:
            j.party_name = j.party.party_name
        # If still unknown or anonymous code, clarify it
        elif (j.party_name == "Unknown" or not j.party_name):
            if j.party_code and j.party_code != "unknown":
                 j.party_name = f"Anonymous ({j.party_code})"
            else:
                 j.party_name = "[Unknown Party]"
        
        # Handle empty job names
        if not j.job_name or j.job_name.lower() == "unknown":
            j.job_name = "[Untitled Job]"

    return jobs


# ── POST /api/jobs ────────────────────────────────────────────────────────────

@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    """
    Create a new job.

    Business rules enforced here:
    1. year and month are extracted from date automatically
    2. Outward entry is created in the same transaction
    3. LamJob and PunchJob are created if provided
    """
    try:
        d = datetime.strptime(payload.date, "%Y-%m-%d")
        year, month = d.year, d.month
    except ValueError:
        raise HTTPException(400, "date must be in YYYY-MM-DD format")


    # Validate party exists
    party = db.query(Party).filter(
        Party.party_code == payload.party_code.lower()
    ).first()
    if not party:
        raise HTTPException(404, f"Party '{payload.party_code}' not found. Add it in Masters first.")

    # Check Stock Availability
    # Rule: If stock is insufficient, Job stays PENDING and NO Outward entry is created.
    # If stock is sufficient OR it's a 'company' job (assuming we buy it), we proceed.
    # Actually, even for 'company' jobs, if it's not in stock, it should be pending.
    
    balance = get_stock_balance(
        db, 
        payload.paper_code, 
        payload.paper_size, 
        payload.paper_source.value, 
        payload.party_code
    )
    
    can_start = (balance >= (payload.total_sheets or 0))
    is_waiting = not can_start
    
    # Build the job object
    job = Job(
        date           = payload.date,
        year           = year,
        month          = month,
        party_code     = payload.party_code.lower(),
        party_name     = payload.party_name,
        job_name       = payload.job_name,
        bill_no        = payload.bill_no,
        ctcp_bill_no   = payload.ctcp_bill_no,
        job_remark     = payload.job_remark,
        paper_code     = payload.paper_code.lower() if payload.paper_code else None,
        paper_size     = payload.paper_size.lower().replace(" ", "") if payload.paper_size else None,
        gsm_desc       = payload.gsm_desc,
        ream           = payload.ream,
        sheet_per_ream = payload.sheet_per_ream,
        loose_sheets   = payload.loose_sheets,
        total_sheets   = payload.total_sheets,
        cut_size       = payload.cut_size,
        qty            = payload.qty,
        cut_part       = payload.cut_part,
        printing       = payload.printing,
        pulling        = payload.pulling,
        set_no         = payload.set_no,
        plate_size     = payload.plate_size,
        plate_process  = payload.plate_process,
        operator_name  = payload.operator_name,
        pulling_charge = payload.pulling_charge,
        paper_source   = payload.paper_source.value,
        is_waiting_for_paper = is_waiting,
        party_provider = payload.party_provider,
        status         = "pending" if is_waiting else "in_progress",
        created_at     = datetime.now().isoformat(),
        updated_at     = datetime.now().isoformat(),
    )
    db.add(job)
    db.flush()  # Get job_id before creating related records

    # Only create outward entry if the paper is actually available
    if not is_waiting:
        create_outward_for_job(db, job)

    # Create lamination record if provided
    if payload.lam_job:
        lam = LamJob(job_id=job.job_id, **payload.lam_job.model_dump())
        db.add(lam)

    # Create punching record if provided
    if payload.punch_job:
        punch = PunchJob(job_id=job.job_id, **payload.punch_job.model_dump())
        db.add(punch)

    # Create inward entry if provided (operator is logging new paper arrival)
    if payload.inward_entry:
        iw = payload.inward_entry
        # Auto-calculate next challan and serial numbers
        max_ch = db.query(func.max(Inward.ch_no)).scalar() or 0
        max_sr = db.query(func.max(Inward.sr_no)).scalar() or 0
        iw_data = iw.model_dump()
        iw_data["stock_type"] = iw.stock_type.value
        inward = Inward(
            **iw_data,
            ch_no      = max_ch + 1,
            sr_no      = max_sr + 1,
            created_at = datetime.now().isoformat()
        )
        if inward.party_code:
            inward.party_code = inward.party_code.lower()
        db.add(inward)

    db.commit()
    db.refresh(job)

    # If an inward entry was created, it might satisfy this job's paper requirement (or other pending jobs)
    if payload.inward_entry and 'inward' in locals():
        try:
            from routers.inward import auto_activate_pending_jobs
            auto_activate_pending_jobs(db, inward)
            db.refresh(job)
        except Exception as e:
            import traceback
            print(f"Auto-activation check failed during job creation: {e}")
            traceback.print_exc()

    return job


# ── GET /api/jobs/{job_id} ────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get full job details including lamination and punching records.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job #{job_id} not found")
    data = {c.name: getattr(job, c.name) for c in job.__table__.columns}
    data["lam_job"] = job.lam_job
    data["punch_job"] = job.punch_job
    return data


# ── PUT /api/jobs/{job_id} ────────────────────────────────────────────────────

@router.put("/{job_id}", response_model=JobOut)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)):
    """
    Update a job. Only fields that are sent are updated (partial update).
    Outward entry is automatically synced after update.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job #{job_id} not found")

    # Update only fields that were provided
    update_data = payload.model_dump(exclude_unset=True, exclude={"lam_job", "punch_job"})
    for field, value in update_data.items():
        if hasattr(job, field):
            # Convert enum to its value
            val = value.value if hasattr(value, 'value') else value
            if field == "party_code" and val:
                val = val.lower()
            elif field == "paper_code" and val:
                val = val.lower()
            elif field == "paper_size" and val:
                val = val.lower().replace(" ", "")
            setattr(job, field, val)
    
    # If explicitly moving out of waiting, we might need to update status
    if payload.is_waiting_for_paper is False and job.status == "pending":
        # We don't auto-activate here, but we clear the flag
        job.is_waiting_for_paper = False

    job.updated_at = datetime.now().isoformat()

    # Re-extract year/month if date was updated
    if "date" in update_data:
        try:
            d = datetime.strptime(job.date, "%Y-%m-%d")
            job.year  = d.year
            job.month = d.month
        except ValueError:
            pass

    # Recalculate stock and waiting status if not explicitly moved out of waiting
    if payload.is_waiting_for_paper is None and job.status == "pending":
        balance = get_stock_balance(
            db, 
            job.paper_code, 
            job.paper_size, 
            job.paper_source, 
            job.party_code
        )
        job.is_waiting_for_paper = balance < (job.total_sheets or 0)

    # Sync outward entry
    sync_outward_for_job(db, job)

    existing_lam = db.query(LamJob).filter(LamJob.job_id == job_id).first()
    if "lam_job" in payload.model_fields_set and payload.lam_job is None:
        if existing_lam:
            db.delete(existing_lam)
    elif payload.lam_job is not None:
        if existing_lam:
            for field, value in payload.lam_job.model_dump().items():
                setattr(existing_lam, field, value)
        else:
            lam = LamJob(job_id=job_id, **payload.lam_job.model_dump())
            db.add(lam)

    existing_punch = db.query(PunchJob).filter(PunchJob.job_id == job_id).first()
    if "punch_job" in payload.model_fields_set and payload.punch_job is None:
        if existing_punch:
            db.delete(existing_punch)
    elif payload.punch_job is not None:
        if existing_punch:
            for field, value in payload.punch_job.model_dump().items():
                setattr(existing_punch, field, value)
        else:
            punch = PunchJob(job_id=job_id, **payload.punch_job.model_dump())
            db.add(punch)

    db.commit()
    db.refresh(job)
    return job


# ── PATCH /api/jobs/{job_id}/status ──────────────────────────────────────────

@router.patch("/{job_id}/status", response_model=MessageResponse)
def update_job_status(job_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    """
    Update just the status of a job.
    Used by the Pending List page to cycle: pending → in_progress → done
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job #{job_id} not found")

    job.status     = payload.status.value
    job.updated_at = datetime.now().isoformat()
    db.commit()

    return {"message": f"Job #{job_id} status updated to {payload.status.value}", "success": True}


# ── DELETE /api/jobs/{job_id} ─────────────────────────────────────────────────

@router.delete("/{job_id}", response_model=MessageResponse)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """
    Soft delete — sets status to 'deleted'.
    The outward entry is also removed so stock balance is corrected.

    Note: We use soft delete (not physical delete) so the job history
    is preserved. The outward entry IS physically deleted so the
    stock balance corrects itself immediately.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job #{job_id} not found")

    # Remove outward entry → stock balance auto-corrects
    outward = db.query(Outward).filter(Outward.job_id == job_id).first()
    if outward:
        db.delete(outward)

    # Soft delete the job
    job.status     = "deleted"
    job.updated_at = datetime.now().isoformat()

    db.commit()
    return {"message": f"Job #{job_id} deleted. Stock balance has been corrected.", "success": True}


# ── GET /api/jobs/{job_id}/card ───────────────────────────────────────────────

@router.get("/{job_id}/card", response_model=JobCardData)
def get_job_card(job_id: int, db: Session = Depends(get_db)):
    """
    Returns all data needed to render the job card slips.
    This is called by jobcard.html when operator types a job number.

    The response includes lam_job and punch_job only if they exist —
    the frontend uses their presence to decide which slips to show.
    """
    job = db.query(Job).filter(
        Job.job_id == job_id,
        Job.status != "deleted"
    ).first()

    if not job:
        raise HTTPException(
            404,
            f"Job #{job_id} not found. Please check the job number and try again."
        )

    # Convert to bool for safety
    job.is_waiting_for_paper = bool(job.is_waiting_for_paper)

    # Query matching inward entries (case-insensitive, space-free)
    p_code = job.paper_code.lower() if job.paper_code else ""
    p_size = job.paper_size.lower().replace(" ", "") if job.paper_size else ""
    
    inward_q = db.query(Inward).filter(
        func.lower(Inward.paper_code) == p_code,
        func.lower(func.replace(Inward.paper_size, ' ', '')) == p_size,
        Inward.stock_type == job.paper_source
    )
    if job.paper_source == "party":
        inward_q = inward_q.filter(func.lower(Inward.party_code) == job.party_code.lower())
        
    inwards = inward_q.all()
    if not inwards:
        job.inward_status = "none"
        job.inward_sheets = 0
    else:
        has_received = any(i.status == "received" for i in inwards)
        job.inward_status = "received" if has_received else "pending"
        job.inward_sheets = sum(i.total_sheets for i in inwards)

    return job


# ── POST /api/jobs/{job_id}/activate ──────────────────────────────────────────

@router.post("/{job_id}/activate", response_model=JobActivateResponse)
def activate_job(job_id: int, payload: JobActivate, db: Session = Depends(get_db)):
    """
    Move a job from 'pending' to 'in_progress'.
    Enforces stock check and creates the Outward entry.
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(404, f"Job #{job_id} not found")

    if job.status != "pending":
        return {
            "success": False,
            "message": f"Job is already {job.status}",
            "job": job
        }

    # Apply updates if provided (e.g. operator changed paper size or type)
    warning = None
    if payload.paper_code:
        new_paper = payload.paper_code.lower()
        if new_paper != job.paper_code:
            warning = f"Paper type changed from {job.paper_code} to {new_paper}"
            job.paper_code = new_paper
    
    if payload.paper_size:
        job.paper_size = payload.paper_size.lower().replace(" ", "")
    if payload.total_sheets: job.total_sheets = payload.total_sheets
    if payload.paper_source: job.paper_source = payload.paper_source.value

    # Check Stock
    balance = get_stock_balance(db, job.paper_code, job.paper_size, job.paper_source, job.party_code)
    if balance < (job.total_sheets or 0):
        raise HTTPException(400, f"Insufficient stock to activate. Current balance: {balance} sheets.")

    # Success -> Sync Outward and Update Status
    job.status     = "in_progress"
    job.updated_at = datetime.now().isoformat()
    
    sync_outward_for_job(db, job)
    
    db.commit()
    db.refresh(job)
    
    return {
        "success": True,
        "message": "Job activated successfully!",
        "job": job,
        "warning": warning
    }
