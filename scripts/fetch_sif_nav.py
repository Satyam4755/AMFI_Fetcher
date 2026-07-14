import sys
import os
import glob
import csv
import datetime

# Add project root to python path to import modules properly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import AMFI_SIF_URL
from services.api_client import fetch_text
from services.parser import extract_schemes
from services.csv_service import save_to_csv
from services.historical_nav_service import update_historical_nav

def get_latest_stored_nav_date(daily_nav_dir):
    files = glob.glob(os.path.join(daily_nav_dir, "*.csv"))
    if not files:
        return None
    # Sort files by name to get the latest (works for both YYYY-MM-DD and YYYYMMDD)
    latest_file = sorted(files)[-1]
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            first_row = next(reader, None)
            if first_row and 'nav_date' in first_row:
                return first_row['nav_date']
    except Exception as e:
        print(f"Error reading {latest_file}: {e}")
    return None

def main():
    print("Starting SIF NAV pipeline...")
    
    # Step 1: Fetch Text
    text_data = fetch_text(AMFI_SIF_URL)
    
    if text_data:
        # Step 2: Parse to flat list
        schemes = extract_schemes(text_data)
        
        if schemes:
            base_dir = "data/sif/scheme/nav/daily"
            os.makedirs(base_dir, exist_ok=True)
            
            latest_fetched_nav_date = schemes[0].get("nav_date") if len(schemes) > 0 else None
            latest_stored_nav_date = get_latest_stored_nav_date(base_dir)
            
            if latest_fetched_nav_date and latest_fetched_nav_date == latest_stored_nav_date:
                print("No new NAV published. Daily snapshot skipped.")
                return
                
            # Step 3: Save to CSV using the new YYYYMMDD format
            today_str = datetime.date.today().strftime("%Y%m%d")
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
