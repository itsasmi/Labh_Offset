from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
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
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    q = db.query(Outward)
    if party_code: q = q.filter(Outward.party_code == party_code.lower())
    if paper_code: q = q.filter(Outward.paper_code == paper_code.lower())
    if date_from:  q = q.filter(Outward.date >= date_from)
    if date_to:    q = q.filter(Outward.date <= date_to)
    return q.order_by(desc(Outward.id)).offset((page-1)*limit).limit(limit).all()
