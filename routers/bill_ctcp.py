from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from database import get_db
from models import Job
from schemas import PendingBillCtcpListItem, UpdateBillCtcpRequest, MessageResponse

router = APIRouter(tags=["Bill & CTCP"])

@router.get("/api/pending-bill-ctcp", response_model=List[PendingBillCtcpListItem])
def get_pending_bill_ctcp(db: Session = Depends(get_db)):
    """
    Get all jobs that do not have a bill number OR do not have a CTCP number.
    Returns results sorted in ascending order by job number (oldest first).
    """
    # Fetch jobs where status != 'deleted' and (bill_no is null/empty OR ctcp_bill_no is null/empty)
    q = db.query(Job).filter(
        Job.status != 'deleted',
        or_(
            Job.bill_no.is_(None),
            Job.bill_no == "",
            Job.ctcp_bill_no.is_(None),
            Job.ctcp_bill_no == ""
        )
    )
    
    # Sort in ascending order by job_id (oldest pending job first)
    return q.order_by(Job.job_id.asc()).all()

@router.put("/api/update-bill-ctcp/{jobId}", response_model=MessageResponse)
def update_bill_ctcp(jobId: int, payload: UpdateBillCtcpRequest, db: Session = Depends(get_db)):
    """
    Update the bill number and/or CTCP number for a specific job.
    """
    job = db.query(Job).filter(Job.job_id == jobId).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job #{jobId} not found")
        
    # Update fields only if provided in payload (convert empty strings to None/NULL)
    if payload.bill_no is not None:
        val = payload.bill_no.strip()
        job.bill_no = val if val else None
        
    if payload.ctcp_bill_no is not None:
        val = payload.ctcp_bill_no.strip()
        job.ctcp_bill_no = val if val else None
        
    db.commit()
    return {"message": "Billing/CTCP details updated successfully", "success": True}
