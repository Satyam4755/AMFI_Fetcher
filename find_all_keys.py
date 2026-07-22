import pandas as pd
import requests
import json
with open('data/sif/scheme/summary.json') as f:
    data = json.load(f)

unique_keys = set()
for scheme in data:
    sid = scheme['scheme_id']
    url = f"https://portal.amfiindia.com/spages/SSD_{sid}.xls"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and not r.content.startswith(b"<"):
            with open("temp.xls", "wb") as f:
                f.write(r.content)
            xls = pd.ExcelFile("temp.xls")
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet)
                raw = df.to_dict(orient="records")
                for row in raw:
                    keys = list(row.keys())
                    if len(keys) >= 2:
                        k = str(row[keys[0]]).strip()
                        unique_keys.add(k)
                    if len(keys) >= 3:
                        k = str(row[keys[1]]).strip()
                        unique_keys.add(k)
    except Exception as e:
        pass

risk_keys = [k for k in unique_keys if 'risk' in k.lower()]
print("RISK KEYS FOUND ACROSS ALL SCHEMES:")
for k in risk_keys:
    print(k)
