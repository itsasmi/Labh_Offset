"""
models.py
=========
SQLAlchemy ORM models — one Python class per database table.
These classes map directly to the tables created by migrate.py.

Every column here matches exactly what is in labh_offset.db.
"""

from sqlalchemy import (
    Column, Integer, Text, Float, ForeignKey,
    String, event, Boolean
)
from sqlalchemy.orm import relationship
from database import Base


# ── PARTIES ───────────────────────────────────────────────────────────────────
class Party(Base):
    """
    Client parties — the print shop's customers.
    e.g. ATUL ENTERPRISE, SHREE SHAKTI PRINTERY
    """
    __tablename__ = "parties"

    party_code = Column(Text, primary_key=True)   # e.g. "amdatu"
    party_name = Column(Text, nullable=False)      # e.g. "ATUL ENTERPRISE"
    phone      = Column(Text, nullable=True)
    email      = Column(Text, nullable=True)
    address    = Column(Text, nullable=True)
    is_active  = Column(Integer, default=1)        # 1 = active, 0 = archived
    created_at = Column(Text)

    # Relationships — allows party.jobs, party.inward_entries
    jobs           = relationship("Job",    back_populates="party")
    inward_entries = relationship("Inward", back_populates="party")


# ── PAPER MASTER ──────────────────────────────────────────────────────────────
class PaperMaster(Base):
    """
    Master list of all paper types.
    e.g. paper_code="300gac", description="300 gsm art card", gsm=300
    """
    __tablename__ = "paper_master"

    paper_code  = Column(Text, primary_key=True)  # e.g. "280gfbb"
    description = Column(Text, nullable=False)     # e.g. "280 GSM FBB"
    gsm         = Column(Integer, nullable=True)   # e.g. 280
    category    = Column(Text, nullable=True)      # e.g. "FBB", "Art Card"
    is_active   = Column(Integer, default=1)


# ── OPERATORS ─────────────────────────────────────────────────────────────────
class Operator(Base):
    """
    Shop floor operators who run the machines.
    e.g. Parth (Offset), Shantaram (Offset), Yash (Lamination)
    """
    __tablename__ = "operators"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    name      = Column(Text, nullable=False, unique=True)
    role      = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)


# ── JOBS ──────────────────────────────────────────────────────────────────────
class Job(Base):
    """
    Core table — one row per print job.
    Sourced from Entry sheet (5976 rows, 49 columns).

    paper_source is the critical field:
        'party'   = client sends their own paper
        'company' = Labh Offset buys paper for this job
    """
    __tablename__ = "jobs"

    job_id         = Column(Integer, primary_key=True)
    date           = Column(Text, nullable=False)
    year           = Column(Integer)
    month          = Column(Integer)

    # Party
    party_code     = Column(Text, ForeignKey("parties.party_code"), nullable=False)
    party_name     = Column(Text, nullable=False)   # denormalised for fast display

    # Job info
    job_name       = Column(Text, nullable=False)
    bill_no        = Column(Text)
    ctcp_bill_no   = Column(Text)
    job_remark     = Column(Text)

    # Paper details
    paper_code     = Column(Text, ForeignKey("paper_master.paper_code"))
    paper_size     = Column(Text)          # full sheet size e.g. "28x40"
    gsm_desc       = Column(Text)          # e.g. "280 GSM FBB"

    # Sheet count
    ream           = Column(Integer)
    sheet_per_ream = Column(Integer)
    loose_sheets   = Column(Integer)
    total_sheets   = Column(Integer)       # = (ream * spr) + loose

    # Cutting
    cut_size       = Column(Text)          # e.g. "13.33x26"
    qty            = Column(Integer)       # number of cut pieces
    cut_part       = Column(Integer)       # cuts per sheet e.g. 2, 3, 4
    printing       = Column(Text)          # s/s | f/b | f+b

    # Printing machine
    pulling        = Column(Text)          # impressions e.g. "1701" or "3100+3100"
    set_no         = Column(Integer, default=1)
    plate_size     = Column(Text)          # "635x775" or "550x670"
    plate_process  = Column(Text)          # CTCP | Thermal | CTP
    operator_name  = Column(Text)
    pulling_charge = Column(Text)

    # Paper source — THE most important new field
    paper_source   = Column(Text, nullable=False, default="party")
    # 'party'   → client's paper, deducts from party stock
    # 'company' → Labh Offset's paper, deducts from company stock

    # Party Provider — who provides paper for cutting (usually same as party)
    party_provider = Column(Text, nullable=True)

    # Status
    status               = Column(Text, nullable=False, default="pending")
    # pending | in_progress | done
    is_waiting_for_paper = Column(Boolean, default=False)
    queue_order          = Column(Integer, default=0)

    created_at     = Column(Text)
    updated_at     = Column(Text)

    # Relationships
    party          = relationship("Party",    back_populates="jobs")
    paper          = relationship("PaperMaster")
    lam_job        = relationship("LamJob",   back_populates="job",
                                  uselist=False, cascade="all, delete-orphan")
    punch_job      = relationship("PunchJob", back_populates="job",
                                  uselist=False, cascade="all, delete-orphan")
    outward_entry  = relationship("Outward",  back_populates="job",
                                  uselist=False, cascade="all, delete-orphan")

    @property
    def has_lamination(self):
        return self.lam_job is not None

    @property
    def has_punching(self):
        return self.punch_job is not None


# ── LAM JOBS ──────────────────────────────────────────────────────────────────
class LamJob(Base):
    """
    Lamination details for a job.
    Only exists if the job has lamination (Matt / Gloss / UV etc.)
    One-to-one with Job.
    """
    __tablename__ = "lam_jobs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    job_id        = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    process       = Column(Text)     # Matt | Gloss | UV | Matt Velvet
    size          = Column(Text)     # lamination size
    agency_name   = Column(Text)     # e.g. "Labh"
    operator_name = Column(Text)     # e.g. "Yash"
    side          = Column(Text)     # S/S | F/B | Both
    pulling       = Column(Integer)
    op_amount     = Column(Float)    # lamination cost
    op_pay        = Column(Float)    # amount paid

    job = relationship("Job", back_populates="lam_job")


# ── PUNCH JOBS ────────────────────────────────────────────────────────────────
class PunchJob(Base):
    """
    Punching / die-cut details for a job.
    Only exists if the job has punching/die-cutting.
    One-to-one with Job.
    """
    __tablename__ = "punch_jobs"

    id     = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    dye    = Column(Text)
    size   = Column(Text)
    gsm    = Column(Text)
    qty    = Column(Integer)
    agency = Column(Text)
    pay    = Column(Float)

    job = relationship("Job", back_populates="punch_job")


# ── INWARD ────────────────────────────────────────────────────────────────────
class Inward(Base):
    """
    Paper received into the shop.

    stock_type = 'party'   → paper sent by a client (party_code is set)
    stock_type = 'company' → paper purchased by Labh Offset (party_code is NULL)
    """
    __tablename__ = "inward"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    ch_no          = Column(Integer)      # challan number
    sr_no          = Column(Integer)      # serial number
    date           = Column(Text, nullable=False)
    dch_no         = Column(Text)         # delivery challan number from supplier
    supplier_name  = Column(Text)         # e.g. "Mansi Paper", "Lalshah 1986"
    paper_code     = Column(Text, ForeignKey("paper_master.paper_code"))
    paper_desc     = Column(Text)         # denormalised description
    paper_size     = Column(Text)         # e.g. "23x36"
    ream           = Column(Integer)
    sheet_per_ream = Column(Integer)
    loose_sheets   = Column(Integer)
    total_sheets   = Column(Integer, nullable=False)
    party_code     = Column(Text, ForeignKey("parties.party_code"), nullable=True)
    stock_type     = Column(Text, nullable=False, default="party")
    notes          = Column(Text)
    status         = Column(Text, nullable=False, default="received")  # received | pending
    created_at     = Column(Text)

    # Relationships
    party = relationship("Party", back_populates="inward_entries")
    paper = relationship("PaperMaster")


# ── OUTWARD ───────────────────────────────────────────────────────────────────
class Outward(Base):
    """
    Paper consumed for a job.

    IMPORTANT: This table is NEVER filled by the operator.
    It is auto-created by the system whenever a job is saved.
    One-to-one with Job (one outward entry per job).

    stock_type mirrors jobs.paper_source:
        'party'   → deducted from party's stock
        'company' → deducted from company's stock
    """
    __tablename__ = "outward"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    job_id      = Column(Integer, ForeignKey("jobs.job_id"),
                         nullable=False, unique=True)
    date        = Column(Text, nullable=False)
    sr_no       = Column(Integer)
    party_code  = Column(Text, nullable=False)
    party_name  = Column(Text, nullable=False)
    job_name    = Column(Text, nullable=False)
    paper_code  = Column(Text)
    paper_name  = Column(Text)
    paper_size  = Column(Text)
    used_sheets = Column(Integer, nullable=False)
    stock_type  = Column(Text, nullable=False, default="party")

    job = relationship("Job", back_populates="outward_entry")


# ── CONFIG ────────────────────────────────────────────────────────────────────
class Config(Base):
    """
    Application configuration key-value store.
    e.g. shop_name, low_stock_threshold, pin_hash
    """
    __tablename__ = "config"

    key   = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)


# ── USERS ─────────────────────────────────────────────────────────────────────
class User(Base):
    """
    Application users for authentication and access control.
    """
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    username   = Column(Text, nullable=False, unique=True)
    password   = Column(Text, nullable=False)      # Hashed password
    is_admin   = Column(Boolean, default=False)
    created_at = Column(Text)
