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
    skipped_schemes = {}
    
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
                        
                        def save_fallback_json(reason):
                            skipped_schemes[scheme_id] = f"Basic JSON Generated ({reason})"
                            print(f"     {reason}. Generating basic JSON from API data for {scheme_id}...")
                            
                            nested_scheme_data, _ = build_scheme_json(scheme_data, [])
                            nested_scheme_data["sif_name"] = sif_name
                            
                            sebi = nested_scheme_data.get("sebi_code")
                            if not sebi:
                                sebi = scheme_id
                                
                            import re
                            safe_name = str(sebi).lower()
                            safe_name = re.sub(r'[^a-z0-9]', '_', safe_name)
                            safe_name = re.sub(r'_+', '_', safe_name)
                            safe_name = safe_name.strip('_')
                                
                            if save_scheme_to_json(safe_name, nested_scheme_data):
                                nonlocal total_json_files
                                total_json_files += 1
                                print("\nValidation (Basic):")
                                print(f"JSON filename: {safe_name}.json")
                                print(f"SEBI used: {sebi}\n")
                        
                        if xls_path:
                            # parse_summary_xls now returns { sheet_name: rows }
                            sheets_data = parse_summary_xls(xls_path)
                            
                            if not sheets_data:
                                save_fallback_json("Parsed sheets returned empty")
                            else:
                                for sheet_name, rows in sheets_data.items():
                                    if not rows: continue
                                    
                                    # Build nested JSON structure for this specific sheet
                                    nested_scheme_data, primary_amfi_code = build_scheme_json(scheme_data, rows)

                                    nested_scheme_data["sif_name"] = sif_name
                                    # Format filename based on SEBI code
                                    # Fallback to scheme_id if sebi_code is somehow completely missing
                                    sebi = nested_scheme_data.get("sebi_code")
                                    if not sebi:
                                        sebi = scheme_id
                                        
                                    import re
                                    # Normalization algorithm:
                                    # lowercase -> replace non-alphanumeric with _ -> collapse _ -> strip _
                                    safe_name = str(sebi).lower()
                                    safe_name = re.sub(r'[^a-z0-9]', '_', safe_name)
                                    safe_name = re.sub(r'_+', '_', safe_name)
                                    safe_name = safe_name.strip('_')
                                        
                                    if save_scheme_to_json(safe_name, nested_scheme_data):
                                        total_json_files += 1
                                        
                                        print("\nValidation:")
                                        print(f"JSON filename: {safe_name}.json")
                                        print(f"SEBI used: {sebi}\n")
                            
                            # Clean up temporary file
                            if os.path.exists(xls_path):
                                os.remove(xls_path)
                                print(f"     Deleted temporary XLS: {xls_path}")
                        else:
                            save_fallback_json("Summary XLS not found or invalid format")
                    else:
                        save_fallback_json("No document URLs available")
                except Exception as e:
                    skipped_schemes[scheme_id] = f"Error parsing data: {e}"
                    print(f"     Error enriching data for scheme_id {scheme_id}: {e}")
                # ------------------------------------
            else:
                skipped_schemes[scheme_id] = "No valid data from API"
                print(f"     No valid data returned for scheme_id {scheme_id}.")
            
    print("\nFetch Pipeline Completed")
    print("-" * 20)
    print("--- Validation Report ---")
    print(f"Total SIFs Processed       : {total_sifs}")
    print(f"Total Schemes Discovered   : {total_schemes_discovered}")
    print(f"Total Details Fetched      : {total_json_files}")
    print(f"Total Skipped/Fallback     : {len(skipped_schemes)}")
    print("\nSkipped Schemes / Fallback Reasons:")
    for sch_id, reason in skipped_schemes.items():
        print(f" - {sch_id}: {reason}")
        
    # Final Reconciliation
    # When falling back, we increment total_json_files AND record it in skipped_schemes to show it wasn't fully parsed.
    # Therefore, we only add the TRUE skipped schemes (the ones that threw errors) to the reconciliation.
    true_skipped = len([r for r in skipped_schemes.values() if "Basic JSON Generated" not in r])
    if total_schemes_discovered == (total_json_files + true_skipped):
        print("\nSUCCESS: Total counts reconcile correctly.")
    else:
        print("\nWARNING: Counts do not reconcile. Some schemes disappeared silently!")

if __name__ == "__main__":
    main()
