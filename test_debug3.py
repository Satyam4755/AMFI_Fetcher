import sys
import os
import json
sys.path.append(os.getcwd())
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls
from services.scheme_parser import build_scheme_json

docs = get_scheme_documents("S-3")
xls_path = download_xls(docs.get("summary_xls_url"))
rows = parse_summary_xls(xls_path)
res = build_scheme_json({}, rows)
print(json.dumps(res, indent=2))
