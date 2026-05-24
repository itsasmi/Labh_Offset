from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, cast, String
from typing import Optional, List
from database import get_db
from models import Outward
from schemas import OutwardOut

router = APIRouter(prefix="/api/outward", tags=["Outward"])

@router.get("", response_model=List[OutwardOut])
def list_outward(
    party_code: Optional[str] = Query(None),
    paper_code: Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    global_query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    q = db.query(Outward)
    if party_code: q = q.filter(Outward.party_code == party_code.lower())
    if paper_code: q = q.filter(Outward.paper_code == paper_code.lower())
    if date_from:  q = q.filter(Outward.date >= date_from)
    if date_to:    q = q.filter(Outward.date <= date_to)
    if global_query:
        pattern = f"%{global_query}%"
        q = q.filter(
            or_(
                Outward.party_code.ilike(pattern),
                Outward.party_name.ilike(pattern),
                Outward.job_name.ilike(pattern),
                Outward.paper_code.ilike(pattern),
                Outward.paper_name.ilike(pattern),
                Outward.paper_size.ilike(pattern)
            )
        )
    return q.order_by(desc(Outward.date), desc(Outward.id)).offset((page-1)*limit).limit(limit).all()
