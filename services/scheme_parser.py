import re
import json

def build_scheme_json(api_data, rows):
    """
    Converts raw API data and XLS rows into a deeply nested JSON-serializable dictionary.
    """
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

    extracted_plans = {}
    
    def normalize_name(name):
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def normalize_amfi_code(code):
        if not code: return code
        code = str(code).strip()
        code = re.sub(r'^(?:SIF|S)[-\s]*', '', code, flags=re.IGNORECASE)
        return f"SIF-{code}"
        
    def extract_embedded_code(line, is_amfi=False, is_isin=False):
        # Extracts code if it's appended at the end or beginning
        code = None
        name = line
        parts = line.split('-')
        
        if is_isin:
            # Look for ISIN pattern anywhere in the line
            m = re.search(r'(INF[A-Z0-9]{9})', line)
            if m:
                code = m.group(1)
                name = line.replace(code, '').strip(' -')
                return name, code

        if is_amfi:
            # Check for embedded SIF codes
            m = re.search(r'((?:SIF|S)[-\s]*\d+)', line, re.IGNORECASE)
            if m:
                code = m.group(1)
                name = line.replace(code, '').strip(' -')
                return name, normalize_amfi_code(code)
            
        if len(parts) > 1:
            last_part = parts[-1].strip()
            first_part = parts[0].strip()
            if ' ' not in last_part and len(last_part) >= 1 and not last_part.isalpha():
                if len(parts) >= 3 and ' ' not in parts[-2].strip() and re.match(r'^(SIF|S)$', parts[-2].strip(), re.IGNORECASE):
                    code = parts[-2].strip() + "-" + last_part
                    name = "-".join(parts[:-2]).strip()
                else:
                    code = last_part
                    name = "-".join(parts[:-1]).strip()
            elif len(parts) >= 2 and ' ' not in parts[1].strip() and re.match(r'^(SIF|S)$', first_part, re.IGNORECASE):
                code = first_part + "-" + parts[1].strip()
                name = "-".join(parts[2:]).strip()
            elif ' ' not in first_part and len(first_part) >= 1 and not first_part.isalpha():
                code = first_part
                name = "-".join(parts[1:]).strip()
                
        if code and is_amfi:
            code = normalize_amfi_code(code)
        return name, code

    def split_into_lines(text):
        if not text: return []
        text = str(text)
        if ',' in text and '\n' not in text:
            text = text.replace(',', '\n')
        # Insert newline before Regular/Direct Plan if missing
        text = re.sub(r'(?<!\n)(Regular Plan|Direct Plan)', r'\n\1', text, flags=re.IGNORECASE)
        # Insert newline before ISINs if separated by spaces
        text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text)
        # Insert newline before SIF codes if separated by spaces
        text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)
        # Insert newline for multiple spaces
        text = re.sub(r'\s{2,}', '\n', text)
        
        lines = []
        for line in text.split('\n'):
            line = line.strip().replace('–', '-')
            line = re.sub(r'^[\d\.\)\uf0b7\-\s,]+', '', line).strip()
            if line: lines.append(line)
        return lines

    # Extract all text blobs
    sebi_code_val = get_val(["sebi code", "sebi codes"])
    options_text = get_val(["option names"])
    amfi_text = get_val(["amfi code", "amfi codes"])
    isin_text = get_val(["isin", "isins"])
    rta_text = get_val(["rta code", "rta codes"])
    
    options_lines = split_into_lines(options_text)
    amfi_lines = split_into_lines(amfi_text)
    isin_lines = split_into_lines(isin_text)
    rta_lines = split_into_lines(rta_text)
    
    # Pre-populate extracted_plans with options
    ordered_plan_names = []
    for line in options_lines:
        clean_name = re.sub(r'[^a-zA-Z0-9\)]+$', '', line).strip()
        if not clean_name: continue
        norm = normalize_name(clean_name)
        if norm not in extracted_plans:
            extracted_plans[norm] = {"name": clean_name}
        ordered_plan_names.append(norm)
        
    # Helper for generic parsing
    def apply_codes(lines, code_key):
        if not lines: return
        is_amfi = code_key == "amfi_code"
        is_isin = code_key == "isin_code"
        
        # Check if it's a single general code
        if len(lines) == 1 and 'plan' not in lines[0].lower() and 'option' not in lines[0].lower() and ' ' not in lines[0]:
            code_val = lines[0]
            if is_amfi: code_val = normalize_amfi_code(code_val)
            for plan_obj in extracted_plans.values():
                if code_key not in plan_obj: plan_obj[code_key] = code_val
            return
            
        # Strategy 1: Perfect parallel mapping
        if ordered_plan_names and len(lines) == len(ordered_plan_names):
            for i, line in enumerate(lines):
                norm = ordered_plan_names[i]
                _, extracted_code = extract_embedded_code(line, is_amfi=is_amfi, is_isin=is_isin)
                
                final_code = None
                if is_amfi:
                    if extracted_code:
                        final_code = normalize_amfi_code(extracted_code)
                    elif re.match(r'^(?:SIF|S)?[-\s]*\d+$', line.strip(), re.IGNORECASE):
                        final_code = normalize_amfi_code(line)
                elif is_isin:
                    if extracted_code:
                        final_code = extracted_code
                    else:
                        m = re.search(r'(INF[A-Z0-9]{9})', line.strip(), re.IGNORECASE)
                        if m:
                            final_code = m.group(1)
                else:
                    if extracted_code:
                        final_code = extracted_code
                    elif len(line.strip()) <= 20 and not re.search(r'regular|direct|plan|growth|idcw', line.lower()):
                        final_code = line.strip()
                        
                if final_code:
                    extracted_plans[norm][code_key] = final_code
            return
            
        # Strategy 2: Extract embedded codes and match by name or fallback positional
        last_unmatched = None
        positional_idx = 0
        
        for i, line in enumerate(lines):
            name, code = extract_embedded_code(line, is_amfi=is_amfi, is_isin=is_isin)
            clean_name = re.sub(r'[^a-zA-Z0-9\)]+$', '', name).strip()
            norm = normalize_name(clean_name) if clean_name else ""
            
            final_code = None
            if is_amfi:
                if code:
                    final_code = normalize_amfi_code(code)
                elif re.match(r'^(?:SIF|S)?[-\s]*\d+$', line.strip(), re.IGNORECASE):
                    final_code = normalize_amfi_code(line)
            elif is_isin:
                if code:
                    final_code = code
                else:
                    m = re.search(r'(INF[A-Z0-9]{9})', line.strip(), re.IGNORECASE)
                    if m:
                        final_code = m.group(1)
            else:
                # RTA code
                if code:
                    final_code = code
                elif len(line.strip()) <= 20 and not re.search(r'regular|direct|plan|growth|idcw', line.lower()):
                    final_code = line.strip()
                    
            if not final_code:
                if norm: last_unmatched = (norm, clean_name)
                continue
                
            matched = False
            
            def find_plan(target_name):
                if not target_name: return None
                if target_name in extracted_plans: return target_name
                # Partial match
                for p in extracted_plans:
                    if target_name in p or p in target_name:
                        return p
                return None
                
            matched_last = find_plan(last_unmatched[0] if last_unmatched else None)
            matched_norm = find_plan(norm)
            
            if matched_last and not extracted_plans[matched_last].get(code_key):
                extracted_plans[matched_last][code_key] = final_code
                matched = True
            elif matched_norm and not extracted_plans[matched_norm].get(code_key):
                extracted_plans[matched_norm][code_key] = final_code
                matched = True
            elif norm and code:
                # Embedded successfully, but name didn't match existing options! Create it.
                if norm not in extracted_plans:
                    extracted_plans[norm] = {"name": clean_name}
                if not extracted_plans[norm].get(code_key):
                    extracted_plans[norm][code_key] = final_code
                    matched = True
            elif last_unmatched:
                unmatched_norm, unmatched_clean = last_unmatched
                if unmatched_norm not in extracted_plans:
                    extracted_plans[unmatched_norm] = {"name": unmatched_clean}
                if not extracted_plans[unmatched_norm].get(code_key):
                    extracted_plans[unmatched_norm][code_key] = final_code
                    matched = True
                    
            if not matched:
                # Positional fallback
                while positional_idx < len(ordered_plan_names) and extracted_plans[ordered_plan_names[positional_idx]].get(code_key):
                    positional_idx += 1
                    
                if positional_idx < len(ordered_plan_names):
                    extracted_plans[ordered_plan_names[positional_idx]][code_key] = final_code
                    positional_idx += 1
                else:
                    # Create orphaned
                    if norm not in extracted_plans:
                        extracted_plans[norm] = {"name": clean_name or final_code}
                    extracted_plans[norm][code_key] = final_code
                    
            last_unmatched = None

    apply_codes(amfi_lines, "amfi_code")
    apply_codes(isin_lines, "isin_code")
    apply_codes(rta_lines, "rta_code")

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
    for plan_obj in extracted_plans.values():
        name_lower = plan_obj.get("name", "").lower()
        plan_type = "direct" if "direct" in name_lower else "regular"
        
        if "growth" in name_lower:
            ref = plans[plan_type]["growth"]
        else:
            if "reinvest" in name_lower: subtype = "reinvestment"
            elif "transfer" in name_lower: subtype = "transfer"
            elif "payout" in name_lower: subtype = "payout"
            else: subtype = "unknown"
            ref = plans[plan_type]["idcw"][subtype]
            
        if not ref.get("name"):
            ref.update(plan_obj)
            if not primary_amfi_code and plan_obj.get("amfi_code"):
                primary_amfi_code = plan_obj.get("amfi_code")
        else:
            if "additional_plans" not in ref: ref["additional_plans"] = []
            ref["additional_plans"].append(plan_obj)
            if not primary_amfi_code and plan_obj.get("amfi_code"):
                primary_amfi_code = plan_obj.get("amfi_code")
                
    if primary_amfi_code:
        primary_amfi_code = primary_amfi_code.replace(',', ' ').replace(';', ' ').split()[0]

    fund_name_val = get_val(["fund name"]) or api_data.get("Scheme_Name")
    if not sebi_code_val:
        import logging
        fund_name_safe = str(fund_name_val).upper() if fund_name_val else "UNKNOWN_FUND"
        safe_name = re.sub(r'[^A-Z0-9]', '_', fund_name_safe).strip('_')
        safe_name = re.sub(r'_+', '_', safe_name)
        sebi_code_val = f"TEMP_{safe_name}" if safe_name else "TEMP_UNKNOWN"
        logging.warning(f"Generated TEMP SEBI code: {sebi_code_val} for scheme {fund_name_val}")

    # Use api_data as fallback for essential fields
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
