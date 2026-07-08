import sys
import os
import pandas as pd

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_api_client import fetch_investment_strategies, fetch_scheme_detail
from services.scheme_insert_service import save_scheme_to_sqlite
from services.scheme_sqlite_service import create_tables

def main():
    print("Starting Scheme Pipeline...")
    
    # Ensure database schema exists
    create_tables()
    
    # Read unique sifIds from the NAV CSV
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sif_nav.csv")
    try:
        df = pd.read_csv(csv_path)
        # Drop NaNs and get unique values
        unique_sifs = df['sifId'].dropna().unique().tolist()
    except Exception as e:
        print(f"Failed to read from NAV CSV ({csv_path}): {e}")
        return
        
    total_sifs = len(unique_sifs)
    print(f"Found {total_sifs} unique SIFs in NAV data...")
    
    total_schemes_discovered = 0
    successful = 0
    failed = 0
    
    for i, sif_val in enumerate(unique_sifs, 1):
        # Convert float to int string if needed
        sif_id = str(int(sif_val)) if isinstance(sif_val, float) else str(sif_val)
        
        print(f"\nProcessing SIF {i}/{total_sifs} (sif_id: {sif_id})...")
        
        # 1. Fetch investment strategies for this SIF
        strategies_response = fetch_investment_strategies(sif_id)
        schemes = strategies_response if isinstance(strategies_response, list) else []
        
        if not schemes:
            print(f"No investment strategies found for SIF {sif_id}.")
            continue
            
        print(f"Discovered {len(schemes)} schemes for SIF {sif_id}.")
        total_schemes_discovered += len(schemes)
        
        # 2. For each scheme, fetch the details and save to SQLite
        for scheme_info in schemes:
            scheme_id = scheme_info.get("scheme_id")
            if not scheme_id:
                continue
                
            print(f"  -> Fetching detail for scheme_id: {scheme_id}...")
            json_response = fetch_scheme_detail(sif_id, scheme_id)
            
            data_list = json_response.get("data", []) if json_response and isinstance(json_response, dict) else []
            
            if data_list and len(data_list) > 0:
                scheme_data = data_list[0]
                success = save_scheme_to_sqlite(scheme_data)
                
                if success:
                    successful += 1
                else:
                    failed += 1
            else:
                print(f"     No valid data returned for scheme_id {scheme_id}.")
                failed += 1
            
    print("\nPipeline Completed")
    print("-" * 20)
    print(f"Total SIFs Processed       : {total_sifs}")
    print(f"Total Schemes Discovered   : {total_schemes_discovered}")
    print(f"Successful Inserts         : {successful}")
    print(f"Failed Inserts             : {failed}")

if __name__ == "__main__":
    main()
