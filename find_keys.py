import pandas as pd
import glob
import os

all_keys = set()
for path in glob.glob("/Users/smritisoni/Desktop/My_SIF/AMFI_Fetcher_clone/temp/xls/*.xls"):
    try:
        xls = pd.ExcelFile(path)
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            raw = df.to_dict(orient="records")
            for row in raw:
                keys = list(row.keys())
                if len(keys) >= 2:
                    k = str(row[keys[0]]).strip()
                    if "risk" in k.lower():
                        all_keys.add(k)
    except:
        pass
print("Unique Risk Keys:", all_keys)
