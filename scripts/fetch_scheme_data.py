import sys
import os
import pandas as pd
import logging

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_api_client import fetch_investment_strategies, fetch_scheme_detail
from services.scheme_parser import build_scheme_json
from services.scheme_json_service import save_scheme_to_json
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls

def main():
    # Setup basic logging so the service loggers will output to console
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    
    print("Starting Scheme Fetch Pipeline...")
    
    # Read unique sifIds from the latest NAV CSV
    nav_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sif", "nav")
    
    import glob
    csv_files = glob.glob(os.path.join(nav_dir, "????-??-??.csv"))
    if not csv_files:
        print(f"Failed to find any daily NAV CSV in {nav_dir}")
        return
        
    latest_csv_path = sorted(csv_files)[-1]
    print(f"Using NAV file: {latest_csv_path}")
    
    try:
        df = pd.read_csv(latest_csv_path)
        # In the new NAV format, the column is 'sif_code' (e.g. SIF-120), we need to extract the number.
        if 'sif_code' in df.columns:
            sif_codes = df['sif_code'].dropna().unique().tolist()
            unique_sifs = [str(code).replace("SIF-", "") for code in sif_codes]
        elif 'sifId' in df.columns:
            unique_sifs = df['sifId'].dropna().unique().tolist()
        else:
            print("Could not find sif_code or sifId column in NAV CSV.")
            return
    except Exception as e:
        print(f"Failed to read from NAV CSV ({latest_csv_path}): {e}")
        return
        
    total_sifs = len(unique_sifs)
    print(f"Found {total_sifs} unique SIFs in NAV data...")
    
    total_schemes_discovered = 0
    total_json_files = 0
    
    for i, sif_val in enumerate(unique_sifs, 1):
        sif_id = str(int(sif_val)) if isinstance(sif_val, float) else str(sif_val)
        
        print(f"\nProcessing SIF {i}/{total_sifs} (sif_id: {sif_id})...")
        
        strategies_response = fetch_investment_strategies(sif_id)
        schemes = strategies_response if isinstance(strategies_response, list) else []
        
        if not schemes:
            print(f"No investment strategies found for SIF {sif_id}.")
            continue
            
        print(f"Discovered {len(schemes)} schemes for SIF {sif_id}.")
        total_schemes_discovered += len(schemes)
        
        for scheme_info in schemes:
            scheme_id = scheme_info.get("scheme_id")
            if not scheme_id:
                continue
                
            print(f"  -> Fetching detail for scheme_id: {scheme_id}...")
            json_response = fetch_scheme_detail(sif_id, scheme_id)
            
            data_list = json_response.get("data", []) if json_response and isinstance(json_response, dict) else []
            
            if data_list and len(data_list) > 0:
                scheme_data = data_list[0]
                
                # --- DOCUMENT ENRICHMENT PIPELINE ---
                try:
                    docs = get_scheme_documents(scheme_id)
                    if docs and docs.get("summary_xls_url"):
                        xls_url = docs.get("summary_xls_url")
                        xls_path = download_xls(xls_url)
                        
                        if xls_path:
                            rows = parse_summary_xls(xls_path)
                            if rows:
                                # Build nested JSON structure
                                nested_scheme_data = build_scheme_json(scheme_data, rows)
                                
                                # Format filename based on scheme_id (e.g., S-22 -> sif_22)
                                safe_scheme_id = str(scheme_id).lower()
                                if safe_scheme_id.startswith("s-"):
                                    safe_scheme_id = safe_scheme_id.replace("s-", "sif_")
                                    
                                if save_scheme_to_json(safe_scheme_id, nested_scheme_data):
                                    total_json_files += 1
                            
                            # Clean up temporary file
                            if os.path.exists(xls_path):
                                os.remove(xls_path)
                                print(f"     Deleted temporary XLS: {xls_path}")
                    else:
                        print(f"     No document URLs available for scheme_id {scheme_id}.")
                except Exception as e:
                    print(f"     Error enriching data for scheme_id {scheme_id}: {e}")
                # ------------------------------------
            else:
                print(f"     No valid data returned for scheme_id {scheme_id}.")
            
    print("\nFetch Pipeline Completed")
    print("-" * 20)
    print(f"Total SIFs Processed       : {total_sifs}")
    print(f"Total Schemes Discovered   : {total_schemes_discovered}")
    print(f"Total Details Fetched      : {total_json_files}")

if __name__ == "__main__":
    main()
