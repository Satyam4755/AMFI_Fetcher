import os
import json
import pandas as pd
from services.scheme_api_client import fetch_investment_strategies, fetch_scheme_detail
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls

nav_dir = "data/sif/nav"
import glob
csv_files = glob.glob(os.path.join(nav_dir, "????-??-??.csv"))
if not csv_files:
    print("No NAV files.")
    sys.exit(0)
latest_csv_path = sorted(csv_files)[-1]
df = pd.read_csv(latest_csv_path)
sif_codes = df['sif_code'].dropna().unique().tolist()
unique_sifs = [str(code).replace("SIF-", "") for code in sif_codes]

for sif_val in unique_sifs:
    sif_id = str(int(float(sif_val)))
    strategies = fetch_investment_strategies(sif_id)
    if strategies:
        for strat in strategies:
            scheme_name = strat.get("scheme_name", "")
            scheme_id = strat.get("scheme_id", "")
            if "altiva" in scheme_name.lower():
                print(f"Found Altiva! SIF_ID: {sif_id}, Scheme ID: {scheme_id}, Name: {scheme_name}")
