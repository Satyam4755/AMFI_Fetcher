import os
import glob
import json
import sys

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_dir = os.path.join(base_dir, "data", "sif", "scheme", "details")
    daily_nav_dir = os.path.join(base_dir, "data", "sif", "scheme", "nav", "daily")
    hist_nav_dir = os.path.join(base_dir, "data", "sif", "scheme", "nav", "historical")
    
    files = glob.glob(os.path.join(json_dir, "*.json"))
    
    total_jsons = len(files)
    
    sebi_codes = set()
    amfi_codes = set()
    
    duplicate_sebi_count = 0
    duplicate_amfi_count = 0
    
    plans_missing_amfi = 0
    plans_missing_isin = 0
    plans_missing_rta = 0
    
    failed_validations = []
    
    # 1. Validate JSON Files
    for file in files:
        with open(file, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading JSON: {file}")
                continue
                
        sebi = data.get("sebi_code")
        
        # Verify JSON filename matches SEBI Code normalized
        import re
        if sebi:
            expected_name = str(sebi).lower()
            expected_name = re.sub(r'[^a-z0-9]', '_', expected_name)
            expected_name = re.sub(r'_+', '_', expected_name)
            expected_name = expected_name.strip('_') + ".json"
            
            actual_name = os.path.basename(file)
            if actual_name != expected_name:
                failed_validations.append(f"JSON Filename mismatch: {actual_name} != {expected_name}")

            if sebi in sebi_codes:
                duplicate_sebi_count += 1
            sebi_codes.add(sebi)
        else:
            if not os.path.basename(file).startswith("s_"):
                failed_validations.append(f"Missing sebi_code inside {os.path.basename(file)}")
            
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
    
    # 2. Validate CSV Files
    def validate_csvs(directory):
        if not os.path.exists(directory):
            failed_validations.append(f"Missing directory: {directory}")
            return
        for csv_file in glob.glob(os.path.join(directory, "*.csv")):
            with open(csv_file, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
                if header != "sif_code,nav_date,nav":
                    failed_validations.append(f"Invalid columns in {csv_file}: {header}")
                    
    validate_csvs(daily_nav_dir)
    validate_csvs(hist_nav_dir)
    
    if duplicate_sebi_count > 0:
        failed_validations.append("Duplicate SEBI Codes detected.")
        
    if failed_validations:
        print("\nFAIL: Validation errors found:")
        for err in failed_validations:
            print(f" - {err}")
        sys.exit(1)
        
    print("SUCCESS: JSON & CSV Validation Passed.")

if __name__ == "__main__":
    main()
