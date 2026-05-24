"""
schemas.py
==========
Pydantic models — defines exactly what data goes INTO the API
and what comes OUT of the API.

Think of these as contracts:
    - Request schemas  → what the frontend must send
    - Response schemas → what the API sends back

FastAPI uses these to automatically validate, serialize, and
generate API documentation at /docs
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ── ENUMS ─────────────────────────────────────────────────────────────────────

class PaperSource(str, Enum):
    party   = "party"
    company = "company"

class JobStatus(str, Enum):
    pending     = "pending"
    in_progress = "in_progress"
    done        = "done"

class PrintingType(str, Enum):
    ss  = "s/s"
    fb  = "f/b"
    fbb = "f+b"
    bs  = "b/s"
    fs  = "f/s"

class PlateProcess(str, Enum):
    ctcp    = "ctcp"
    thermal = "Tharmal"
    ctp     = "CTP"

class StockType(str, Enum):
    party   = "party"
    company = "company"


# ── PARTY ─────────────────────────────────────────────────────────────────────

class PartyBase(BaseModel):
    party_code: str
    party_name: str
    phone:      Optional[str] = None
    email:      Optional[str] = None
    address:    Optional[str] = None

class PartyCreate(PartyBase):
    pass

class PartyUpdate(BaseModel):
    party_name: Optional[str] = None
    phone:      Optional[str] = None
    email:      Optional[str] = None
    address:    Optional[str] = None
    is_active:  Optional[int] = None

class PartyOut(PartyBase):
    is_active:  int
    created_at: Optional[str] = None
    model_config = {"from_attributes": True}

class PartyDropdown(BaseModel):
    """Minimal data for dropdown menus in the frontend."""
    party_code: str
    party_name: str
    model_config = {"from_attributes": True}


# ── PAPER MASTER ──────────────────────────────────────────────────────────────

class PaperBase(BaseModel):
    paper_code:  str
    description: str
    gsm:         Optional[int]  = None
    category:    Optional[str]  = None

class PaperCreate(PaperBase):
    pass

class PaperOut(PaperBase):
    is_active: int
    model_config = {"from_attributes": True}

class PaperDropdown(BaseModel):
    """Minimal data for dropdown menus."""
    paper_code:  str
    description: str
    gsm:         Optional[int] = None
    model_config = {"from_attributes": True}


# ── OPERATOR ──────────────────────────────────────────────────────────────────

class OperatorBase(BaseModel):
    name: str
    role: Optional[str] = None

class OperatorCreate(OperatorBase):
    pass

class OperatorOut(OperatorBase):
    id:        int
    is_active: int
    model_config = {"from_attributes": True}


# ── LAMINATION ────────────────────────────────────────────────────────────────

class LamJobBase(BaseModel):
    process:       Optional[str]   = None
    size:          Optional[str]   = None
    agency_name:   Optional[str]   = None
    operator_name: Optional[str]   = None
    side:          Optional[str]   = None
    pulling:       Optional[int]   = None
    op_amount:     Optional[float] = None
    op_pay:        Optional[float] = None

class LamJobCreate(LamJobBase):
    pass

class LamJobOut(LamJobBase):
    id:     int
    job_id: int
    model_config = {"from_attributes": True}


# ── PUNCHING ──────────────────────────────────────────────────────────────────

class PunchJobBase(BaseModel):
    dye:    Optional[str]   = None
    size:   Optional[str]   = None
    gsm:    Optional[str]   = None
    qty:    Optional[int]   = None
    agency: Optional[str]   = None
    pay:    Optional[float] = None

class PunchJobCreate(PunchJobBase):
    pass

class PunchJobOut(PunchJobBase):
    id:     int
    job_id: int
    model_config = {"from_attributes": True}


# ── JOB ───────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    """
    What the frontend sends when creating a new job.
    All fields match the Entry sheet columns.
    """
    date:           str
    party_code:     str
    party_name:     str
    job_name:       str
    bill_no:        Optional[str] = None
    ctcp_bill_no:   Optional[str] = None
    job_remark:     Optional[str] = None

    # Paper
    paper_code:     Optional[str] = None
    paper_size:     Optional[str] = None
    gsm_desc:       Optional[str] = None
    ream:           Optional[int] = None
    sheet_per_ream: Optional[int] = None
    loose_sheets:   Optional[int] = None
    total_sheets:   Optional[int] = None

    # Cutting
    cut_size:  Optional[str] = None
    qty:       Optional[int] = None
    cut_part:  Optional[int] = None
    printing:  Optional[str] = None

    # Printing machine
    pulling:        Optional[str] = None
    set_no:         int           = 1
    plate_size:     Optional[str] = None
    plate_process:  Optional[str] = None
    operator_name:  Optional[str] = None
    pulling_charge: Optional[str] = None

    # Paper source — CRITICAL
    paper_source: PaperSource = PaperSource.party
    is_waiting_for_paper: bool = False
    party_provider: Optional[str] = None  # who provides paper for cutting

    # Optional sub-records
    lam_job:      Optional[LamJobCreate]   = None
    punch_job:    Optional[PunchJobCreate] = None
    inward_entry: Optional['InwardCreate'] = None

class JobUpdate(BaseModel):
    """All fields optional — only send what changed."""
    date:           Optional[str]         = None
    party_code:     Optional[str]         = None
    party_name:     Optional[str]         = None
    job_name:       Optional[str]         = None
    bill_no:        Optional[str]         = None
    ctcp_bill_no:   Optional[str]         = None
    job_remark:     Optional[str]         = None
    paper_code:     Optional[str]         = None
    paper_size:     Optional[str]         = None
    gsm_desc:       Optional[str]         = None
    ream:           Optional[int]         = None
    sheet_per_ream: Optional[int]         = None
    loose_sheets:   Optional[int]         = None
    total_sheets:   Optional[int]         = None
    cut_size:       Optional[str]         = None
    qty:            Optional[int]         = None
    cut_part:       Optional[int]         = None
    printing:       Optional[str]         = None
    pulling:        Optional[str]         = None
    set_no:         Optional[int]         = None
    plate_size:     Optional[str]         = None
    plate_process:  Optional[str]         = None
    operator_name:  Optional[str]         = None
    pulling_charge: Optional[str]         = None
    paper_source:   Optional[PaperSource] = None
    is_waiting_for_paper: Optional[bool] = None
    party_provider: Optional[str] = None
    status:         Optional[JobStatus]   = None
    lam_job:        Optional[LamJobCreate]   = None
    punch_job:      Optional[PunchJobCreate] = None

class JobOut(BaseModel):
    """Full job data returned by the API."""
    job_id:         int
    date:           str
    year:           Optional[int] = None
    month:          Optional[int] = None
    party_code:     str
    party_name:     str
    job_name:       str
    bill_no:        Optional[str] = None
    ctcp_bill_no:   Optional[str] = None
    job_remark:     Optional[str] = None
    paper_code:     Optional[str] = None
    paper_size:     Optional[str] = None
    gsm_desc:       Optional[str] = None
    ream:           Optional[int] = None
    sheet_per_ream: Optional[int] = None
    loose_sheets:   Optional[int] = None
    total_sheets:   Optional[int] = None
    cut_size:       Optional[str] = None
    qty:            Optional[int] = None
    cut_part:       Optional[int] = None
    printing:       Optional[str] = None
    pulling:        Optional[str] = None
    set_no:         Optional[int] = None
    plate_size:     Optional[str] = None
    plate_process:  Optional[str] = None
    operator_name:  Optional[str] = None
    pulling_charge: Optional[str] = None
    paper_source:   str
    status:         str
    is_waiting_for_paper: bool = False
    party_provider: Optional[str] = None
    created_at:     Optional[str] = None
    updated_at:     Optional[str] = None
    lam_job:        Optional[LamJobOut]   = None
    punch_job:      Optional[PunchJobOut] = None
    model_config = {"from_attributes": True}

class JobListItem(BaseModel):
    """Compact job data for list views (dashboard, pending list)."""
    job_id:       int
    date:         str
    party_code:   Optional[str] = None
    party_name:   str
    job_name:     str
    qty:          Optional[int] = None
    gsm_desc:     Optional[str] = None
    printing:     Optional[str] = None
    pulling:      Optional[str] = None
    set_no:       Optional[int] = None
    plate_size:   Optional[str] = None
    operator_name: Optional[str] = None
    paper_source: str
    paper_code:   Optional[str] = None
    paper_size:   Optional[str] = None
    total_sheets: Optional[int] = None
    status:       str
    is_waiting_for_paper: Optional[bool] = False
    has_lamination: Optional[bool] = False
    has_punching: Optional[bool] = False
    queue_order:  int = 0
    model_config = {"from_attributes": True}

class JobCardData(BaseModel):
    """
    Everything needed to render the job card slips.
    Returned by GET /api/jobs/{id}/card
    """
    job_id:        int
    date:          str
    party_name:    str
    bill_no:       Optional[str] = None
    ctcp_bill_no:  Optional[str] = None
    job_name:      str
    gsm_desc:      Optional[str] = None
    paper_size:    Optional[str] = None
    ream:          Optional[int] = None
    sheet_per_ream: Optional[int] = None
    loose_sheets:  Optional[int] = None
    total_sheets:  Optional[int] = None
    cut_size:      Optional[str] = None
    cut_part:      Optional[int] = None
    qty:           Optional[int] = None
    printing:      Optional[str] = None
    pulling:       Optional[str] = None
    set_no:        Optional[int] = None
    plate_size:    Optional[str] = None
    plate_process: Optional[str] = None
    operator_name: Optional[str] = None
    paper_source:  str
    status:        Optional[str] = None
    job_remark:    Optional[str] = None
    is_waiting_for_paper: bool = False
    party_provider: Optional[str] = None
    inward_status: str = "none"  # "none", "pending", "received"
    inward_sheets: int = 0
    lam_job:       Optional[LamJobOut]   = None
    punch_job:     Optional[PunchJobOut] = None
    model_config = {"from_attributes": True}


# ── INWARD ────────────────────────────────────────────────────────────────────

class InwardCreate(BaseModel):
    date:          str
    stock_type:    StockType = StockType.party
    party_code:    Optional[str]   = None   # required if stock_type = party
    supplier_name: Optional[str]   = None
    dch_no:        Optional[str]   = None
    paper_code:    Optional[str]   = None
    paper_desc:    Optional[str]   = None
    paper_size:    Optional[str]   = None
    ream:          Optional[int]   = None
    sheet_per_ream: Optional[int]  = None
    loose_sheets:  Optional[int]   = None
    total_sheets:  int
    notes:         Optional[str]   = None
    status:        str             = "received"

class InwardOut(InwardCreate):
    id:         int
    ch_no:      Optional[int] = None
    sr_no:      Optional[int] = None
    party_name: Optional[str] = None   # resolved from Party relationship
    created_at: Optional[str] = None
    model_config = {"from_attributes": True}


# ── OUTWARD ───────────────────────────────────────────────────────────────────

class OutwardOut(BaseModel):
    """Outward entries are read-only — never created by frontend."""
    id:          int
    job_id:      int
    date:        str
    sr_no:       Optional[int] = None
    party_code:  str
    party_name:  str
    job_name:    str
    paper_code:  Optional[str] = None
    paper_name:  Optional[str] = None
    paper_size:  Optional[str] = None
    used_sheets: int
    stock_type:  str
    model_config = {"from_attributes": True}


# ── STOCK ─────────────────────────────────────────────────────────────────────

class StockBalance(BaseModel):
    """One row in the stock register — computed live, never stored."""
    party_code:    Optional[str] = None
    party_name:    Optional[str] = None
    paper_code:    Optional[str] = None
    paper_desc:    Optional[str] = None
    paper_size:    Optional[str] = None
    stock_type:    str
    total_inward:  int
    total_outward: int
    pending_inward: int
    balance:       int
    is_negative:   bool   # True if balance < 0 — shown in red on UI

class StockCheckResponse(BaseModel):
    """Response from GET /api/stock/check — used during job entry."""
    available:  bool    # True if any stock exists
    balance:    int     # current sheet count
    sufficient: bool    # True if balance >= requested qty
    message:    str     # human-readable message for UI

class LedgerEntry(BaseModel):
    """One row in the party ledger — inward or outward transaction."""
    type:            str            # "inward" or "outward"
    date:            str
    job_id:          Optional[int]  = None
    job_name:        Optional[str]  = None
    supplier:        Optional[str]  = None
    paper_code:      Optional[str]  = None
    paper_desc:      Optional[str]  = None
    paper_size:      Optional[str]  = None
    sheets:          int
    running_balance: int            # cumulative balance after this transaction
    
class StockTransferRequest(BaseModel):
    """Payload for transferring party stock to company stock."""
    party_code: str
    paper_code: str
    paper_size: str
    qty:        int


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    """Summary stats shown on the dashboard home page."""
    today_jobs:            int
    pending_jobs:          int
    in_progress_jobs:      int
    low_party_stock_count: int    # party balances below 0
    low_company_stock_count: int  # company stock below threshold


# ── GENERIC RESPONSES ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Generic success/error message."""
    message: str
    success: bool = True

class StatusUpdate(BaseModel):
    """For PATCH /api/jobs/{id}/status"""
    status: JobStatus

class JobActivate(BaseModel):
    """Data for moving a job from Pending to Active."""
    paper_code:   Optional[str] = None
    paper_size:   Optional[str] = None
    total_sheets: Optional[int] = None
    paper_source: Optional[PaperSource] = None

class ReorderRequest(BaseModel):
    """Payload to update the queue order of pending jobs."""
    job_ids: List[int]

class JobActivateResponse(BaseModel):
    """Response after activating a job."""
    success: bool
    message: str
    job:     JobOut
    warning: Optional[str] = None


# ── USERS ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_admin: bool
    created_at: Optional[str] = None
    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_admin: Optional[bool] = None


# ── BILL & CTCP ENTRY ─────────────────────────────────────────────────────────

class PendingBillCtcpListItem(BaseModel):
    """Compact job details for the Bill & CTCP Entry queue."""
    job_id:        int
    date:          str
    job_name:      str
    party_name:    str
    operator_name: Optional[str] = None  # Plate Provider
    gsm_desc:      Optional[str] = None  # Paper Name
    paper_size:    Optional[str] = None  # Paper Size
    bill_no:       Optional[str] = None
    ctcp_bill_no:  Optional[str] = None
    model_config = {"from_attributes": True}

class UpdateBillCtcpRequest(BaseModel):
    """Payload to update Bill and/or CTCP number."""
    bill_no:       Optional[str] = None
    ctcp_bill_no:  Optional[str] = None

