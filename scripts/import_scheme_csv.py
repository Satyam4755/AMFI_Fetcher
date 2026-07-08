import sys
import os
import pandas as pd

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_sqlite_service import create_tables
from services.scheme_insert_service import save_scheme_to_sqlite

def main():
    print("Starting Scheme Import Pipeline...")
    
    csv_path = "data/sif_scheme.csv"
    if not os.path.exists(csv_path):
        print(f"Error: CSV file {csv_path} does not exist. Run fetch_scheme_data.py first.")
        return
        
    # Ensure database schema exists
    create_tables()
    
    try:
        # Read the CSV
        df = pd.read_csv(csv_path)
        # Handle nan/null values elegantly by replacing with empty string before converting to dict
        df = df.fillna("")
    except Exception as e:
        print(f"Failed to read from Scheme CSV ({csv_path}): {e}")
        return
        
    total_records = len(df)
    print(f"Found {total_records} records in {csv_path}...")
    
    successful = 0
    failed = 0
    
    # Iterate through DataFrame and UPSERT each row
    for i, row in df.iterrows():
        # Convert row to dictionary format expected by save_scheme_to_sqlite
        scheme_data = row.to_dict()
        
        # Optionally print progress every 10 records
        if (i + 1) % 10 == 0 or (i + 1) == total_records:
            print(f"Processing record {i + 1}/{total_records}...")
            
        success = save_scheme_to_sqlite(scheme_data)
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
