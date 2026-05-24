import pandas as pd
from typing import Dict
from openpyxl.styles import Font, Alignment
import os
import shutil

def format_excel_sheet(writer: pd.ExcelWriter, df: pd.DataFrame, sheet_name: str):
    """
    Applies formatting to the Excel sheet:
    - Auto-adjusts column widths
    - Bolds headers
    """
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Format Headers
    for col_num, value in enumerate(df.columns.values):
        cell = worksheet.cell(row=1, column=col_num + 1)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        
    # Auto-adjust column widths
    for col in worksheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column].width = adjusted_width

def generate_excel_files(dataframes: Dict[str, pd.DataFrame], output_path_archival: str, output_path_latest: str):
    """
    Generates two formatted Excel files from the dataframes:
    1. The archival backup file
    2. The Latest_data.xlsx file
    """
    # Generate Archival
    with pd.ExcelWriter(output_path_archival, engine='openpyxl') as writer:
        for table_name, df in dataframes.items():
            safe_sheet_name = table_name[:31]  # Excel limits sheet names to 31 chars
            format_excel_sheet(writer, df, safe_sheet_name)
            
    # Copy to Latest
    shutil.copy2(output_path_archival, output_path_latest)
