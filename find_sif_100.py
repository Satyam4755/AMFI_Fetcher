import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.scheme_api_client import fetch_all_sifs, fetch_investment_strategies, fetch_scheme_detail
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls
import re

sifs = fetch_all_sifs()
for sif in sifs:
    sif_id = sif.get("SIF_Id")
    strategies = fetch_investment_strategies(sif_id)
    if not strategies: continue
    
    for sch in strategies:
        scheme_id = sch.get("scheme_id")
        docs = get_scheme_documents(scheme_id)
        if docs and docs.get("summary_xls_url"):
            xls_path = download_xls(docs.get("summary_xls_url"))
            if xls_path:
                sheets_data = parse_summary_xls(xls_path)
                for sheet, rows in sheets_data.items():
                    for r in rows:
                        for k, v in r.items():
                            if "SIF-100" in str(v) or "SIF-101" in str(v):
                                print(f"Found in scheme_id {scheme_id} sheet {sheet}")
                                print("Row:", r)
                                sys.exit(0)
