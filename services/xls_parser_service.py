import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def parse_summary_xls(xls_path: str) -> list[dict]:
    """
    Reads a Summary XLS file and returns its rows as a list of dictionaries.
    Strips extra whitespace from strings and converts NaN to None.
    """
    if not xls_path or not os.path.exists(xls_path):
        logger.error(f"Invalid or non-existent file path provided: {xls_path}")
        return []
        
    try:
        # Read the Excel file.
        # We assume pandas will pick the correct engine (xlrd for .xls, openpyxl for .xlsx)
        df = pd.read_excel(xls_path)
        
        if df.empty:
            logger.info(f"File {xls_path} contains no rows.")
            return []
            
        # Clean the data:
        # Strip whitespace from string columns
        # Pandas 2.1.0+ prefers map over applymap for dataframes
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
            
        logger.info(f"Successfully parsed {len(cleaned_list)} rows from {xls_path}.")
        return cleaned_list
        
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
        
    return []
