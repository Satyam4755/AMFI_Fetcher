import sys
import os

# Add project root to python path to import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AMFI_SIF_URL, CSV_FILE_PATH
from services.api_client import fetch_text
from services.parser import extract_schemes
from services.csv_service import save_to_csv

def main():
    print("Starting SIF NAV pipeline...")
    
    # Step 1: Fetch Text
    text_data = fetch_text(AMFI_SIF_URL)
    
    if text_data:
        # Step 2: Parse to flat list
        schemes = extract_schemes(text_data)
        
        if schemes:
            # Step 3: Save to CSV
            csv_saved = save_to_csv(schemes, CSV_FILE_PATH)
            
            # Step 4: Complete
            if csv_saved:
                print("Pipeline completed successfully.")
            else:
                print("Pipeline failed at CSV generation.")
        else:
            print("No schemes extracted. Pipeline aborted.")
    else:
        print("Failed to fetch API data. Pipeline aborted.")

if __name__ == "__main__":
    main()
