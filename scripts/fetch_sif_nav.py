import sys
import os

# Add project root to python path to import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime

from config.settings import AMFI_SIF_URL
from services.api_client import fetch_text
from services.parser import extract_schemes
from services.csv_service import save_to_csv
from services.historical_nav_service import update_historical_nav

def main():
    print("Starting SIF NAV pipeline...")
    
    # Step 1: Fetch Text
    text_data = fetch_text(AMFI_SIF_URL)
    
    if text_data:
        # Step 2: Parse to flat list
        schemes = extract_schemes(text_data)
        
        if schemes:
            # Step 3: Save to CSV
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            base_dir = "data/sif/scheme/nav/daily"
            csv_path = f"{base_dir}/{today_str}.csv"
            csv_saved = save_to_csv(schemes, csv_path)
            
            # Step 4: Complete and update history
            if csv_saved:
                update_historical_nav(schemes)
                
                # Cleanup (if downloaded as file by some external script)
                if os.path.exists("SIF_NAVAll.txt"):
                    os.remove("SIF_NAVAll.txt")
                    
                print("Pipeline completed successfully.")
            else:
                print("Pipeline failed at CSV generation.")
        else:
            print("No schemes extracted. Pipeline aborted.")
    else:
        print("Failed to fetch API data. Pipeline aborted.")

if __name__ == "__main__":
    main()
