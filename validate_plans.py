import json
import glob
import os

json_dir = "data/sif/schemes"
files = glob.glob(os.path.join(json_dir, "*.json"))

total_schemes = len(files)
total_plans = 0
growth_plans = 0
idcw_payout = 0
idcw_reinvestment = 0
idcw_transfer = 0
unmapped_plans = 0

for file in files:
    with open(file, 'r') as f:
        data = json.load(f)
        plans = data.get("plans", {})
        
        for p_type in ["regular", "direct"]:
            pt = plans.get(p_type, {})
            
            if pt.get("growth", {}).get("name"):
                total_plans += 1
                growth_plans += 1
                
            idcw = pt.get("idcw", {})
            if idcw.get("payout", {}).get("name"):
                total_plans += 1
                idcw_payout += 1
            if idcw.get("reinvestment", {}).get("name"):
                total_plans += 1
                idcw_reinvestment += 1
            if idcw.get("transfer", {}).get("name"):
                total_plans += 1
                idcw_transfer += 1

print(f"Schemes processed: {total_schemes}")
print(f"Plans detected: {total_plans}")
print(f"Growth plans: {growth_plans}")
print(f"IDCW payout: {idcw_payout}")
print(f"IDCW reinvestment: {idcw_reinvestment}")
print(f"IDCW transfer: {idcw_transfer}")
print(f"Unmapped plans: {unmapped_plans}")
