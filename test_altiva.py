import os
import sys
import pandas as pd
sys.path.append(os.getcwd())
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls

docs = get_scheme_documents("S-13")
xls_path = download_xls(docs.get("summary_xls_url"))
xls = pd.ExcelFile(xls_path)
print("Sheets in S-13:", xls.sheet_names)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    print(f"Sheet {sheet} rows: {len(df)}")
