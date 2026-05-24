import pandas as pd
import sqlite3
from typing import Dict, List

def extract_all_data(db_path: str) -> Dict[str, pd.DataFrame]:
    """
    Connects to the database and extracts all data from all active tables.
    Performs a FULL DATABASE BACKUP.
    Returns a dictionary mapping table_names to pandas DataFrames.
    """
    try:
        conn = sqlite3.connect(db_path)
        
        # Get all table names
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(query, conn)
        
        # Exclude sqlite internal tables
        table_names = [name for name in tables['name'] if not name.startswith('sqlite_')]
        
        dataframes = {}
        for table_name in table_names:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            dataframes[table_name] = df
            
        return dataframes
    finally:
        if 'conn' in locals():
            conn.close()
