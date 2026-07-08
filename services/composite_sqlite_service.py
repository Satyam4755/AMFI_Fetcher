import sqlite3
import logging
import os
import sys

# Allow direct execution by adding project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SCHEME_DB_FILE_PATH

logger = logging.getLogger(__name__)

def create_composite_tables():
    """
    Creates the relational database schema for composite mappings.
    """
    os.makedirs(os.path.dirname(SCHEME_DB_FILE_PATH), exist_ok=True)
    
    try:
        logger.info(f"Connecting to SQLite database at {SCHEME_DB_FILE_PATH}...")
        conn = sqlite3.connect(SCHEME_DB_FILE_PATH)
        cursor = conn.cursor()
        
        logger.info("Creating table 'amfi_composite_mapping'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS amfi_composite_mapping (
                sebi_code TEXT NOT NULL,
                amfi_code TEXT NOT NULL UNIQUE,
                PRIMARY KEY (sebi_code, amfi_code)
            )
        """)
        
        logger.info("Creating table 'isin_composite_mapping'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS isin_composite_mapping (
                sebi_code TEXT NOT NULL,
                isin TEXT NOT NULL UNIQUE,
                PRIMARY KEY (sebi_code, isin)
            )
        """)
        
        conn.commit()
        logger.info("Successfully created composite mapping database schema.")
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error occurred while creating composite tables: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating composite tables: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed.")

def insert_composite_mapping(mapping: dict) -> bool:
    """
    Inserts composite mappings into the SQLite database using INSERT OR IGNORE.
    """
    if not mapping or not mapping.get("sebi_code"):
        logger.warning("Invalid mapping data or missing sebi_code.")
        return False
        
    sebi_code = mapping.get("sebi_code")
    amfi_mapping = mapping.get("amfi_mapping", [])
    isin_mapping = mapping.get("isin_mapping", [])
    
    if not amfi_mapping and not isin_mapping:
        logger.info("No AMFI or ISIN mappings to insert.")
        return False
        
    try:
        conn = sqlite3.connect(SCHEME_DB_FILE_PATH)
        cursor = conn.cursor()
        
        amfi_inserted = 0
        isin_inserted = 0
        
        for item in amfi_mapping:
            amfi_code = item.get("amfi_code")
            if amfi_code:
                cursor.execute("""
                    INSERT OR IGNORE INTO amfi_composite_mapping (sebi_code, amfi_code)
                    VALUES (?, ?)
                """, (sebi_code, amfi_code))
                if cursor.rowcount > 0:
                    amfi_inserted += 1
                    
        for item in isin_mapping:
            isin = item.get("isin")
            if isin:
                cursor.execute("""
                    INSERT OR IGNORE INTO isin_composite_mapping (sebi_code, isin)
                    VALUES (?, ?)
                """, (sebi_code, isin))
                if cursor.rowcount > 0:
                    isin_inserted += 1
                    
        conn.commit()
        logger.info(f"Successfully inserted {amfi_inserted} AMFI mappings and {isin_inserted} ISIN mappings.")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error occurred while inserting composite mapping: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while inserting composite mapping: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_composite_tables()
