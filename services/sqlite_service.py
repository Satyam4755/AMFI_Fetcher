import pandas as pd
import os
import sqlite3

def save_to_sqlite(csv_file, db_path, table_name):
    """Reads a CSV file and loads its contents into a SQLite database."""
    if not os.path.exists(csv_file):
        print(f"CSV file {csv_file} does not exist.")
        return False
        
    try:
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        print(f"Connecting to SQLite database at {db_path}...")
        conn = sqlite3.connect(db_path)
        
        print(f"Reading CSV from {csv_file}...")
        df = pd.read_csv(csv_file)
        
        print(f"Inserting {len(df)} records into table '{table_name}'...")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        
        print("Successfully saved data to SQLite database.")
        return True
    except Exception as e:
        print(f"Error while saving to SQLite: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
            print("Database connection closed.")
