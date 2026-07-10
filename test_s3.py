import pandas as pd
xls = pd.ExcelFile("/Users/smritisoni/Desktop/AMFI_Fetcher/temp/xls/SSD_S-3.xls")
print("Sheets in S-3:", xls.sheet_names)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    print(f"Sheet {sheet} rows: {len(df)}")
