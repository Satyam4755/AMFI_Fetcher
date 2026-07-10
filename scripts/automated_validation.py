import os
import glob
import json
import sys

def main():
    json_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sif", "schemes")
    files = glob.glob(os.path.join(json_dir, "*.json"))
    
    total_jsons = len(files)
    
    sebi_codes = set()
    amfi_codes = set()
    
    duplicate_sebi_count = 0
    duplicate_amfi_count = 0
    
    plans_missing_amfi = 0
    plans_missing_isin = 0
    plans_missing_rta = 0
    
    for file in files:
        with open(file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading JSON: {file}")
                continue
                
        sebi = data.get("sebi_code")
        if sebi:
            if sebi in sebi_codes:
                duplicate_sebi_count += 1
            sebi_codes.add(sebi)
            
        plans = data.get("plans", {})
        
        for p_type in ["regular", "direct"]:
            pt = plans.get(p_type, {})
            
            # Check growth
            growth = pt.get("growth", {})
            if growth.get("name"):
                amfi = growth.get("amfi_code")
                if not amfi: plans_missing_amfi += 1
                else:
                    if amfi in amfi_codes: duplicate_amfi_count += 1
                    amfi_codes.add(amfi)
                if not growth.get("isin_code"): plans_missing_isin += 1
                if not growth.get("rta_code"): plans_missing_rta += 1
                
            # Check IDCW subtypes
            idcw = pt.get("idcw", {})
            for subtype in ["payout", "reinvestment", "transfer"]:
                st = idcw.get(subtype, {})
                if st.get("name"):
                    amfi = st.get("amfi_code")
                    if not amfi: plans_missing_amfi += 1
                    else:
                        if amfi in amfi_codes: duplicate_amfi_count += 1
                        amfi_codes.add(amfi)
                    if not st.get("isin_code"): plans_missing_isin += 1
                    if not st.get("rta_code"): plans_missing_rta += 1

    print("\n--- Validation Report ---")
    print(f"JSON Files Generated: {total_jsons}")
    print(f"Duplicate SEBI Codes: {duplicate_sebi_count}")
    print(f"Duplicate AMFI Codes: {duplicate_amfi_count}")
    print(f"Plans Missing AMFI Code: {plans_missing_amfi}")
    print(f"Plans Missing ISIN: {plans_missing_isin}")
    print(f"Plans Missing RTA: {plans_missing_rta}")
    
    if duplicate_sebi_count > 0:
        print("FAIL: Duplicate SEBI Codes detected.")
        sys.exit(1)
        
    print("SUCCESS: JSON Validation Passed.")

if __name__ == "__main__":
    main()
