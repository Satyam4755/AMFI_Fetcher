import pandas as pd
import requests

url = "https://portal.amfiindia.com/spages/SSD_S-29.xls" # Let's try S-29 which was a normal XLS
r = requests.get(url)
with open("temp.xls", "wb") as f:
    f.write(r.content)

xls = pd.ExcelFile("temp.xls")
df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
raw = df.to_dict(orient="records")

print("Keys related to risk or benchmark:")
for row in raw:
    keys = list(row.keys())
    if len(keys) >= 2:
        k = str(row[keys[0]]).strip()
        v = str(row[keys[1]]).strip()
        if any(w in k.lower() for w in ["risk", "benchmark", "tier"]):
            print(f"{k} : {v}")
