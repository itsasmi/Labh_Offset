import sqlite3
import pandas as pd
import os
from datetime import datetime

def backup_database_to_excel():
    # File paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'labh_offset.db')
    backup_dir = os.path.join(base_dir, 'backups')
    
    # Ensure backups directory exists
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Generate filename with current date
    current_date_str = datetime.now().strftime('%Y_%m_%d')
    excel_filename = f'labh_offset_backup_{current_date_str}.xlsx'
    excel_path = os.path.join(backup_dir, excel_filename)
    
    print(f"Connecting to database at: {db_path}")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        
        # Get all table names
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(query, conn)
        
        # Exclude sqlite internal tables
        table_names = [name for name in tables['name'] if not name.startswith('sqlite_')]
        
        if not table_names:
            print("No tables found to backup.")
            return

        print(f"Found {len(table_names)} tables. Starting backup to {excel_path}...")

        # Write to Excel
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for table_name in table_names:
                print(f"  Exporting table: {table_name}")
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                df.to_excel(writer, sheet_name=table_name[:31], index=False) # Excel sheet names max 31 chars
                
        print("Backup completed successfully!")

    except Exception as e:
        print(f"An error occurred during backup: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    backup_database_to_excel()
