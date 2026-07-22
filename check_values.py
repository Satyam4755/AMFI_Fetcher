import pandas as pd
xls = pd.ExcelFile("temp.xls")
df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
raw = df.to_dict(orient="records")
for row in raw[:30]:
    keys = list(row.keys())
    if len(keys) >= 3:
        k = str(row[keys[1]]).strip()
        v = str(row[keys[2]]).strip()
        print(f"'{k}' : '{v}'")
