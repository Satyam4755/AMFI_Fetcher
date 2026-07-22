import json
import glob
import os

files = glob.glob("/Users/smritisoni/Desktop/My_SIF/AMFI_Fetcher_clone/data/sif/scheme/details/temp_*.json")
for f in files:
    with open(f, 'r') as fp:
        data = json.load(fp)
    
    plans = data.get("plans", [])
    has_plans = len(plans) > 0
    sif_codes = []
    isins = []
    for plan in plans:
        if plan.get("sif_code"):
            sif_codes.append(plan["sif_code"])
        if plan.get("isin"):
            isins.append(plan["isin"])
            
    print(f"--- {os.path.basename(f)} ---")
    print(f"fund_name: {data.get('fund_name')}")
    print(f"fund_type: {data.get('fund_type')}")
    print(f"category: {data.get('category')}")
    print(f"riskometer_at_launch: {data.get('riskometer_at_launch')}")
    print(f"scheme_objective: {'Yes' if data.get('scheme_objective') else 'No'}")
    print(f"benchmark: {data.get('benchmark_tier_1')}")
    print(f"plans count: {len(plans)}")
    print(f"SIF codes found: {sif_codes}")
    print(f"ISINs found: {isins}")
    print("")

