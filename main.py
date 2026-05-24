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
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from database import engine, Base, SessionLocal
from routers import jobs, masters, stock, inward, outward, pending
from routers import jobcard, auth_routes, users, bill_ctcp, backups
from models import User
from auth import get_password_hash

from apscheduler.schedulers.background import BackgroundScheduler
import calendar
from datetime import timedelta
from backup_manager.orchestrator import run_backup_pipeline

def scheduled_backup_check():
    """Runs daily at 12:00 PM. Triggers backup if it's the last day of month (and not Sunday), or 1st of month (if last day was Sunday)."""
    now = datetime.now()
    last_day_of_month = calendar.monthrange(now.year, now.month)[1]
    is_last_day = (now.day == last_day_of_month)
    
    should_run = False
    if is_last_day:
        if now.weekday() != 6: # 6 is Sunday
            should_run = True
    elif now.day == 1:
        yesterday = now - timedelta(days=1)
        if yesterday.weekday() == 6:
            should_run = True
            
    if should_run:
        print("[Scheduler] Triggering Automated Monthly Backup...")
        run_backup_pipeline()

# ── CREATE APP ────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Labh Offset — Print Shop Management",
    description = "Job management, paper stock, job card generation for Labh Offset.",
    version     = "1.1.0",  # no-cache fix
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
def seed_admin_users():
    db = SessionLocal()
    try:
        admins = [
            {"username": "asmi", "password": "7434023114"},
            {"username": "chirag", "password": "9376146514"}
        ]
        for admin in admins:
            existing = db.query(User).filter(User.username == admin["username"]).first()
            if not existing:
                new_admin = User(
                    username=admin["username"],
                    password=get_password_hash(admin["password"]),
                    is_admin=True,
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                db.add(new_admin)
        db.commit()
    finally:
        db.close()

@app.on_event("startup")
def startup():
    """
    Create all database tables on startup if they don't exist.
    If you already ran migrate.py, tables already exist — this is a no-op.
    """
    Base.metadata.create_all(bind=engine)
    seed_admin_users()
    
    # Initialize APScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_backup_check, 'cron', hour=12, minute=0)
    scheduler.start()
    
    print("[OK] Database ready and admins seeded")
    print("[OK] APScheduler started for automated backups")
    print("[OK] Labh Offset server started")
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
app.include_router(auth_routes.router)
app.include_router(users.router)
app.include_router(bill_ctcp.router)
app.include_router(backups.router)

# ── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Labh Offset"}

# ── SERVE STATIC FRONTEND FILES ───────────────────────────────────────────────
import mimetypes
from fastapi.responses import FileResponse

static_dir = os.path.join(os.path.dirname(__file__), "static")

NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma":        "no-cache",
    "Expires":       "0",
}

# Serve HTML files with explicit no-cache headers
@app.get("/{page:path}.html")
async def serve_html(page: str, request: Request):
    if page != "login":
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/login.html", status_code=303)
            
    file_path = os.path.join(static_dir, f"{page}.html")
    if not os.path.exists(file_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    return FileResponse(file_path, media_type="text/html", headers=NO_CACHE)

@app.get("/")
async def root(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login.html", status_code=303)
    return RedirectResponse(url="/index.html", status_code=303)

# Mount everything else (CSS, JS, images)
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=False), name="static")


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host     = "0.0.0.0",
        port     = 8000,
        reload   = True,
    )
