from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from database import get_db
from models import Job
from schemas import JobListItem

router = APIRouter(prefix="/api/pending", tags=["Pending"])

@router.get("", response_model=List[JobListItem])
def list_pending(
    plate_size:    Optional[str] = Query(None),
    operator_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Job).filter(Job.status.in_(["pending", "in_progress"]))
    if plate_size:    q = q.filter(Job.plate_size == plate_size)
    if operator_name: q = q.filter(Job.operator_name == operator_name)
    return q.order_by(desc(Job.job_id)).all()
