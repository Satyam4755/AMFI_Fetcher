import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def parse_summary_xls(xls_path: str) -> dict:
    """
    Reads a Summary XLS file and returns its rows as a dictionary mapping sheet_name to a list of dictionaries.
    Strips extra whitespace from strings and converts NaN to None.
    """
    if not xls_path or not os.path.exists(xls_path):
        logger.error(f"Invalid or non-existent file path provided: {xls_path}")
        return {}
        
    try:
        xls = pd.ExcelFile(xls_path)
        sheet_names = xls.sheet_names
        
        print("\n--- DEBUG LOGGING ---")
        print(f"Workbook: {os.path.basename(xls_path)}")
        print(f"Sheets: {sheet_names}")
        
        all_sheets_data = {}
        for sheet in sheet_names:
            print(f"\nSelected sheet: {sheet}")
            df = pd.read_excel(xls, sheet_name=sheet)
            
            if not df.empty:
                print(f"Detected headers: {df.columns.tolist()}")
                
            if df.empty:
                logger.info(f"Sheet {sheet} in file {xls_path} contains no rows.")
                all_sheets_data[sheet] = []
                continue
                
            # Clean the data:
            # Strip whitespace from string columns
            if hasattr(df, 'map'):
                df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
            else:
                df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
            
            # Convert to dictionary records
            raw_list = df.to_dict(orient="records")
            
            # Clean up NaNs to native Python None
            cleaned_list = []
            for row in raw_list:
                cleaned_row = {}
                for k, v in row.items():
                    if pd.isna(v):
                        cleaned_row[k] = None
                    else:
                        cleaned_row[k] = v
                cleaned_list.append(cleaned_row)
                
            print(f"Rows parsed: {len(cleaned_list)}")
            
            all_sheets_data[sheet] = cleaned_list
            logger.info(f"Successfully parsed {len(cleaned_list)} rows from sheet {sheet} in {xls_path}.")
            
        print("---------------------\n")
        return all_sheets_data
        
    except FileNotFoundError:
        logger.error(f"File not found: {xls_path}")
    except pd.errors.EmptyDataError:
        logger.error(f"File {xls_path} is empty or unreadable.")
    except pd.errors.ParserError as e:
        logger.error(f"Parser error reading {xls_path}: {e}")
    except ValueError as e:
        logger.error(f"Value error reading {xls_path} (possibly unsupported format): {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing XLS {xls_path}: {e}")
        
    return {}
