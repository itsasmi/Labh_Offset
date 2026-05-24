from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Inward, Job
from routers.inward import auto_activate_pending_jobs

engine = create_engine('sqlite:///labh_offset.db')
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    inward = db.query(Inward).filter(Inward.id == 302).first()
    if inward:
        print(f"Triggering auto-activation for Inward {inward.id}")
        auto_activate_pending_jobs(db, inward)
        print("Done")
        
        job = db.query(Job).filter(Job.job_id == 1024).first()
        print(f"Job 1024 status: {job.status}, waiting_for_paper: {job.is_waiting_for_paper}")
    else:
        print("Inward 302 not found")
finally:
    db.close()
