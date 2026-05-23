from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime
from database import get_db
from models import Inward, Job, Outward, PaperMaster
from schemas import InwardCreate, InwardOut, MessageResponse
from routers.stock import get_stock_balance
from routers.jobs import get_next_outward_sr

router = APIRouter(prefix="/api/inward", tags=["Inward"])


def _enrich(entry: Inward) -> dict:
    """Build an InwardOut-compatible dict with party_name resolved."""
    data = {c.name: getattr(entry, c.name) for c in entry.__table__.columns}
    data["party_name"] = entry.party.party_name if entry.party else None
    data["paper_desc"] = entry.paper.description if entry.paper else data.get("paper_desc")
    return data


def auto_activate_pending_jobs(db: Session, entry: Inward):
    """
    Chronologically scans pending jobs that are waiting for the paper size and type
    logged by this inward entry, and auto-activates them if stock is now sufficient.
    """
    entry_paper_code = entry.paper_code.lower() if entry.paper_code else ""
    entry_paper_size = entry.paper_size.lower().replace(" ", "") if entry.paper_size else ""
    entry_stock_type = entry.stock_type

    # Query matching pending jobs
    q = db.query(Job).filter(
        Job.status == "pending",
        Job.is_waiting_for_paper == True,
        func.lower(Job.paper_code) == entry_paper_code,
        func.lower(func.replace(Job.paper_size, ' ', '')) == entry_paper_size,
        Job.paper_source == entry_stock_type
    )
    if entry_stock_type == "party":
        entry_party_code = entry.party_code.lower() if entry.party_code else ""
        q = q.filter(func.lower(Job.party_code) == entry_party_code)
        
    matching_jobs = q.order_by(Job.job_id).all()
    if not matching_jobs:
        return

    received_in = db.query(func.coalesce(func.sum(Inward.total_sheets), 0)).filter(
        func.lower(Inward.paper_code) == entry_paper_code,
        func.lower(func.replace(Inward.paper_size, ' ', '')) == entry_paper_size,
        Inward.stock_type == entry_stock_type,
        Inward.status == "received"
    )
    if entry_stock_type == "party":
        entry_party_code = entry.party_code.lower() if entry.party_code else ""
        received_in = received_in.filter(func.lower(Inward.party_code) == entry_party_code)

    consumed_by_active_jobs = db.query(func.coalesce(func.sum(Outward.used_sheets), 0)).join(
        Job, Job.job_id == Outward.job_id
    ).filter(
        func.lower(Outward.paper_code) == entry_paper_code,
        func.lower(func.replace(Outward.paper_size, ' ', '')) == entry_paper_size,
        Outward.stock_type == entry_stock_type,
        ~(
            (Job.status == "pending") &
            (Job.is_waiting_for_paper == True)
        )
    )
    if entry_stock_type == "party":
        consumed_by_active_jobs = consumed_by_active_jobs.filter(func.lower(Outward.party_code) == entry_party_code)

    available_for_waiting_jobs = (received_in.scalar() or 0) - (consumed_by_active_jobs.scalar() or 0)
    
    for job in matching_jobs:
        required = job.total_sheets or 0
        if available_for_waiting_jobs >= required:
            # Activate job
            job.status = "in_progress"
            job.is_waiting_for_paper = False
            job.updated_at = datetime.now().isoformat()
            
            # Get paper description for display
            paper_name = job.gsm_desc or ""
            if not paper_name and job.paper_code:
                pm = db.query(PaperMaster).filter(
                    PaperMaster.paper_code == job.paper_code
                ).first()
                if pm:
                    paper_name = pm.description

            # Create Outward entry if missing
            existing = db.query(Outward).filter(Outward.job_id == job.job_id).first()
            if existing:
                existing.date        = job.date
                existing.party_code  = job.party_code
                existing.party_name  = job.party_name
                existing.job_name    = job.job_name
                existing.paper_code  = job.paper_code
                existing.paper_name  = paper_name
                existing.paper_size  = job.paper_size
                existing.used_sheets = job.total_sheets or 0
                existing.stock_type  = job.paper_source
            else:
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
            available_for_waiting_jobs -= required

    db.commit()


@router.get("", response_model=List[InwardOut])
def list_inward(
    party_code: Optional[str] = Query(None),
    stock_type: Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    q = db.query(Inward).options(joinedload(Inward.party), joinedload(Inward.paper))
    if party_code: q = q.filter(Inward.party_code == party_code.lower())
    if stock_type: q = q.filter(Inward.stock_type == stock_type)
    if date_from:  q = q.filter(Inward.date >= date_from)
    if date_to:    q = q.filter(Inward.date <= date_to)
    entries = q.order_by(desc(Inward.id)).offset((page-1)*limit).limit(limit).all()
    return [_enrich(e) for e in entries]

@router.post("", response_model=InwardOut)
def create_inward(payload: InwardCreate, db: Session = Depends(get_db)):
    if payload.stock_type.value == "party" and not payload.party_code:
        raise HTTPException(400, "party_code is required when stock_type is 'party'")
    max_ch = db.query(func.max(Inward.ch_no)).scalar() or 0
    max_sr = db.query(func.max(Inward.sr_no)).scalar() or 0
    data = payload.model_dump()
    data["stock_type"] = payload.stock_type.value
    entry = Inward(
        **data,
        ch_no      = max_ch + 1,
        sr_no      = max_sr + 1,
        created_at = datetime.now().isoformat()
    )
    if entry.party_code:
        entry.party_code = entry.party_code.lower()
    if entry.paper_code:
        entry.paper_code = entry.paper_code.lower()
    if entry.paper_size:
        entry.paper_size = entry.paper_size.lower().replace(" ", "")
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    # Auto-activate any matching pending jobs waiting for this paper
    try:
        auto_activate_pending_jobs(db, entry)
    except Exception as e:
        # Gracefully log activation failures so the inward creation itself doesn't crash
        import traceback
        print(f"Auto-activation check failed: {e}")
        traceback.print_exc()

    return _enrich(entry)

@router.put("/{id}", response_model=InwardOut)
def update_inward(id: int, payload: InwardCreate, db: Session = Depends(get_db)):
    entry = db.query(Inward).filter(Inward.id == id).first()
    if not entry: raise HTTPException(404, "Inward entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "party_code" and value:
            setattr(entry, field, value.lower())
        elif field == "paper_code" and value:
            setattr(entry, field, value.lower())
        elif field == "paper_size" and value:
            setattr(entry, field, value.lower().replace(" ", ""))
        else:
            setattr(entry, field, value.value if hasattr(value,'value') else value)
    db.commit()
    db.refresh(entry)
    
    # Also trigger auto-activation of pending jobs if update changes status or paper specs
    if entry.status == "received":
        try:
            auto_activate_pending_jobs(db, entry)
        except Exception as e:
            print(f"Auto-activation check failed on update: {e}")
            
    return _enrich(entry)

@router.delete("/{id}", response_model=MessageResponse)
def delete_inward(id: int, db: Session = Depends(get_db)):
    entry = db.query(Inward).filter(Inward.id == id).first()
    if not entry: raise HTTPException(404, "Inward entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Inward entry deleted. Stock balance updated.", "success": True}
