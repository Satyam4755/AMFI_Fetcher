import sys
import os
import pandas as pd

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_sqlite_service import create_tables
from services.scheme_insert_service import save_scheme_to_sqlite

def main():
    print("Starting SIF Import Pipeline...")
    
    csv_path = "data/sif_nav.csv"
    if not os.path.exists(csv_path):
        print(f"Error: CSV file {csv_path} does not exist. Run fetch_sif_nav.py first.")
        return
        
    # Ensure database schema exists
    create_tables()
    
    try:
        # Read the CSV
        df = pd.read_csv(csv_path)
        # Handle nan/null values elegantly
        df = df.fillna("")
    except Exception as e:
        print(f"Failed to read from SIF CSV ({csv_path}): {e}")
        return
        
    total_records = len(df)
    print(f"Found {total_records} records in {csv_path}...")
    
    successful = 0
    failed = 0
    
    # Iterate through DataFrame and UPSERT each row
    for i, row in df.iterrows():
        # Convert row to dictionary format expected by save_scheme_to_sqlite
        # We only pass SIf_Id and SIF_Name, so it gracefully skips scheme mappings
        sif_data = {
            "SIf_Id": row.get("sifId"),
            "SIF_Name": row.get("SIFName"),
            "AMC_Website": None
        }
        
        # Optionally print progress every 10 records
        if (i + 1) % 10 == 0 or (i + 1) == total_records:
            print(f"Processing record {i + 1}/{total_records}...")
            
        success = save_scheme_to_sqlite(sif_data)
        if success:
            successful += 1
        else:
            failed += 1
            
    print("\nImport Pipeline Completed")
    print("-" * 20)
    print(f"Total Records Found : {total_records}")
    print(f"Successful Inserts  : {successful}")
    print(f"Failed Inserts      : {failed}")

if __name__ == "__main__":
    main()
