from services.xls_parser_service import parse_summary_xls
import json

data = parse_summary_xls("/Users/smritisoni/Desktop/My_SIF/AMFI_Fetcher_clone/temp/xls/SSD_S-27.xls")
if data:
    first_sheet = list(data.values())[0]
    for r in first_sheet[:5]:
        print(r)
