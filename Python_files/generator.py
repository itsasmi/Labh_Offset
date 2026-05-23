"""
pdf/generator.py
================
Generates job card PDFs using Jinja2 templates + WeasyPrint.

Called by the route:
    GET /api/jobs/{job_id}/pdf

Returns bytes of a PDF file containing all applicable job card slips:
    - Slip 1: Cutting       (always)
    - Slip 2: Offset        (always)
    - Slip 3: Lamination    (only if job has lam_job)
    - Slip 4: Punching      (only if job has punch_job)

The PDF is A4, portrait, ready to print and cut.
"""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import weasyprint


# ── TEMPLATE SETUP ────────────────────────────────────────────
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


# ── MAIN FUNCTION ─────────────────────────────────────────────

def generate_job_card_pdf(job) -> bytes:
    """
    Generate a PDF job card for the given job object.

    Args:
        job: SQLAlchemy Job model instance (with lam_job and punch_job loaded)

    Returns:
        bytes: PDF file content ready to send as HTTP response
    """
    template = jinja_env.get_template("job_card.html")

    # Build a plain dict so Jinja2 can access all fields
    # This avoids SQLAlchemy lazy-loading issues inside the template
    job_data = _job_to_dict(job)

    html_content = template.render(
        job          = job_data,
        generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p"),
    )

    # WeasyPrint converts the HTML to PDF
    pdf_bytes = weasyprint.HTML(
        string   = html_content,
        base_url = TEMPLATE_DIR,   # for any relative asset paths
    ).write_pdf()

    return pdf_bytes


def _job_to_dict(job) -> dict:
    """
    Convert a SQLAlchemy Job model instance to a plain dict
    that Jinja2 can safely access without hitting lazy-load issues.
    """
    d = {
        "job_id":         job.job_id,
        "date":           job.date or "",
        "party_name":     job.party_name or "",
        "party_code":     job.party_code or "",
        "job_name":       job.job_name or "",
        "bill_no":        job.bill_no,
        "ctcp_bill_no":   job.ctcp_bill_no,
        "job_remark":     job.job_remark,
        "paper_code":     job.paper_code,
        "paper_size":     job.paper_size,
        "gsm_desc":       job.gsm_desc,
        "ream":           job.ream,
        "sheet_per_ream": job.sheet_per_ream,
        "loose_sheets":   job.loose_sheets,
        "total_sheets":   job.total_sheets,
        "cut_size":       job.cut_size,
        "qty":            job.qty,
        "cut_part":       job.cut_part,
        "printing":       job.printing,
        "pulling":        job.pulling,
        "set_no":         job.set_no or 1,
        "plate_size":     job.plate_size,
        "plate_process":  job.plate_process,
        "operator_name":  job.operator_name,
        "pulling_charge": job.pulling_charge,
        "paper_source":   job.paper_source or "party",
        "status":         job.status,
        "lam_job":   None,
        "punch_job": None,
    }

    # Lamination details
    if job.lam_job:
        l = job.lam_job
        d["lam_job"] = {
            "process":       l.process,
            "size":          l.size,
            "agency_name":   l.agency_name,
            "operator_name": l.operator_name,
            "side":          l.side,
            "pulling":       l.pulling,
            "op_amount":     l.op_amount,
            "op_pay":        l.op_pay,
        }

    # Punching details
    if job.punch_job:
        p = job.punch_job
        d["punch_job"] = {
            "dye":    p.dye,
            "size":   p.size,
            "gsm":    p.gsm,
            "qty":    p.qty,
            "agency": p.agency,
            "pay":    p.pay,
        }

    # Convert dict to object so Jinja2 can use dot notation (job.field)
    return _DotDict(d)


class _DotDict(dict):
    """
    A dict subclass that allows attribute-style access.
    So Jinja2 can write {{ job.party_name }} instead of {{ job['party_name'] }}.
    Also handles nested dicts (lam_job, punch_job).
    """
    def __getattr__(self, key):
        try:
            val = self[key]
            if isinstance(val, dict):
                return _DotDict(val)
            return val
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value
