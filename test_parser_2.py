from services.scheme_parser import build_scheme_json
import json

rows = [
    {"0": "1", "1": "AMFI Codes", "2": "SIF-9 - Altiva Hybrid Long-Short Fund Direct Plan Growth\nSIF-10 - Altiva Hybrid Long-Short Fund Direct Plan - IDCW Payout"}
]
res, primary = build_scheme_json({}, rows)
print(json.dumps(res, indent=2))
print("Primary:", primary)
