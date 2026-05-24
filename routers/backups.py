from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import BackupLog
from backup_manager.orchestrator import run_backup_pipeline
import threading

router = APIRouter(
    prefix="/api/backups",
    tags=["Backups"]
)

@router.get("/logs")
def get_backup_logs(db: Session = Depends(get_db)):
    """
    Returns the history of all backups.
    """
    logs = db.query(BackupLog).order_by(BackupLog.id.desc()).all()
    return logs

@router.post("/generate")
def trigger_manual_backup():
    """
    Triggers a manual backup asynchronously so it doesn't block the request.
    """
    thread = threading.Thread(target=run_backup_pipeline)
    thread.start()
    return {"status": "success", "message": "Backup generation started in the background."}
