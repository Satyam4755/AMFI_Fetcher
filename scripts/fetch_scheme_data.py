import sys
import os
import pandas as pd
import logging

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_api_client import fetch_investment_strategies, fetch_scheme_detail
from services.csv_service import save_to_csv

from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls
from services.composite_mapper_service import build_composite_mapping

def main():
    # Setup basic logging so the service loggers will output to console
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    
    print("Starting Scheme Fetch Pipeline...")
    
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
    all_schemes_data = []
    
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
                
                # Pre-fill empty enrichment fields to maintain consistent CSV schema
                scheme_data["sebi_code"] = None
                scheme_data["amfi_codes"] = None
                scheme_data["isin_codes"] = None
                
                # --- DOCUMENT ENRICHMENT PIPELINE ---
                try:
                    docs = get_scheme_documents(scheme_id)
                    if docs and docs.get("summary_xls_url"):
                        xls_url = docs.get("summary_xls_url")
                        xls_path = download_xls(xls_url)
                        
                        if xls_path:
                            rows = parse_summary_xls(xls_path)
                            if rows:
                                mapping = build_composite_mapping(rows)
                                if mapping:
                                    if mapping.get("sebi_code"):
                                        scheme_data["sebi_code"] = mapping.get("sebi_code")
                                        
                                    amfi_mapping = mapping.get("amfi_mapping", [])
                                    if amfi_mapping:
                                        scheme_data["amfi_codes"] = ";".join(
                                            m["amfi_code"] for m in amfi_mapping
                                        )
                                        
                                    isin_mapping = mapping.get("isin_mapping", [])
                                    if isin_mapping:
                                        scheme_data["isin_codes"] = ";".join(
                                            m["isin"] for m in isin_mapping
                                        )
                            
                            # Clean up temporary file
                            if os.path.exists(xls_path):
                                os.remove(xls_path)
                                print(f"     Deleted temporary XLS: {xls_path}")
                    else:
                        print(f"     No document URLs available for scheme_id {scheme_id}.")
                except Exception as e:
                    print(f"     Error enriching data for scheme_id {scheme_id}: {e}")
                # ------------------------------------
                
                all_schemes_data.append(scheme_data)
            else:
                print(f"     No valid data returned for scheme_id {scheme_id}.")
            
    # Save everything into data/sif_scheme.csv
    print(f"\nCollected a total of {len(all_schemes_data)} scheme detail records.")
    save_to_csv(all_schemes_data, "data/sif_scheme.csv")
            
    print("\nFetch Pipeline Completed")
    print("-" * 20)
    print(f"Total SIFs Processed       : {total_sifs}")
    print(f"Total Schemes Discovered   : {total_schemes_discovered}")
    print(f"Total Details Fetched      : {len(all_schemes_data)}")

if __name__ == "__main__":
    main()
