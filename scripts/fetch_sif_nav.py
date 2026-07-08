import sys
import os

# Add project root to python path to import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AMFI_SIF_URL, CSV_FILE_PATH, DB_FILE_PATH, TABLE_NAME
from services.api_client import fetch_json
from services.parser import extract_schemes
from services.csv_service import save_to_csv
from services.sqlite_service import save_to_sqlite

def main():
    print("Starting SIF NAV pipeline...")
    
    # Step 1: Fetch JSON
    json_data = fetch_json(AMFI_SIF_URL)
    
    if json_data:
        # Step 2: Parse to flat list
        schemes = extract_schemes(json_data)
        
        if schemes:
            # Step 3: Save to CSV
            csv_saved = save_to_csv(schemes, CSV_FILE_PATH)
            
            # Step 4: Save to SQLite
            if csv_saved:
                save_to_sqlite(CSV_FILE_PATH, DB_FILE_PATH, TABLE_NAME)
                print("Pipeline completed successfully.")
            else:
                print("Pipeline failed at CSV generation.")
        else:
            print("No schemes extracted. Pipeline aborted.")
    else:
        print("Failed to fetch API data. Pipeline aborted.")

if __name__ == "__main__":
    main()
