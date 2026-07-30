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

    def parse_asset_allocation(text):
        if not text: return None
        allocations = []
        pattern = r'([A-Za-z\s]+?)\s*(?:-)?\s*(\d+(?:\.\d+)?)%?\s*(?:to|-)\s*(\d+(?:\.\d+)?)%?'
        matches = list(re.finditer(pattern, str(text), re.IGNORECASE))
        if not matches:
            text_clean = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\t]+', '\n', str(text))
            for line in text_clean.split('\n'):
                line = line.strip()
                if line:
                    allocations.append({
                        "allocation_type": line,
                        "minimum_percentage": None,
                        "maximum_percentage": None
                    })
            return allocations
            
        for m in matches:
            name = m.group(1).strip()
            name = re.sub(r'^[\s,;]+', '', name)
            allocations.append({
                "allocation_type": name,
                "minimum_percentage": float(m.group(2)) if '.' in m.group(2) else int(m.group(2)),
                "maximum_percentage": float(m.group(3)) if '.' in m.group(3) else int(m.group(3))
            })
        return allocations

    def parse_fund_managers(fm_names_raw, fm_types_raw, fm_dates_raw, fm_todates_raw=""):
        fm_names = [l.strip() for l in str(fm_names_raw).split('\n') if l.strip()] if fm_names_raw else []
        fm_types = [l.strip() for l in str(fm_types_raw).split('\n') if l.strip()] if fm_types_raw else []
        fm_froms = [l.strip() for l in str(fm_dates_raw).split('\n') if l.strip()] if fm_dates_raw else []
        fm_tos   = [l.strip() for l in str(fm_todates_raw).split('\n') if l.strip()] if fm_todates_raw else []
        
        def extract_prefix(text):
            m = re.match(r'^(.*?)\s*-\s*(.*)$', text)
            if m:
                prefix = m.group(1).strip()
                if len(prefix) < 50:
                    return prefix, m.group(2).strip()
            return None, text
            
        records_dict = {}
        for l in fm_names:
            pref, val = extract_prefix(l)
            key = pref if pref else "default"
            if key not in records_dict: records_dict[key] = {"name": "", "type": "", "from": "", "to": None, "role_or_portion": pref}
            records_dict[key]["name"] = val
            
        for l in fm_types:
            pref, val = extract_prefix(l)
            key = pref if pref else "default"
            if key in records_dict: records_dict[key]["type"] = val
            
        for l in fm_froms:
            pref, val = extract_prefix(l)
            key = pref if pref else "default"
            if key in records_dict: records_dict[key]["from"] = normalize_date(val)
            
        for l in fm_tos:
            pref, val = extract_prefix(l)
            key = pref if pref else "default"
            if key in records_dict: records_dict[key]["to"] = normalize_date(val)
            
        if (not any(records_dict[k]["name"] for k in records_dict if k != "default")) and len(fm_names) > 1 and len(fm_names) == len(fm_types) == len(fm_froms):
            records = []
            for i in range(len(fm_names)):
                records.append({
                    "name": fm_names[i],
                    "type": fm_types[i] if i < len(fm_types) else "",
                    "from": normalize_date(fm_froms[i]) if i < len(fm_froms) else "",
                    "to": normalize_date(fm_tos[i]) if i < len(fm_tos) else None,
                    "role_or_portion": None
                })
            return records
        return list(records_dict.values())

    def normalize_date(d_str):
        if not d_str: return None
        d_clean = str(d_str).strip()
        if re.search(r'(?i)^(NA|N\.A\.|N/A|-|TBD)$', d_clean) or not d_clean: return None
        from datetime import datetime
        formats = [
            "%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d",
            "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y",
            "%d-%m-%y", "%d/%m/%y"
        ]
        for fmt in formats:
            try:
                parsed = datetime.strptime(d_clean, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return d_clean

    fund_managers = parse_fund_managers(
        get_val(["fund manager name"]),
        get_val(["fund manager type"]),
        get_val(["fund manager from date"]),
        get_val(["fund manager to date"])
    )



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
        if re.search(r'\b(direct|dir)\b', text_lower):
            plan = "direct"
            
        option = "growth"
        if any(k in text_lower for k in ["idcw", "dividend", "div", "payout", "reinvestment", "re-investment", "re-inv", "transfer"]):
            option = "idcw"
            
        subtype = "unknown"
        time_period = None
        
        if option == "idcw":
            if re.search(r'\b(reinvest|reinvestment|re-invest|re-inv)\b', text_lower):
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
        text = re.sub(r'(?<!\n)(INF[A-Z0-9]{8}[0-9])', r'\n\1', text, flags=re.IGNORECASE)
        text = re.sub(r'(?<!\n)((?:SIF|S)[-\s]*\d+)(?=\b|[^a-zA-Z0-9])', r'\n\1', text, flags=re.IGNORECASE)
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
            elif re.search(r'^(INF[A-Z0-9]{8}[0-9]|(?:SIF|S)[-\s]*\d+)', line, re.IGNORECASE):
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
            m = re.search(r'(INF[A-Z0-9]{8}[0-9])', line, re.IGNORECASE)
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
    # STAGE 1: Record Extraction & Cross-Field Mapping
    # -------------------------------------------------------------------------
    
    def extract_records(text, identifier_type):
        if not text: return []
        text = str(text)
        
        # Clean the text
        text = text.replace(',', '\n')
        text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\t]+', '\n', text)
        text = re.sub(r'\s{3,}', '\n', text)
        
        lines = []
        for line in text.split('\n'):
            clean_line = line.strip().strip('-–,.')
            clean_line = re.sub(r'^[\d\w]\)[\s\-]+', '', clean_line)
            clean_line = re.sub(r'^\d+\.[\s\-]+', '', clean_line)
            
            if clean_line and clean_line.lower() != 'na':
                pattern = None
                if identifier_type == "AMFI": pattern = r'((?:SIF|S)[-\s]*\d+)'
                elif identifier_type == "ISIN": pattern = r'(INF[A-Z0-9]{8}[0-9])'
                elif identifier_type == "OPTION": pattern = None
                    
                if pattern:
                    matches = list(re.finditer(pattern, clean_line, re.IGNORECASE))
                    if len(matches) > 1:
                        first_match = matches[0]
                        text_before = clean_line[:first_match.start()].strip()
                        if len(text_before) > 5:
                            clean_line = re.sub(pattern + r'(?=\s*[^a-zA-Z0-9\n])', r'\1\n', clean_line, flags=re.IGNORECASE)
                            clean_line = re.sub(pattern + r'(?=\s*[a-zA-Z])', r'\1\n', clean_line, flags=re.IGNORECASE)
                        else:
                            clean_line = re.sub(r'(?<!^)(?<!\n)\s*' + pattern, r'\n\1', clean_line, flags=re.IGNORECASE)
                            
                if identifier_type == "OPTION":
                    clean_line = re.sub(r'(?<!\n)(Regular Plan|Direct Plan|Regular|Direct)(?=\s|\-)', r'\n\1', clean_line, flags=re.IGNORECASE)

                for sub_line in clean_line.split('\n'):
                    sub_line = sub_line.strip().strip('-–,.')
                    if sub_line:
                        lines.append(sub_line)
                        
        extracted = []
        for line in lines:
            if line.startswith("NA - ") or line == "NA": continue
                
            code = None
            name = line
            has_identifier = False
            
            if identifier_type == "AMFI":
                m = re.search(r'((?:SIF|S)[-\s]*\d+)', line, re.IGNORECASE)
                if m:
                    code = m.group(1)
                    code = re.sub(r'^(?:SIF|S)[-\s]*', '', code, flags=re.IGNORECASE)
                    code = f"SIF-{code}"
                    name = line.replace(m.group(1), '').strip(' -–')
                    has_identifier = True
            elif identifier_type == "ISIN":
                m = re.search(r'(INF[A-Z0-9]{8}[0-9])', line, re.IGNORECASE)
                if m:
                    code = m.group(1)
                    name = line.replace(code, '').strip(' -–')
                    has_identifier = True
            elif identifier_type == "RTA":
                parts = line.split('-')
                if len(parts) > 1:
                    last = parts[-1].strip()
                    first = parts[0].strip()
                    if len(first) >= 1 and ' ' not in first and first.isupper() and len(first) <= 10:
                        code = first
                        name = line.replace(code, '', 1).strip(' -–')
                        has_identifier = True
                    elif len(last) >= 1 and ' ' not in last and not last.isalpha():
                        code = last
                        name = "-".join(parts[:-1]).strip()
                        has_identifier = True
                elif len(line) <= 20 and not re.search(r'regular|direct|plan|growth|idcw', line.lower()):
                    code = line
                    name = ""
                    has_identifier = True
            elif identifier_type == "OPTION":
                has_identifier = True
                
            if not has_identifier: continue
                
            name_clean = name.strip() if name.strip() else None
            traits = get_canonical_traits(name_clean if name_clean else line)
            
            extracted.append({
                "identifier_type": identifier_type,
                "identifier": code,
                "plan_type": traits["plan"],
                "option": traits["option"],
                "sub_option": traits["subtype"],
                "time_period": traits["time_period"],
                "raw_name": line,
                "is_bare": name_clean is None  # True if the line was just the identifier without any text
            })
            
        return extracted

    amfi_recs = extract_records(amfi_text, "AMFI")
    isin_recs = extract_records(isin_text, "ISIN")
    rta_recs = extract_records(rta_text, "RTA")
    option_recs = extract_records(options_text, "OPTION")
    
    # Identify the "Source of Truth" for variants
    # Prefer ISIN if it has full variants, otherwise OPTION
    signatures = []
    
    def gather_signatures(recs):
        sigs = []
        for r in recs:
            if not r.get("is_bare"):
                sig = (r["plan_type"], r["option"], r["sub_option"], r["time_period"])
                if sig not in sigs:
                    sigs.append(sig)
        return sigs

    isin_sigs = gather_signatures(isin_recs)
    opt_sigs = gather_signatures(option_recs)
    
    def count_specific(sigs):
        count = 0
        for s in sigs:
            if s[1] and s[2] and s[2] not in ["unknown", "none"]:
                count += 1
        return count

    # Use ISIN as source of truth if it has equal or more specific variants than Option
    if len(isin_sigs) > 0 and count_specific(isin_sigs) >= count_specific(opt_sigs):
        signatures = isin_sigs
    elif len(opt_sigs) > 0:
        signatures = opt_sigs
    else:
        signatures = isin_sigs
        
    def map_bare_records(recs, sigs):
        if not recs or not sigs: return
        bare_recs = [r for r in recs if r["is_bare"]]
        if not bare_recs: return

        # If ALL records are bare, do a 1-to-1 sequential mapping if counts match
        if len(bare_recs) == len(recs):
            if len(recs) == len(sigs):
                for idx, r in enumerate(recs):
                    sig = sigs[idx]
                    r["plan_type"], r["option"], r["sub_option"], r["time_period"] = sig
                return
            elif len(recs) < len(sigs):
                # Duplicate to cover all sub_options in that group
                groups = []
                for sig in sigs:
                    g = (sig[0], sig[1])
                    if g not in groups: groups.append(g)
                if len(recs) == len(groups):
                    new_recs = []
                    for idx, r in enumerate(recs):
                        g = groups[idx]
                        matching_sigs = [s for s in sigs if (s[0], s[1]) == g]
                        for sig in matching_sigs:
                            cloned_r = dict(r)
                            cloned_r["plan_type"], cloned_r["option"], cloned_r["sub_option"], cloned_r["time_period"] = sig
                            new_recs.append(cloned_r)
                    recs.clear()
                    recs.extend(new_recs)
                return

        # If partially bare, try to map using process of elimination per plan_type
        # First group by plan_type (for records that HAVE a plan_type)
        plan_groups = {}
        for r in recs:
            plan = r["plan_type"]
            if plan not in plan_groups: plan_groups[plan] = []
            plan_groups[plan].append(r)

        resolved_recs = []
        for plan, group_recs in plan_groups.items():
            if not plan:
                resolved_recs.extend(group_recs)
                continue
            
            group_sigs = [s for s in sigs if s[0] == plan]
            explicit_recs = [r for r in group_recs if not r["is_bare"]]
            local_bare_recs = [r for r in group_recs if r["is_bare"]]

            if not local_bare_recs:
                resolved_recs.extend(group_recs)
                continue

            # Find which signatures are explicitly taken
            taken_sigs = []
            for r in explicit_recs:
                sig = (r["plan_type"], r["option"], r["sub_option"], r["time_period"])
                if sig not in taken_sigs: taken_sigs.append(sig)

            # Available signatures
            available_sigs = [s for s in group_sigs if s not in taken_sigs]

            resolved_recs.extend(explicit_recs)
            
            if len(local_bare_recs) == len(available_sigs):
                # 1-to-1 assignment
                for i, br in enumerate(local_bare_recs):
                    sig = available_sigs[i]
                    br["plan_type"], br["option"], br["sub_option"], br["time_period"] = sig
                    resolved_recs.append(br)
            else:
                # Can't confidently resolve, leave as is
                resolved_recs.extend(local_bare_recs)
        
        recs.clear()
        recs.extend(resolved_recs)

    map_bare_records(amfi_recs, signatures)
    map_bare_records(isin_recs, signatures)
    map_bare_records(rta_recs, signatures)
    
    def resolve_unknown_sub_options(recs, sigs):
        if not recs: return
        groups = {}
        for r in recs:
            key = (r["plan_type"], r["option"])
            if key not in groups: groups[key] = []
            groups[key].append(r)
            
        resolved_recs = []
        for key, group_recs in groups.items():
            plan, option = key
            if option != "idcw":
                resolved_recs.extend(group_recs)
                continue
                
            group_sigs = [s[2] for s in sigs if s[0] == plan and s[1] == option and s[2] not in [None, "unknown"]]
            taken_slots = set(r["sub_option"] for r in group_recs if r["sub_option"] not in [None, "unknown"])
            available_slots = set(group_sigs) - taken_slots
            
            generic_recs = [r for r in group_recs if r["sub_option"] in [None, "unknown"]]
            explicit_recs = [r for r in group_recs if r["sub_option"] not in [None, "unknown"]]
            
            resolved_recs.extend(explicit_recs)
            
            if len(generic_recs) == 1 and not explicit_recs and group_sigs:
                for s in group_sigs:
                    cloned = dict(generic_recs[0])
                    cloned["sub_option"] = s
                    resolved_recs.append(cloned)
            elif generic_recs:
                available_list = list(available_slots)
                for gr in generic_recs:
                    if available_list:
                        slot = available_list.pop(0)
                        cloned = dict(gr)
                        cloned["sub_option"] = slot
                        resolved_recs.append(cloned)
                    else:
                        resolved_recs.append(gr)
        
        recs.clear()
        recs.extend(resolved_recs)

    resolve_unknown_sub_options(amfi_recs, signatures)
    resolve_unknown_sub_options(isin_recs, signatures)
    resolve_unknown_sub_options(rta_recs, signatures)

    records = amfi_recs + isin_recs + rta_recs
    


    # -------------------------------------------------------------------------
    # STAGE 2: JSON Builder
    # -------------------------------------------------------------------------
    
    plans = {
        "regular": {
            "growth": [],
            "idcw": { "payout": [], "reinvestment": [], "transfer": [], "time_period": [], "unknown": [] },
            "unresolved": []
        }
    }
    
    # We group by semantic signature (plan_type, option, sub_option, time_period)
    grouped = {}
    for r in records:
        sig = (r["plan_type"], r["option"], r["sub_option"], r["time_period"])
        if sig not in grouped:
            grouped[sig] = []
        grouped[sig].append(r)
        
    for sig, recs in grouped.items():
        ptype, otype, stype, tperiod = sig
        
        if ptype != "regular":
            continue
        
        # Merge all identifiers for this exact signature into a single output node
        amfi_code = None
        isin_code = None
        rta_code = None
        names = []
        
        for r in recs:
            if r["identifier_type"] == "AMFI" and not amfi_code: amfi_code = r["identifier"]
            if r["identifier_type"] == "ISIN" and not isin_code: isin_code = r["identifier"]
            if r["identifier_type"] == "RTA" and not rta_code: rta_code = r["identifier"]
            if r["raw_name"] and r["raw_name"] not in names: names.append(r["raw_name"])
            
        combined_name = " | ".join(names) if names else f"{ptype.title()} Plan {otype.title()}"
        
        output_node = {
            "plan_type": ptype,
            "option": otype,
            "sub_option": stype,
            "time_period": tperiod,
            "name": combined_name,
            "amfi_code": amfi_code,
            "isin_code": isin_code,
            "rta_code": rta_code
        }
        
        if otype == "growth":
            plans[ptype]["growth"].append(output_node)
        else:
            if stype and stype in plans[ptype]["idcw"]:
                plans[ptype]["idcw"][stype].append(output_node)
            else:
                plans[ptype]["idcw"]["unknown"].append(output_node)
                
    primary_amfi_code = None
    for r in records:
        if r["identifier_type"] == "AMFI":
            primary_amfi_code = r["identifier"]
            break

    if primary_amfi_code:
        primary_amfi_code = primary_amfi_code.replace(',', ' ').replace(';', ' ').split()[0]

    fund_name_val_old = get_val(["fund name"]) or api_data.get("Scheme_Name")
    if not sebi_code_val:
        import logging
        fund_name_safe = str(fund_name_val).upper() if fund_name_val else "UNKNOWN_FUND"
        logging.warning(f"Could not extract SEBI code for scheme {fund_name_safe}. Leaving as None.")
        sebi_code_val = None

    result = {
        "sebi_code": sebi_code_val,
        "fund_name": fund_name_val,
        "fund_type": get_val(["fund type"]) or api_data.get("SchemeType_Desc"),
        "category": get_val(["category as per sebi", "category as per"]) or api_data.get("SchemeCat_Desc"),
        
        "riskometer_at_launch": get_val(["riskometer (at the time of launch)", "riskometer at launch"]),
        "riskometer_as_on_date": get_val(["riskometer (as on date)", "riskometer as on date"]),
        "potential_risk_class": get_val(["potential risk class"]),
        "scheme_objective": get_val(["description, objective of the scheme", "objective of the scheme"]),
        
        "face_value": get_val(["face value"]),
        
        "nfo_open_date": normalize_date(get_val(["nfo open date"])),
        "nfo_close_date": normalize_date(get_val(["nfo close date"])),
        "allotment_date": normalize_date(get_val(["allotment date"])),
        "reopen_date": normalize_date(get_val(["reopen date", "re-open date"])),
        "maturity_date": normalize_date(get_val(["maturity date"])),
        
        "benchmark_tier_1": get_val(["benchmark (tier 1)", "tier 1 benchmark", "tier 1"]),
        "benchmark_tier_2": get_val(["benchmark (tier 2)", "tier 2 benchmark", "tier 2"]),
        
        "asset_allocation": parse_asset_allocation(get_val(["stated asset allocation", "asset allocation"])),
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
