import os
from .extractor import extract_all_data
from .generator import generate_excel_files
from .storage import prepare_storage_paths
from .uploader import upload_to_drive
from .logger import log_backup

def run_backup_pipeline():
    """
    Executes the complete backup pipeline:
    1. Prepare Storage
    2. Extract Data
    3. Generate Excel files
    4. Upload to Google Drive (if configured)
    5. Log the process
    """
    print("--- Starting Automated Backup Pipeline ---")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'labh_offset.db')
    credentials_path = os.path.join(base_dir, 'gdrive_credentials.json')
    
    # 1. Prepare Storage Paths
    archival_path, latest_path = prepare_storage_paths(base_dir)
    print(f"Archival path: {archival_path}")
    
    upload_status = 'skipped'
    status = 'success'
    error_msg = None
    
    try:
        # 2. Extract Data (Full DB Backup)
        print("Extracting full database...")
        dataframes = extract_all_data(db_path)
        
        if not dataframes:
            raise Exception("No tables found to backup.")
            
        # 3. Generate Excel files
        print(f"Generating Excel files...")
        generate_excel_files(dataframes, archival_path, latest_path)
        print(f"Generated successfully: {archival_path} and {latest_path}")
        
        # 4. Upload to Google Drive
        if os.path.exists(credentials_path):
            print("Google Drive credentials found, attempting upload...")
            upload_success = upload_to_drive(archival_path, credentials_path)
            # Also upload the Latest_data.xlsx? Let's just upload the archival one,
            # or upload both. We will upload the archival one as the backup.
            if upload_success:
                upload_status = 'success'
            else:
                upload_status = 'failed'
                error_msg = 'Google Drive upload failed. Check credentials.'
        else:
            print("No gdrive_credentials.json found. Skipping cloud upload.")
            
    except Exception as e:
        status = 'failed'
        error_msg = str(e)
        print(f"Pipeline failed: {error_msg}")
        
    # 5. Log the process
    log_backup(status=status, file_path=archival_path, upload_status=upload_status, error_message=error_msg)
    print("--- Backup Pipeline Finished ---")
