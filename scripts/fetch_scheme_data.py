import sys
import os
import pandas as pd
import logging

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_api_client import fetch_investment_strategies, fetch_scheme_detail, fetch_all_sifs
from services.scheme_parser import build_scheme_json
from services.scheme_json_service import save_scheme_to_json
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls

def main():
    # Setup basic logging so the service loggers will output to console
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    
    print("Starting Scheme Fetch Pipeline...")
    
    # Fetch all SIFs directly from API
    sif_list = fetch_all_sifs()
    if not sif_list:
        print("Failed to fetch SIFs from AMFI API.")
        return
        
    total_sifs = len(sif_list)
    print(f"Found {total_sifs} total SIFs...")
    
    total_schemes_discovered = 0
    total_json_files = 0
    
    for i, sif_info in enumerate(sif_list, 1):
        sif_id = str(sif_info.get("SIF_Id", ""))
        sif_name = sif_info.get("SIF_Name", "Unknown")
        if not sif_id: continue
        
        print(f"\nProcessing SIF {i}/{total_sifs} (sif_id: {sif_id}, {sif_name})...")
        
        strategies_response = fetch_investment_strategies(sif_id)
        schemes = strategies_response if isinstance(strategies_response, list) else []
        
        if not schemes:
            print(f"No investment strategies found for SIF {sif_id}.")
            continue
            
        print(f"Discovered {len(schemes)} API schemes for SIF {sif_id}.")
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
                            # parse_summary_xls now returns { sheet_name: rows }
                            sheets_data = parse_summary_xls(xls_path)
                            
                            if sheets_data:
                                for sheet_name, rows in sheets_data.items():
                                    if not rows: continue
                                    
                                    # Build nested JSON structure for this specific sheet
                                    nested_scheme_data, primary_amfi_code = build_scheme_json(scheme_data, rows)
                                    
                                    # Format filename based on primary AMFI code (e.g., SIF-107 -> sif_107)
                                    fallback_used = False
                                    if primary_amfi_code:
                                        safe_name = str(primary_amfi_code).lower().replace("-", "_")
                                    else:
                                        fallback_used = True
                                        sebi = nested_scheme_data.get("sebi_code", scheme_id)
                                        safe_name = "sebi_" + str(sebi).lower().replace("/", "_")
                                        
                                    if save_scheme_to_json(safe_name, nested_scheme_data):
                                        total_json_files += 1
                                        
                                        print("\nValidation:")
                                        print(f"JSON filename: {safe_name}.json")
                                        print(f"Primary AMFI: {primary_amfi_code}")
                                        print(f"Fallback used: {'Yes' if fallback_used else 'No'}\n")
                            
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
