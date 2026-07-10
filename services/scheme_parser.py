import re
import json

def build_scheme_json(api_data, rows):
    """
    Converts raw API data and XLS rows into a deeply nested JSON-serializable dictionary.
    """
    xls_data = {}
    if rows:
        for row in rows:
            keys = list(row.keys())
            if len(keys) >= 3:
                key_col = keys[1]
                val_col = keys[2]
                
                key = row.get(key_col)
                if not key or not isinstance(key, str):
                    continue
                
                val = row.get(val_col)
                if val is not None and str(val).strip().lower() != "nan":
                    xls_data[key.strip()] = str(val).strip()

    def get_val(possible_keys):
        for k in xls_data.keys():
            cleaned_k = re.sub(r'\s+', ' ', k.lower().strip())
            for pk in possible_keys:
                if pk.lower() in cleaned_k:
                    return xls_data[k]
        print(f"Missing expected column name for: {possible_keys[0]}")
        return None

    # Helper to parse fund managers
    fund_managers = []
    
    # Check if managers are split into multiple rows like "Fund Manager 1 - Name"
    fm_names = {}
    fm_types = {}
    fm_dates = {}
    for k, v in xls_data.items():
        kl = k.lower()
        if "fund manager" in kl:
            # Extract number if it exists
            match = re.search(r'fund manager (\d+)', kl)
            idx = match.group(1) if match else "1"
            
            if "name" in kl: fm_names[idx] = v
            elif "type" in kl: fm_types[idx] = v
            elif "from date" in kl: fm_dates[idx] = v
            
    # Combine them
    if fm_names:
        for idx, name in fm_names.items():
            if name:
                fund_managers.append({
                    "name": name,
                    "type": fm_types.get(idx, ""),
                    "from": fm_dates.get(idx, "")
                })
    else:
        # Fallback to single row split by semicolon (older format)
        fm_names_raw = get_val(["fund manager name"]) or ""
        fm_types_raw = get_val(["fund manager type"]) or ""
        fm_dates_raw = get_val(["fund manager from date"]) or ""
        
        if fm_dates_raw and fm_names_raw:
            manager_entries = re.split(r';|\band\b', fm_dates_raw)
            for entry in manager_entries:
                entry = entry.strip()
                if not entry: continue
                parts = entry.split("-", 1)
                name = parts[0].strip()
                from_date = parts[1].strip() if len(parts) > 1 else ""
                fund_managers.append({
                    "name": name,
                    "type": fm_types_raw,
                    "from": from_date
                })
        else:
            print("Missing expected column name for: fund_managers")

    # Helper to parse plans
    plans = {
        "regular": {
            "growth": {},
            "idcw": {
                "payout": {},
                "reinvestment": {},
                "transfer": {}
            }
        },
        "direct": {
            "growth": {},
            "idcw": {
                "payout": {},
                "reinvestment": {},
                "transfer": {}
            }
        }
    }

    def parse_plan_lines(text, code_key):
        if not text:
            return
            
        # Check if text is just a single general code (no newlines, no plan names inside)
        if '\n' not in text and 'plan' not in text.lower() and 'option' not in text.lower():
            code_val = text.strip()
            # Apply this code to all currently active plans
            for p_type in ["regular", "direct"]:
                if "name" in plans[p_type]["growth"]:
                    plans[p_type]["growth"][code_key] = code_val
                for subtype in ["payout", "reinvestment", "transfer"]:
                    if "name" in plans[p_type]["idcw"][subtype]:
                        plans[p_type]["idcw"][subtype][code_key] = code_val
            return

        for line in text.split('\n'):
            line = line.strip().replace('–', '-')
            if not line: continue
            
            # Remove leading numbering like "1."
            line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
            
            code = None
            name = line
            parts = line.split('-')
            if len(parts) > 1:
                last_part = parts[-1].strip()
                if re.match(r'^(SIF|INF|S)\S*', last_part, re.IGNORECASE) or ' ' not in last_part:
                    if len(parts) >= 3 and re.match(r'^(SIF|S)\b', parts[-2].strip() + "-" + last_part, re.IGNORECASE):
                        code = parts[-2].strip() + "-" + last_part
                        name = "-".join(parts[:-2]).strip()
                    else:
                        code = last_part
                        name = "-".join(parts[:-1]).strip()
                        
            name_lower = name.lower()
            plan_type = "direct" if "direct" in name_lower else "regular"
            if "growth" in name_lower:
                ref = plans[plan_type]["growth"]
                category = "growth"
                subtype = None
            else:
                if "reinvest" in name_lower: subtype = "reinvestment"
                elif "transfer" in name_lower: subtype = "transfer"
                else: subtype = "payout"
                ref = plans[plan_type]["idcw"][subtype]
                category = "idcw"
                
            if "name" not in ref or len(name) > len(ref["name"]):
                ref["name"] = name
                
            if code_key and code:
                ref[code_key] = code

            # Temporarily print the mapped plan as requested for debugging
            if not getattr(build_scheme_json, "has_printed_plans", False):
                print(f"\nPlan:")
                print(f"Name: {name}")
                if code_key == "amfi_code": print(f"AMFI: {code}")
                if code_key == "isin_code": print(f"ISIN: {code}")
                if code_key == "rta_code": print(f"RTA: {code}")
                if subtype:
                    print(f"Mapped to:\n{plan_type} -> {category} -> {subtype}")
                else:
                    print(f"Mapped to:\n{plan_type} -> {category}")

    # Parse all potential plan sources
    sebi_code_val = get_val(["sebi codes"])
    if not getattr(build_scheme_json, "has_printed_plans", False):
        print(f"\nProcessing scheme:\n{sebi_code_val}")
        
    parse_plan_lines(get_val(["option names"]), None)
    parse_plan_lines(get_val(["amfi codes"]), "amfi_code")
    parse_plan_lines(get_val(["isins"]), "isin_code")
    parse_plan_lines(get_val(["rta code"]), "rta_code")
    
    build_scheme_json.has_printed_plans = True

    # Construct the final nested payload
    result = {
        "sebi_code": sebi_code_val,
        "fund_name": get_val(["fund name"]),
        "fund_type": get_val(["fund type"]),
        "category": get_val(["category as per sebi", "category as per"]),
        "potential_risk_class": get_val(["potential risk class"]),
        "face_value": get_val(["face value"]),
        "listing_details": get_val(["listing details"]),
        
        "plans": plans,
        "fund_managers": fund_managers,
        
        "investment_limits": {
            "minimum_application_amount": get_val(["minimum application amount"]),
            "application_multiple": get_val(["minimum application amount in multiples", "application multiple"]),
            "minimum_additional_amount": get_val(["minimum additional amount"]),
            "additional_multiple": get_val(["minimum additional amount in multiples", "additional multiple"]),
            "minimum_redemption_amount": get_val(["minimum redemption amount in rs", "minimum redemption amount"]),
            "minimum_redemption_units": get_val(["minimum redemption amount in units"])
        },
        
        "exit_load": get_val(["exit load"]),
        "registrar": get_val(["registrar"]),
        "custodian": get_val(["custodian"]),
        "auditor": get_val(["auditor"])
    }
    
    # Print first grouped scheme object before JSON generation
    # Use a global flag to only print once
    if not getattr(build_scheme_json, "has_printed", False):
        print("\nGrouped scheme:")
        print(json.dumps(result, indent=2))
        build_scheme_json.has_printed = True
    
    return result
