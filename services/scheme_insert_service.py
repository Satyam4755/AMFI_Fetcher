import sqlite3
import os
import sys
import pandas as pd

# Allow direct execution by adding project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SCHEME_DB_FILE_PATH

def save_scheme_to_sqlite(scheme_data):
    """
    Inserts or updates a single scheme JSON object into the normalized 
    relational database (sif_master, scheme_master, and composite mappings).
    """
    if not scheme_data:
        print("No scheme data provided.")
        return False
        
    try:
        conn = sqlite3.connect(SCHEME_DB_FILE_PATH)
        
        # Enable foreign key constraint enforcement in SQLite
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        # Extract fields for sif_master
        sif_id = scheme_data.get("SIf_Id")
        sif_name = scheme_data.get("SIF_Name")
        amc_website = scheme_data.get("AMC_Website")
        
        # UPSERT sif_master
        if sif_id is not None and not pd.isna(sif_id):
            cursor.execute("""
                INSERT INTO sif_master (sif_id, sif_name, amc_website)
                VALUES (?, ?, ?)
                ON CONFLICT(sif_id)
                DO UPDATE SET
                    sif_name = excluded.sif_name,
                    amc_website = excluded.amc_website
            """, (sif_id, sif_name, amc_website))
            
        # Extract fields for scheme_master
        scheme_id = scheme_data.get("scheme_id")
        
        # UPSERT scheme_master
        if scheme_id is not None and not pd.isna(scheme_id) and sif_id is not None and not pd.isna(sif_id):
            scheme_name = scheme_data.get("Scheme_Name")
            scheme_type = scheme_data.get("SchemeType_Desc")
            scheme_category = scheme_data.get("SchemeCat_Desc")
            scheme_objective = scheme_data.get("Scheme_Objective")
            launch_date = scheme_data.get("Launch_Date")
            scheme_load = scheme_data.get("scheme_load")
            minimum_amount = scheme_data.get("Scheme_min_amt")
            
            cursor.execute("""
                INSERT INTO scheme_master (
                    scheme_id, sif_id, scheme_name, scheme_type, scheme_category,
                    scheme_objective, launch_date, scheme_load, minimum_amount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scheme_id)
                DO UPDATE SET
                    sif_id = excluded.sif_id,
                    scheme_name = excluded.scheme_name,
                    scheme_type = excluded.scheme_type,
                    scheme_category = excluded.scheme_category,
                    scheme_objective = excluded.scheme_objective,
                    launch_date = excluded.launch_date,
                    scheme_load = excluded.scheme_load,
                    minimum_amount = excluded.minimum_amount
            """, (
                scheme_id, sif_id, scheme_name, scheme_type, scheme_category,
                scheme_objective, launch_date, scheme_load, minimum_amount
            ))
            
        # Extract mappings
        sebi_code = scheme_data.get("sebi_code")
        
        # Handle nan gracefully
        if pd.isna(sebi_code) or not str(sebi_code).strip() or str(sebi_code) == "None":
            sebi_code = None
        else:
            sebi_code = str(sebi_code).strip()
            
        if sebi_code:
            amfi_codes_str = scheme_data.get("amfi_codes")
            if not pd.isna(amfi_codes_str) and str(amfi_codes_str).strip() and str(amfi_codes_str) != "None":
                amfi_codes = [c.strip() for c in str(amfi_codes_str).split(";") if c.strip()]
                for code in amfi_codes:
                    cursor.execute("""
                        INSERT OR IGNORE INTO amfi_composite_mapping (sebi_code, amfi_code)
                        VALUES (?, ?)
                    """, (sebi_code, code))
                    
            isin_codes_str = scheme_data.get("isin_codes")
            if not pd.isna(isin_codes_str) and str(isin_codes_str).strip() and str(isin_codes_str) != "None":
                isin_codes = [c.strip() for c in str(isin_codes_str).split(";") if c.strip()]
                for isin in isin_codes:
                    cursor.execute("""
                        INSERT OR IGNORE INTO isin_composite_mapping (sebi_code, isin)
                        VALUES (?, ?)
                    """, (sebi_code, isin))
            
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error occurred while saving scheme: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while saving scheme: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
