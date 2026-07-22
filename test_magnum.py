import pandas as pd
import json

dfs = pd.read_html("https://portal.amfiindia.com/spages/SSD_S-4.xls", flavor='lxml')
print(f"Found {len(dfs)} tables")

df = dfs[0]
print(df.head(20))

raw_list = df.to_dict(orient="records")
cleaned_list = []
for row in raw_list:
    cleaned_row = {}
    for k, v in row.items():
        if pd.isna(v):
            cleaned_row[k] = None
        else:
            cleaned_row[k] = v
    cleaned_list.append(cleaned_row)

print("First few rows:")
for r in cleaned_list[:5]:
    print(r)
