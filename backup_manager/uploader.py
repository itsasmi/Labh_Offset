import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def upload_to_drive(file_path: str, credentials_path: str, folder_id: str = None) -> bool:
    """
    Uploads a file to Google Drive using a service account credentials JSON.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(credentials_path):
        print(f"Credentials file not found at {credentials_path}. Skipping upload.")
        return False
        
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES)
            
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': os.path.basename(file_path)}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        media = MediaFileUpload(file_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        file = service.files().create(body=file_metadata,
                                      media_body=media,
                                      fields='id').execute()
        print(f"File ID: {file.get('id')} uploaded successfully to Google Drive.")
        return True
    except Exception as e:
        print(f"Failed to upload to Google Drive: {e}")
        return False
