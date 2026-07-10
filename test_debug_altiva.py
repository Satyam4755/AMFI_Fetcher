import json
from services.xls_parser_service import parse_summary_xls
from services.scheme_document_service import get_scheme_documents
from services.xls_download_service import download_xls

docs = get_scheme_documents("S-3")
if docs and docs.get("summary_xls_url"):
    xls_path = download_xls(docs.get("summary_xls_url"))
    if xls_path:
        sheets = parse_summary_xls(xls_path)
        for sheet, rows in sheets.items():
            print(f"Sheet: {sheet}")
            for row in rows:
                print(row)
