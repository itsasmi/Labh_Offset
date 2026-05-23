from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime
from database import get_db
from models import Inward
from schemas import InwardCreate, InwardOut, MessageResponse

router = APIRouter(prefix="/api/inward", tags=["Inward"])

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
    q = db.query(Inward)
    if party_code: q = q.filter(Inward.party_code == party_code.lower())
    if stock_type: q = q.filter(Inward.stock_type == stock_type)
    if date_from:  q = q.filter(Inward.date >= date_from)
    if date_to:    q = q.filter(Inward.date <= date_to)
    return q.order_by(desc(Inward.id)).offset((page-1)*limit).limit(limit).all()

@router.post("", response_model=InwardOut)
def create_inward(payload: InwardCreate, db: Session = Depends(get_db)):
    if payload.stock_type.value == "party" and not payload.party_code:
        raise HTTPException(400, "party_code is required when stock_type is 'party'")
    max_ch = db.query(func.max(Inward.ch_no)).scalar() or 0
    max_sr = db.query(func.max(Inward.sr_no)).scalar() or 0
    entry = Inward(
        **payload.model_dump(),
        ch_no      = max_ch + 1,
        sr_no      = max_sr + 1,
        stock_type = payload.stock_type.value,
        created_at = datetime.now().isoformat()
    )
    if entry.party_code:
        entry.party_code = entry.party_code.lower()
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

@router.put("/{id}", response_model=InwardOut)
def update_inward(id: int, payload: InwardCreate, db: Session = Depends(get_db)):
    entry = db.query(Inward).filter(Inward.id == id).first()
    if not entry: raise HTTPException(404, "Inward entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value.value if hasattr(value,'value') else value)
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/{id}", response_model=MessageResponse)
def delete_inward(id: int, db: Session = Depends(get_db)):
    entry = db.query(Inward).filter(Inward.id == id).first()
    if not entry: raise HTTPException(404, "Inward entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Inward entry deleted. Stock balance updated.", "success": True}
