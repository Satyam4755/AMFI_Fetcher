import re
import json
import logging

def build_scheme_json(api_data, rows):
    xls_data = {}
    for row in rows:
        key_val = None
        val_val = None
        for k in row.keys():
            v = row.get(k)
            if v is None or str(v).strip().lower() == "nan" or str(v).strip() == "":
                continue
            if key_val is None:
                if isinstance(v, str) and not re.match(r'^\d+(\.\d+)?$', str(v).strip()):
                    key_val = str(v).strip()
            elif val_val is None:
                val_val = str(v).strip()
                break
        if key_val and val_val:
            xls_data[key_val] = val_val

    def get_val(possible_keys):
        for k in xls_data.keys():
            cleaned_k = re.sub(r'\s+', ' ', k.lower().strip())
            for pk in possible_keys:
                if pk.lower() in cleaned_k:
                    return xls_data[k]
        return None

    fund_managers = []
    fm_names = {}
    fm_types = {}
    fm_dates = {}
    for k, v in xls_data.items():
        kl = k.lower()
        if "fund manager" in kl:
            match = re.search(r'fund manager (\d+)', kl)
            idx = match.group(1) if match else "1"
            if "name" in kl: fm_names[idx] = v
            elif "type" in kl: fm_types[idx] = v
            elif "from date" in kl: fm_dates[idx] = v
            
    if fm_names:
        for idx, name in fm_names.items():
            if name:
                fund_managers.append({
                    "name": name,
                    "type": fm_types.get(idx, ""),
                    "from": fm_dates.get(idx, "")
                })
    else:
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

    sebi_code_val = get_val(["sebi code", "sebi codes"])
    options_text = get_val(["option names"])
    amfi_text = get_val(["amfi code", "amfi codes"])
    isin_text = get_val(["isin", "isins"])
    rta_text = get_val(["rta code", "rta codes"])
    
    # -------------------------------------------------------------------------
    # STAGE 2 & 3: Normalization Engine and Tokenization
    # -------------------------------------------------------------------------
    def get_canonical_traits(text):
        text_lower = text.lower()
        
        # Determine plan
        plan = "regular"
        if "direct" in text_lower or "dir" in text_lower.split():
            plan = "direct"
            
        # Determine option
        option = "growth"
        if any(k in text_lower for k in ["idcw", "dividend", "div", "payout", "reinvestment", "re-investment", "transfer"]):
            option = "idcw"
            
        # Determine subtype
        subtype = "unknown"
        if option == "idcw":
            if "reinvest" in text_lower:
                subtype = "reinvestment"
            elif "transfer" in text_lower:
                subtype = "transfer"
            elif "payout" in text_lower:
                subtype = "payout"
                
        return {"plan": plan, "option": option, "subtype": subtype if option == "idcw" else None}

    def tokenize_section(text, is_amfi=False, is_isin=False):
        if not text: return []
        text = str(text)
        
        if is_isin:
            text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text, flags=re.IGNORECASE)
        if is_amfi:
            text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)
        
        text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\t]+', '\n', text)
        text = re.sub(r'\s{3,}', '\n', text)
        
        lines = []
        for line in text.split('\n'):
            clean_line = line.strip().strip('-–,.')
            if clean_line:
                lines.append(clean_line)
        return lines

    def extract_code_from_line(line, is_amfi=False, is_isin=False):
        name = line
        code = None
        if is_isin:
            m = re.search(r'(INF[A-Z0-9]{9})', line, re.IGNORECASE)
            if m:
                code = m.group(1)
                name = line.replace(code, '').strip(' -–')
        elif is_amfi:
            m = re.search(r'((?:SIF|S)[-\s]*\d+)', line, re.IGNORECASE)
            if m:
                code = m.group(1)
                name = line.replace(code, '').strip(' -–')
        else:
            # RTA codes: if short, maybe it's just the code
            parts = line.split('-')
            if len(parts) > 1:
                last = parts[-1].strip()
                if len(last) >= 1 and ' ' not in last and not last.isalpha():
                    code = last
                    name = "-".join(parts[:-1]).strip()
            elif len(line) <= 20 and not re.search(r'regular|direct|plan|growth|idcw', line.lower()):
                code = line
                name = ""
                
        return name, code

    def normalize_amfi_code(code):
        if not code: return code
        code = str(code).strip()
        code = re.sub(r'^(?:SIF|S)[-\s]*', '', code, flags=re.IGNORECASE)
        return f"SIF-{code}"

    # -------------------------------------------------------------------------
    # STAGE 4: Independent Extraction
    # -------------------------------------------------------------------------
    options_raw = tokenize_section(options_text)
    amfi_raw = tokenize_section(amfi_text, is_amfi=True)
    isin_raw = tokenize_section(isin_text, is_isin=True)
    rta_raw = tokenize_section(rta_text)

    # Master list of plan objects
    master_plans = []
    
    # 1. Base options
    for opt in options_raw:
        traits = get_canonical_traits(opt)
        master_plans.append({
            "raw_name": opt,
            "traits": traits,
            "amfi_code": None,
            "isin_code": None,
            "rta_code": None
        })

    def merge_codes(raw_lines, code_type):
        is_amfi = code_type == "amfi_code"
        is_isin = code_type == "isin_code"
        
        # If no options exist, populate them from this list (happens in some spreadsheets)
        if not master_plans:
            for line in raw_lines:
                name, code = extract_code_from_line(line, is_amfi=is_amfi, is_isin=is_isin)
                if code and is_amfi: code = normalize_amfi_code(code)
                if not name and not code: continue
                traits = get_canonical_traits(name if name else "")
                master_plans.append({
                    "raw_name": name if name else (code if code else ""),
                    "traits": traits,
                    "amfi_code": code if is_amfi else None,
                    "isin_code": code if is_isin else None,
                    "rta_code": code if not is_amfi and not is_isin else None
                })
            return
            
        # Parse items
        parsed_items = []
        for line in raw_lines:
            name, code = extract_code_from_line(line, is_amfi=is_amfi, is_isin=is_isin)
            if code and is_amfi: code = normalize_amfi_code(code)
            if not name and not code: continue
            traits = get_canonical_traits(name if name else "")
            parsed_items.append({"name": name, "code": code, "traits": traits})
            
        # If it's a single general code (like RTA code for the whole scheme)
        if len(parsed_items) == 1 and not parsed_items[0]["name"] and parsed_items[0]["code"]:
            for mp in master_plans:
                if not mp[code_type]: mp[code_type] = parsed_items[0]["code"]
            return

        # Stage 5: Smart Merging
        # Strategy A: Positional 1-to-1 matching (if counts match exactly)
        if len(parsed_items) == len(master_plans):
            for i, pitem in enumerate(parsed_items):
                if pitem["code"]:
                    master_plans[i][code_type] = pitem["code"]
            return
            
        # Strategy B: Canonical trait matching
        for pitem in parsed_items:
            if not pitem["code"]: continue
            
            # 1. Try exact trait match
            if pitem["name"]:
                candidates = [m for m in master_plans if m["traits"] == pitem["traits"] and not m[code_type]]
                if len(candidates) == 1:
                    candidates[0][code_type] = pitem["code"]
                    continue
                elif len(candidates) > 1:
                    # Match by similarity or just pick first
                    candidates[0][code_type] = pitem["code"]
                    continue
                    
            # 2. Try positional fallback (first empty slot)
            for m in master_plans:
                if not m[code_type]:
                    m[code_type] = pitem["code"]
                    # If this item had a name, maybe we update the master plan's name if it was empty?
                    if pitem["name"] and not m["raw_name"]:
                        m["raw_name"] = pitem["name"]
                        m["traits"] = pitem["traits"]
                    break
            else:
                # 3. Create orphaned
                master_plans.append({
                    "raw_name": pitem["name"] if pitem["name"] else pitem["code"],
                    "traits": pitem["traits"],
                    "amfi_code": pitem["code"] if is_amfi else None,
                    "isin_code": pitem["code"] if is_isin else None,
                    "rta_code": pitem["code"] if not is_amfi and not is_isin else None
                })

    merge_codes(amfi_raw, "amfi_code")
    merge_codes(isin_raw, "isin_code")
    merge_codes(rta_raw, "rta_code")

    # -------------------------------------------------------------------------
    # STAGE 6: Classification
    # -------------------------------------------------------------------------
    plans = {
        "regular": {
            "growth": {},
            "idcw": { "payout": {}, "reinvestment": {}, "transfer": {}, "unknown": {} }
        },
        "direct": {
            "growth": {},
            "idcw": { "payout": {}, "reinvestment": {}, "transfer": {}, "unknown": {} }
        }
    }
    
    primary_amfi_code = None
    for mp in master_plans:
        ptype = mp["traits"]["plan"]
        otype = mp["traits"]["option"]
        stype = mp["traits"]["subtype"]
        
        if otype == "growth":
            ref = plans[ptype]["growth"]
        else:
            ref = plans[ptype]["idcw"][stype]
            
        plan_output = {
            "name": mp["raw_name"]
        }
        if mp["amfi_code"]: plan_output["amfi_code"] = mp["amfi_code"]
        if mp["isin_code"]: plan_output["isin_code"] = mp["isin_code"]
        if mp["rta_code"]: plan_output["rta_code"] = mp["rta_code"]
        
        if not ref.get("name"):
            ref.update(plan_output)
            if not primary_amfi_code and mp["amfi_code"]:
                primary_amfi_code = mp["amfi_code"]
        else:
            if "additional_plans" not in ref: ref["additional_plans"] = []
            ref["additional_plans"].append(plan_output)
            if not primary_amfi_code and mp["amfi_code"]:
                primary_amfi_code = mp["amfi_code"]

    if primary_amfi_code:
        primary_amfi_code = primary_amfi_code.replace(',', ' ').replace(';', ' ').split()[0]

    fund_name_val = get_val(["fund name"]) or api_data.get("Scheme_Name")
    if not sebi_code_val:
        fund_name_safe = str(fund_name_val).upper() if fund_name_val else "UNKNOWN_FUND"
        safe_name = re.sub(r'[^A-Z0-9]', '_', fund_name_safe).strip('_')
        safe_name = re.sub(r'_+', '_', safe_name)
        sebi_code_val = f"TEMP_{safe_name}" if safe_name else "TEMP_UNKNOWN"
        logging.warning(f"Generated TEMP SEBI code: {sebi_code_val} for scheme {fund_name_val}")

    result = {
        "sebi_code": sebi_code_val,
        "fund_name": fund_name_val,
        "fund_type": get_val(["fund type"]) or api_data.get("SchemeType_Desc"),
        "category": get_val(["category as per sebi", "category as per"]) or api_data.get("SchemeCat_Desc"),
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
    
    return result, primary_amfi_code

