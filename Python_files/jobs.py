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
from sqlalchemy import func, desc
from datetime import datetime, date
from typing import Optional, List

from database import get_db
from models import Job, LamJob, PunchJob, Outward, Party, PaperMaster
from schemas import (
    JobCreate, JobUpdate, JobOut, JobListItem,
    JobCardData, MessageResponse, StatusUpdate
)

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
    party_code: Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    search:     Optional[str] = Query(None),   # searches party_name and job_name
    page:       int           = Query(1, ge=1),
    limit:      int           = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    List jobs with optional filters.
    Returns compact JobListItem objects (not full job details).
    """
    q = db.query(Job)

    if party_code:
        q = q.filter(Job.party_code == party_code.lower())
    if status:
        q = q.filter(Job.status == status)
    if date_from:
        q = q.filter(Job.date >= date_from)
    if date_to:
        q = q.filter(Job.date <= date_to)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            Job.party_name.ilike(pattern) |
            Job.job_name.ilike(pattern)
        )

    total = q.count()
    jobs  = q.order_by(desc(Job.job_id)) \
              .offset((page - 1) * limit) \
              .limit(limit) \
              .all()

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
    # Parse year and month from date string
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
        paper_code     = payload.paper_code,
        paper_size     = payload.paper_size,
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
        status         = "pending",
        created_at     = datetime.now().isoformat(),
        updated_at     = datetime.now().isoformat(),
    )
    db.add(job)
    db.flush()  # Get job_id before creating related records

    # Auto-create outward entry (same transaction)
    create_outward_for_job(db, job)

    # Create lamination record if provided
    if payload.lam_job:
        lam = LamJob(job_id=job.job_id, **payload.lam_job.model_dump())
        db.add(lam)

    # Create punching record if provided
    if payload.punch_job:
        punch = PunchJob(job_id=job.job_id, **payload.punch_job.model_dump())
        db.add(punch)

    db.commit()
    db.refresh(job)
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
    return job


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
            setattr(job, field, value.value if hasattr(value, 'value') else value)

    job.updated_at = datetime.now().isoformat()

    # Re-extract year/month if date was updated
    if "date" in update_data:
        try:
            d = datetime.strptime(job.date, "%Y-%m-%d")
            job.year  = d.year
            job.month = d.month
        except ValueError:
            pass

    # Sync outward entry
    sync_outward_for_job(db, job)

    # Update lamination if provided
    if payload.lam_job is not None:
        existing_lam = db.query(LamJob).filter(LamJob.job_id == job_id).first()
        if existing_lam:
            for field, value in payload.lam_job.model_dump().items():
                setattr(existing_lam, field, value)
        else:
            lam = LamJob(job_id=job_id, **payload.lam_job.model_dump())
            db.add(lam)

    # Update punching if provided
    if payload.punch_job is not None:
        existing_punch = db.query(PunchJob).filter(PunchJob.job_id == job_id).first()
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

    return job
