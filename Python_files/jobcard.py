"""
routers/jobcard.py
==================
PDF generation route.

    GET /api/jobs/{job_id}/pdf
        → Returns a printable A4 PDF of all job card slips
        → Browser opens print dialog or downloads the file
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Job
from pdf.generator import generate_job_card_pdf

router = APIRouter(prefix="/api/jobs", tags=["Job Card PDF"])


@router.get("/{job_id}/pdf")
def get_job_pdf(job_id: int, db: Session = Depends(get_db)):
    """
    Generate and return the job card PDF.

    The PDF contains:
      - Slip 1: Cutting (always)
      - Slip 2: Offset Printing (always)
      - Slip 3: Lamination (only if job has lamination details)
      - Slip 4: Punching (only if job has punching details)

    The response header Content-Disposition: inline makes the browser
    open the PDF in a new tab for printing rather than downloading it.
    Change to 'attachment' if you want it to download instead.
    """
    # Load job with all related records eagerly (avoids lazy-load errors)
    job = (
        db.query(Job)
        .options(
            joinedload(Job.lam_job),
            joinedload(Job.punch_job),
        )
        .filter(Job.job_id == job_id, Job.status != "deleted")
        .first()
    )

    if not job:
        raise HTTPException(
            status_code = 404,
            detail      = f"Job #{job_id} not found"
        )

    # Generate PDF bytes
    pdf_bytes = generate_job_card_pdf(job)

    filename = f"job_card_{job_id}_{job.party_name.replace(' ', '_')}.pdf"

    return Response(
        content      = pdf_bytes,
        media_type   = "application/pdf",
        headers      = {
            # 'inline' = open in browser tab (for printing)
            # Change to 'attachment' to force download
            "Content-Disposition": f"inline; filename={filename}",
            "Content-Length":      str(len(pdf_bytes)),
        }
    )
