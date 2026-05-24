import os
from datetime import datetime

def prepare_storage_paths(base_dir: str):
    """
    Creates the local backup directories if they don't exist.
    Returns a tuple (archival_path, latest_path).
    """
    now = datetime.now()
    year_str = now.strftime('%Y')
    month_str = now.strftime('%m')
    
    # Base backups directory
    backups_base = os.path.join(base_dir, 'backups')
    
    # Year/Month directory
    monthly_dir = os.path.join(backups_base, year_str, month_str)
    os.makedirs(monthly_dir, exist_ok=True)
    
    # File names
    timestamp = now.strftime('%d-%m-%Y')
    archival_filename = f"labh_offset_backup_{timestamp}.xlsx"
    latest_filename = "Latest_data.xlsx"
    
    archival_path = os.path.join(monthly_dir, archival_filename)
    latest_path = os.path.join(base_dir, latest_filename) # Placed in root or wherever you want
    
    return archival_path, latest_path
