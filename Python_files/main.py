"""
main.py
=======
FastAPI application entry point.

HOW TO RUN (copy-paste into terminal):
    pip install fastapi uvicorn sqlalchemy pydantic
    python main.py

Then open in browser:
    http://localhost:8000          → app
    http://localhost:8000/docs     → interactive API docs (auto-generated)
    http://localhost:8000/redoc    → alternative API docs

On LAN (other devices on same Wi-Fi):
    http://192.168.x.x:8000       → replace with your PC's local IP
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine, Base
from routers import jobs, masters, stock, inward, outward, pending
from routers import jobcard

# ── CREATE APP ────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Labh Offset — Print Shop Management",
    description = "Job management, paper stock, job card generation for Labh Offset.",
    version     = "1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow all origins — this is a local network app, no security risk
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── STARTUP: CREATE TABLES ────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    """
    Create all database tables on startup if they don't exist.
    If you already ran migrate.py, tables already exist — this is a no-op.
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database ready")
    print("✓ Labh Offset server started")
    print("  Open: http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")

# ── INCLUDE ROUTERS ───────────────────────────────────────────────────────────
app.include_router(jobs.router)
app.include_router(jobcard.router)
app.include_router(masters.router)
app.include_router(stock.router)
app.include_router(inward.router)
app.include_router(outward.router)
app.include_router(pending.router)

# ── SERVE STATIC FRONTEND FILES ───────────────────────────────────────────────
# All HTML/CSS/JS files in static/ are served directly
# e.g. static/jobcard.html → http://localhost:8000/jobcard.html
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# ── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Labh Offset"}


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host     = "0.0.0.0",   # makes it accessible on LAN, not just localhost
        port     = 8000,
        reload   = True,         # auto-restarts when you save any .py file
    )
