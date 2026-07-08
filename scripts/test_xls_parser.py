import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.xls_parser_service import parse_summary_xls

rows = parse_summary_xls("temp/xls/SSD_S-3.xls")

print(f"Total rows: {len(rows)}")

for i, row in enumerate(rows):
    print(f"\nRow {i+1}")
    print(row)