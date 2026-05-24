from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, case
from typing import Optional, List
from database import get_db
from models import Job
from schemas import JobListItem, ReorderRequest, MessageResponse

router = APIRouter(prefix="/api/pending", tags=["Pending"])

@router.get("", response_model=List[JobListItem])
def list_pending(
    plate_size:    Optional[str] = Query(None),
    operator_name: Optional[str] = Query(None),
    waiting_only:  Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Job).filter(Job.status.in_(["pending", "in_progress"]))
    if plate_size:    q = q.filter(Job.plate_size == plate_size)
    if operator_name: q = q.filter(Job.operator_name == operator_name)
    if waiting_only is not None:
        q = q.filter(Job.is_waiting_for_paper == waiting_only)
    
    # Sort new jobs (queue_order=0) to the bottom, then by queue_order ASC, then newest first
    return q.order_by(
        case((Job.queue_order == 0, 1), else_=0),
        Job.queue_order.asc(),
        desc(Job.job_id)
    ).all()

@router.post("/reorder", response_model=MessageResponse)
def reorder_pending(
    req: ReorderRequest,
    db: Session = Depends(get_db)
):
    # Fetch jobs to update
    jobs = db.query(Job).filter(Job.job_id.in_(req.job_ids)).all()
    job_map = {j.job_id: j for j in jobs}
    
    # Update queue_order based on array index (1-based)
    for idx, j_id in enumerate(req.job_ids):
        if j_id in job_map:
            job_map[j_id].queue_order = idx + 1
            
    db.commit()
    return {"message": "Queue order updated successfully", "success": True}
