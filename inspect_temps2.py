import json
import glob
import os

def has_any_plans(plans_dict):
    for plan_type, options in plans_dict.items():
        if isinstance(options, dict):
            for option_type, sub_options in options.items():
                if isinstance(sub_options, dict):
                    # Check nested sub_options like idcw -> payout
                    for k, v in sub_options.items():
                        if isinstance(v, dict) and v: # Not empty dict
                            return True
                        elif k == "name" or (isinstance(v, list) and v):
                            return True
                elif sub_options: # List or populated dict
                    return True
    return False

files = glob.glob("/Users/smritisoni/Desktop/My_SIF/AMFI_Fetcher_clone/data/sif/scheme/details/temp_*.json")
for f in files:
    with open(f, 'r') as fp:
        data = json.load(fp)
    
    plans = data.get("plans", {})
    has_plans = has_any_plans(plans)
            
    print(f"--- {os.path.basename(f)} ---")
    print(f"fund_name: {data.get('fund_name')}")
    print(f"scheme_objective: {'Yes' if data.get('scheme_objective') else 'No'}")
    print(f"plans exist: {'Yes' if has_plans else 'No'}")
    print("")

