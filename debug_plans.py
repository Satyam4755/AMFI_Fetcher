import sys
import os
import json
sys.path.append(os.getcwd())
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls
from services.xls_parser_service import parse_summary_xls
from services.scheme_parser import build_scheme_json

docs = get_scheme_documents("S-1")
xls_path = download_xls(docs.get("summary_xls_url"))
rows = parse_summary_xls(xls_path)

xls_data = {}
for row in rows:
    keys = list(row.keys())
    if len(keys) >= 3:
        key_col = keys[1]
        val_col = keys[2]
        key = row.get(key_col)
        if not key or not isinstance(key, str): continue
        val = row.get(val_col)
        if val is not None and str(val).strip().lower() != "nan":
            xls_data[key.strip()] = str(val).strip()

import re
def get_val(possible_keys):
    for k in xls_data.keys():
        cleaned_k = re.sub(r'\s+', ' ', k.lower().strip())
        for pk in possible_keys:
            if pk.lower() in cleaned_k:
                return xls_data[k]
    return None

print("Option Names:", repr(get_val(["option names"])))
print("AMFI Codes:", repr(get_val(["amfi codes"])))
print("ISINs:", repr(get_val(["isins"])))
print("RTA Codes:", repr(get_val(["rta code"])))

