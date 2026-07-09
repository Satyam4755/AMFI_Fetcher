import sqlite3
import os
import sys

# Allow direct execution by adding project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SCHEME_DB_FILE_PATH

def create_tables():
    """
    Creates the relational database schema for Scheme data and composite mappings.
    """
    # Ensure the database directory exists
    os.makedirs(os.path.dirname(SCHEME_DB_FILE_PATH), exist_ok=True)
    
    try:
        print(f"Connecting to SQLite database at {SCHEME_DB_FILE_PATH}...")
        conn = sqlite3.connect(SCHEME_DB_FILE_PATH)
        
        # Enable foreign key constraint enforcement in SQLite
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        
        print("Creating table 'sif_master'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sif_master (
                sif_id INTEGER PRIMARY KEY,
                sif_name TEXT NOT NULL,
                amc_website TEXT
            )
        """)
        
        print("Creating table 'scheme_master'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheme_master (
                scheme_id TEXT PRIMARY KEY,
                sif_id INTEGER NOT NULL,
                scheme_name TEXT NOT NULL,
                scheme_type TEXT,
                scheme_category TEXT,
                scheme_objective TEXT,
                launch_date TEXT,
                scheme_load TEXT,
                minimum_amount TEXT,
                sebi_code TEXT UNIQUE,
                FOREIGN KEY (sif_id) REFERENCES sif_master(sif_id)
            )
        """)
        
        print("Creating table 'amfi_composite_mapping'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS amfi_composite_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sebi_code TEXT NOT NULL,
                amfi_code TEXT NOT NULL,
                FOREIGN KEY (sebi_code) REFERENCES scheme_master(sebi_code),
                UNIQUE(sebi_code, amfi_code)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_amfi_sebi ON amfi_composite_mapping(sebi_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_amfi_code ON amfi_composite_mapping(amfi_code)")
        
        print("Creating table 'isin_composite_mapping'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS isin_composite_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sebi_code TEXT NOT NULL,
                isin TEXT NOT NULL,
                FOREIGN KEY (sebi_code) REFERENCES scheme_master(sebi_code),
                UNIQUE(sebi_code, isin)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_isin_sebi ON isin_composite_mapping(sebi_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_isin_code ON isin_composite_mapping(isin)")
        
        conn.commit()
        print("Successfully created database schema.")
        
    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    create_tables()
