import sys
import os
sys.path.append(os.getcwd())
from services.scheme_api_client import fetch_scheme_detail
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls
from services.scheme_parser import build_scheme_json

sif_id = "13"
scheme_id = "S-1"
docs = get_scheme_documents(scheme_id)
xls_path = download_xls(docs.get("summary_xls_url"))
rows = parse_summary_xls(xls_path)
xls_data = {}
for row in rows:
    key = row.get("SCHEME SUMMARY DOCUMENT") or row.get("SUMMARY DOCUMENT OF STRATEGIES")
    if not key or not isinstance(key, str): continue
    val = None
    for k, v in row.items():
        if k not in ["Fields", "SCHEME SUMMARY DOCUMENT", "SUMMARY DOCUMENT OF STRATEGIES"] and v is not None:
            if str(v).strip().lower() != "nan": val = str(v).strip(); break
    if val: xls_data[key.strip()] = val
print("XLS KEYS:", list(xls_data.keys()))
