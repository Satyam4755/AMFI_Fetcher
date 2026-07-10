import sys
import os
import json
sys.path.append(os.getcwd())
from services.scheme_api_client import fetch_investment_strategies
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls

sif_id = "47"
strats = fetch_investment_strategies(sif_id)
for scheme_info in strats:
    scheme_id = scheme_info.get("scheme_id")
    docs = get_scheme_documents(scheme_id)
    if docs and docs.get("summary_xls_url"):
        xls_path = download_xls(docs.get("summary_xls_url"))
        if xls_path:
            rows = parse_summary_xls(xls_path)
            if rows:
                print(f"--- XLS DATA FOR {scheme_id} ---")
                def default_converter(o):
                    return str(o)
                print(json.dumps(rows[:45], indent=2, default=default_converter))
                break
