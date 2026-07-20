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



    # Extract all text blobs
    sebi_code_val = get_val(["sebi code", "sebi codes"])
    fund_name_val = get_val(["fund name"]) or api_data.get("Scheme_Name")
    options_text = get_val(["option names"])
    amfi_text = get_val(["amfi code", "amfi codes"])
    isin_text = get_val(["isin", "isins"])
    rta_text = get_val(["rta code", "rta codes"])
    
    # -------------------------------------------------------------------------
    # STAGE 2 & 3: Normalization Engine and Tokenization
    # -------------------------------------------------------------------------
    def get_canonical_traits(text):
        text_lower = text.lower()
        
        plan = "regular"
        if "direct" in text_lower or "dir" in text_lower.split():
            plan = "direct"
            
        option = "growth"
        if any(k in text_lower for k in ["idcw", "dividend", "div", "payout", "reinvestment", "re-investment", "transfer"]):
            option = "idcw"
            
        subtype = "unknown"
        time_period = None
        
        if option == "idcw":
            if "reinvest" in text_lower:
                subtype = "reinvestment"
            elif "transfer" in text_lower:
                subtype = "transfer"
            elif "payout" in text_lower:
                subtype = "payout"
                
            periods = {
                "daily": ["daily"],
                "weekly": ["weekly"],
                "fortnightly": ["fortnightly", "fortnight"],
                "monthly": ["monthly"],
                "quarterly": ["quarterly"],
                "half_yearly": ["half yearly", "half-yearly"],
                "annual": ["annual", "yearly"],
                "periodic": ["periodic"]
            }
            for p_key, p_keywords in periods.items():
                if any(k in text_lower for k in p_keywords):
                    time_period = p_key
                    break
                    
            if subtype == "unknown" and time_period:
                subtype = "time_period"
                
        return {"plan": plan, "option": option, "subtype": subtype if option == "idcw" else None, "time_period": time_period}

    def segment_records(text, fund_name):
        if not text: return []
        text = str(text)
        
        if ',' in text and '\n' not in text:
            text = text.replace(',', '\n')
        elif ',' in text:
            text = re.sub(r',\s*(?=[a-zA-Z])', '\n', text)
            
        fn_escaped = ""
        if fund_name:
            fn_escaped = re.escape(fund_name)
            text = re.sub(f'(?i)(?<!\\n)({fn_escaped})', r'\n\1', text)
            
        text = re.sub(r'(?<!\n)(Regular Plan|Direct Plan|Regular|Direct)(?=\s|\-)', r'\n\1', text, flags=re.IGNORECASE)
        text = re.sub(r'(?<!\n)(INF[A-Z0-9]{9})', r'\n\1', text, flags=re.IGNORECASE)
        text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\s|$)', r'\n\1', text, flags=re.IGNORECASE)
        text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\t]+', '\n', text)
        text = re.sub(r'\s{3,}', '\n', text)
        
        lines = []
        for line in text.split('\n'):
            clean_line = line.strip().strip('-–,.')
            clean_line = re.sub(r'^[\d\w]\)[\s\-]+', '', clean_line)
            clean_line = re.sub(r'^\d+\.[\s\-]+', '', clean_line)
            if clean_line:
                lines.append(clean_line)
                
        records = []
        current_record = []
        for line in lines:
            is_boundary = False
            if fund_name and re.search(f'(?i)^{fn_escaped}', line):
                is_boundary = True
            elif re.search(r'^(regular plan|direct plan|regular|direct)\b', line, re.IGNORECASE):
                is_boundary = True
                
            if is_boundary and current_record:
                cr_str = " ".join(current_record)
                if fund_name and cr_str.lower() == fund_name.lower():
                    pass
                else:
                    records.append(" ".join(current_record))
                    current_record = []
                    
            current_record.append(line)
            
        if current_record:
            records.append(" ".join(current_record))
            
        return records

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
    options_raw = segment_records(options_text, fund_name_val)
    amfi_raw = segment_records(amfi_text, fund_name_val)
    isin_raw = segment_records(isin_text, fund_name_val)
    rta_raw = segment_records(rta_text, fund_name_val)

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
            
        # If no options exist, populate them dynamically with carry-forward logic
        if not master_plans:
            last_name = None
            last_traits = None
            for pitem in parsed_items:
                if pitem["name"] and not pitem["code"]:
                    last_name = pitem["name"]
                    last_traits = pitem["traits"]
                elif pitem["code"]:
                    r_name = pitem["name"] if pitem["name"] else (last_name if last_name else pitem["code"])
                    r_traits = pitem["traits"] if pitem["name"] else (last_traits if last_traits else get_canonical_traits(pitem["code"]))
                    master_plans.append({
                        "raw_name": r_name,
                        "traits": r_traits,
                        "amfi_code": pitem["code"] if is_amfi else None,
                        "isin_code": pitem["code"] if is_isin else None,
                        "rta_code": pitem["code"] if not is_amfi and not is_isin else None
                    })
                    last_name = None
                    last_traits = None
            return

        # Stage 5: Smart Merging
        # Strategy A: Positional 1-to-1 matching
        if len(parsed_items) == len(master_plans):
            for i, pitem in enumerate(parsed_items):
                if pitem["code"]:
                    master_plans[i][code_type] = pitem["code"]
            return
            
        # Strategy B: Advanced Trait & Partial Name Matching
        positional_idx = 0
        last_unmatched_mp = None
        
        for pitem in parsed_items:
            if not pitem["code"]:
                # If there's a name but no code, remember this name for the next code (embedded code broken across lines)
                if pitem["name"]:
                    p_lower = pitem["name"].lower()
                    candidates = [m for m in master_plans if not m[code_type] and (p_lower in m["raw_name"].lower() or m["raw_name"].lower() in p_lower)]
                    if candidates:
                        last_unmatched_mp = candidates[0]
                continue
                
            matched = False
            
            # 1. Exact canonical trait match (if name was provided and has clear traits)
            if pitem["name"]:
                candidates = [m for m in master_plans if m["traits"] == pitem["traits"] and not m[code_type]]
                if len(candidates) == 1:
                    candidates[0][code_type] = pitem["code"]
                    matched = True
                elif len(candidates) > 1:
                    # Resolve tie with partial name match
                    p_lower = pitem["name"].lower()
                    sub_candidates = [m for m in candidates if p_lower in m["raw_name"].lower() or m["raw_name"].lower() in p_lower]
                    if sub_candidates:
                        sub_candidates[0][code_type] = pitem["code"]
                        matched = True
                    else:
                        candidates[0][code_type] = pitem["code"]
                        matched = True
                        
            # 2. Partial String Match
            if not matched and pitem["name"]:
                p_lower = pitem["name"].lower()
                candidates = [m for m in master_plans if not m[code_type] and (p_lower in m["raw_name"].lower() or m["raw_name"].lower() in p_lower)]
                if candidates:
                    candidates[0][code_type] = pitem["code"]
                    matched = True
                    
            # 3. Last Unmatched carryover
            if not matched and last_unmatched_mp and not last_unmatched_mp[code_type]:
                last_unmatched_mp[code_type] = pitem["code"]
                matched = True
                
            # 4. Positional fallback
            if not matched:
                while positional_idx < len(master_plans) and master_plans[positional_idx][code_type]:
                    positional_idx += 1
                    
                if positional_idx < len(master_plans):
                    master_plans[positional_idx][code_type] = pitem["code"]
                    positional_idx += 1
                    matched = True
                    
            if not matched:
                # 5. Create orphaned
                master_plans.append({
                    "raw_name": pitem["name"] if pitem["name"] else pitem["code"],
                    "traits": pitem["traits"],
                    "amfi_code": pitem["code"] if is_amfi else None,
                    "isin_code": pitem["code"] if is_isin else None,
                    "rta_code": pitem["code"] if not is_amfi and not is_isin else None
                })
            
            last_unmatched_mp = None

    merge_codes(amfi_raw, "amfi_code")
    merge_codes(isin_raw, "isin_code")
    merge_codes(rta_raw, "rta_code")

    # -------------------------------------------------------------------------
    # STAGE 6: Classification
    # -------------------------------------------------------------------------
    plans = {
        "regular": {
            "growth": {},
            "idcw": { "payout": {}, "reinvestment": {}, "transfer": {}, "time_period": {}, "unknown": {} }
        },
        "direct": {
            "growth": {},
            "idcw": { "payout": {}, "reinvestment": {}, "transfer": {}, "time_period": {}, "unknown": {} }
        }
    }
    
    primary_amfi_code = None
    validation_conflicts = []
    
    for mp in master_plans:
        ptype = mp["traits"]["plan"]
        otype = mp["traits"]["option"]
        stype = mp["traits"]["subtype"]
        tperiod = mp["traits"].get("time_period")
        
        plan_output = {
            "name": mp["raw_name"]
        }
        if mp["amfi_code"]: plan_output["amfi_code"] = mp["amfi_code"]
        if mp["isin_code"]: plan_output["isin_code"] = mp["isin_code"]
        if mp["rta_code"]: plan_output["rta_code"] = mp["rta_code"]
        if tperiod: plan_output["time_period"] = tperiod
        
        if otype == "growth":
            ref = plans[ptype]["growth"]
            if not ref.get("name"):
                ref.update(plan_output)
                if not primary_amfi_code and mp["amfi_code"]:
                    primary_amfi_code = mp["amfi_code"]
            else:
                # Growth is full, try the alternative plan
                alt_ptype = "direct" if ptype == "regular" else "regular"
                alt_ref = plans[alt_ptype]["growth"]
                if not alt_ref.get("name"):
                    import logging
                    logging.warning(f"Ambiguous Growth record re-routed to {alt_ptype}: {mp['raw_name']}")
                    alt_ref.update(plan_output)
                    if not primary_amfi_code and mp["amfi_code"]:
                        primary_amfi_code = mp["amfi_code"]
                else:
                    import logging
                    logging.warning(f"Dropped Growth record due to conflict: {mp['raw_name']}")
                    validation_conflicts.append({
                        "reason": "Duplicate Growth record",
                        "record": plan_output
                    })
        else:
            ref = plans[ptype]["idcw"][stype]
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

    fund_name_val_old = get_val(["fund name"]) or api_data.get("Scheme_Name")
    if not sebi_code_val:
        import logging
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
    
    # -------------------------------------------------------------------------
    # STAGE 8: Cross Validation Reporting
    # -------------------------------------------------------------------------
    import logging
    total_extracted_amfi = len([a for a in amfi_raw if a])
    total_extracted_isin = len([i for i in isin_raw if i])
    total_extracted_rta = len([r for r in rta_raw if r])
    
    mapped_amfi = 0
    mapped_isin = 0
    mapped_rta = 0
    unknown_mappings = 0
    
    def count_mappings(plan_node, is_unknown=False):
        nonlocal mapped_amfi, mapped_isin, mapped_rta, unknown_mappings
        if not isinstance(plan_node, dict): return
        if plan_node.get("amfi_code"): mapped_amfi += 1
        if plan_node.get("isin_code"): mapped_isin += 1
        if plan_node.get("rta_code"): mapped_rta += 1
        if is_unknown and (plan_node.get("amfi_code") or plan_node.get("isin_code") or plan_node.get("rta_code")):
            unknown_mappings += 1
        for ap in plan_node.get("additional_plans", []):
            if ap.get("amfi_code"): mapped_amfi += 1
            if ap.get("isin_code"): mapped_isin += 1
            if ap.get("rta_code"): mapped_rta += 1
            if is_unknown: unknown_mappings += 1
            
    for ptype, pdata in plans.items():
        count_mappings(pdata["growth"])
        for stype, sdata in pdata["idcw"].items():
            count_mappings(sdata, is_unknown=(stype == "unknown"))
            
    total_records = len(master_plans)
    dropped_records = len(validation_conflicts)
    classified = total_records - dropped_records
    
    # Confidence Score: heavily penalizes dropped records and unmapped codes
    unmapped_amfi = max(0, total_extracted_amfi - mapped_amfi)
    score = 100
    if total_records > 0:
        score -= (dropped_records / total_records) * 50
    if total_extracted_amfi > 0:
        score -= (unmapped_amfi / total_extracted_amfi) * 50
        
    logging.info(f"--- Parser Cross-Validation for {sebi_code_val} ---")
    logging.info(f"Logical Records: Detected={total_records}, Classified={classified}, Dropped={dropped_records}")
    logging.info(f"AMFI Codes: Extracted={total_extracted_amfi}, Mapped={mapped_amfi}")
    logging.info(f"ISIN Codes: Extracted={total_extracted_isin}, Mapped={mapped_isin}")
    logging.info(f"RTA Codes: Extracted={total_extracted_rta}, Mapped={mapped_rta}")
    logging.info(f"Unknown Mappings: {unknown_mappings}")
    logging.info(f"Confidence Score: {max(0, int(score))}%")
    for conflict in validation_conflicts:
        logging.warning(f"Conflict: {conflict['reason']} -> {conflict['record']}")
    logging.info("-------------------------------------------------")
    
    return result, primary_amfi_code
