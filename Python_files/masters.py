from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Party, PaperMaster, Operator
from schemas import (
    PartyCreate, PartyUpdate, PartyOut, PartyDropdown,
    PaperCreate, PaperOut, PaperDropdown,
    OperatorCreate, OperatorOut, MessageResponse
)

router = APIRouter(prefix="/api", tags=["Masters"])

# ── PARTIES ──────────────────────────────────────────────────────────────────
@router.get("/parties", response_model=List[PartyDropdown])
def list_parties(db: Session = Depends(get_db)):
    return db.query(Party).filter(Party.is_active == 1).order_by(Party.party_name).all()

@router.post("/parties", response_model=PartyOut)
def create_party(payload: PartyCreate, db: Session = Depends(get_db)):
    existing = db.query(Party).filter(Party.party_code == payload.party_code.lower()).first()
    if existing:
        raise HTTPException(400, f"Party code '{payload.party_code}' already exists")
    party = Party(**payload.model_dump())
    party.party_code = party.party_code.lower()
    db.add(party)
    db.commit()
    db.refresh(party)
    return party

@router.put("/parties/{party_code}", response_model=PartyOut)
def update_party(party_code: str, payload: PartyUpdate, db: Session = Depends(get_db)):
    party = db.query(Party).filter(Party.party_code == party_code.lower()).first()
    if not party:
        raise HTTPException(404, f"Party '{party_code}' not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(party, field, value)
    db.commit()
    db.refresh(party)
    return party

# ── PAPER MASTER ─────────────────────────────────────────────────────────────
@router.get("/papers", response_model=List[PaperDropdown])
def list_papers(db: Session = Depends(get_db)):
    return db.query(PaperMaster).filter(PaperMaster.is_active == 1).order_by(PaperMaster.description).all()

@router.post("/papers", response_model=PaperOut)
def create_paper(payload: PaperCreate, db: Session = Depends(get_db)):
    existing = db.query(PaperMaster).filter(PaperMaster.paper_code == payload.paper_code.lower()).first()
    if existing:
        raise HTTPException(400, f"Paper code '{payload.paper_code}' already exists")
    paper = PaperMaster(**payload.model_dump())
    paper.paper_code = paper.paper_code.lower()
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper

# ── OPERATORS ────────────────────────────────────────────────────────────────
@router.get("/operators", response_model=List[OperatorOut])
def list_operators(db: Session = Depends(get_db)):
    return db.query(Operator).filter(Operator.is_active == 1).order_by(Operator.name).all()

@router.post("/operators", response_model=OperatorOut)
def create_operator(payload: OperatorCreate, db: Session = Depends(get_db)):
    op = Operator(**payload.model_dump())
    db.add(op)
    db.commit()
    db.refresh(op)
    return op
