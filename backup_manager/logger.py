from database import SessionLocal
from models import BackupLog
from datetime import datetime

def log_backup(status: str, file_path: str = None, upload_status: str = 'pending', error_message: str = None):
    """
    Logs the backup operation into the BackupLog database table.
    """
    db = SessionLocal()
    try:
        now = datetime.now()
        new_log = BackupLog(
            backup_date=now.strftime("%Y-%m-%d"),
            status=status,
            file_path=file_path,
            upload_status=upload_status,
            error_message=error_message,
            created_at=now.strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        print(f"Failed to write to backup log: {e}")
    finally:
        db.close()
