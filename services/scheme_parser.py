import re
import json
import html


def build_scheme_json(api_data, rows):
    """
    Converts raw API data and XLS rows into a deeply nested JSON-serializable dictionary.
    """
    def clean_key(s):
        return re.sub(r'[^a-z0-9]', '', str(s).lower())

    xls_data = {}
    for row in rows:
        if not isinstance(row, dict):
            continue

        # Check for explicit field_N keys
        for k, v in row.items():
            if str(k).startswith("field_") and v:
                xls_data[str(k)] = v

        # Check if any column contains numeric field index (e.g. Fields: 8 or 0: '8')
        field_num = None
        for k, v in row.items():
            if str(k).lower() in ("fields", "field", "0", "col0", "sr no", "sr. no.", "s.no.", "sno"):
                if str(v).strip().isdigit():
                    field_num = str(v).strip()
            elif str(k).isdigit() and str(v).strip():
                field_num = str(k).strip()

        # If it's a key-value row (e.g. 2-4 columns with metadata keys like AttributeName/Value or SUMMARY/Unnamed: 2 or Fields/col0)
        vals = [(str(k).strip(), v) for k, v in row.items() if v is not None and not (isinstance(v, str) and (v.strip().lower() in ("nan", "none", "null", "") or v.strip() == ""))]
        
        is_kv_row = len(vals) <= 4 and any(
            k.lower() in ("summary document", "summary", "attributename", "fields", "col0", "unnamed: 0", "unnamed: 1", "unnamed: 2", "value", "attributevalue", "field", "0", "1", "2")
            or re.match(r"^\d+$", k)
            for k, _ in vals
        )

        if is_kv_row:
            key_val = None
            val_val = None
            for col_name, v in vals:
                if key_val is None:
                    if isinstance(v, str) and not re.match(r'^\d+(\.\d+)?$', str(v).strip()):
                        key_val = str(v).strip()
                elif val_val is None:
                    val_val = v
                    break
            if key_val and val_val is not None:
                if key_val in xls_data and xls_data[key_val] != val_val:
                    xls_data[f"{key_val}_2"] = val_val
                else:
                    xls_data[key_val] = val_val
            if field_num and val_val is not None:
                xls_data[f"field_{field_num}"] = val_val
            continue

        # If it's a direct dictionary of scheme fields (e.g. from XML or single-row dict where keys are field names)
        for k, v in row.items():
            if v is not None and not (isinstance(v, str) and v.strip().lower() in ("nan", "none", "null", "")):
                k_str = str(k).strip()
                if k_str not in ("Fields", "col0", "val"):
                    if k_str in xls_data and xls_data[k_str] != v:
                        xls_data[f"{k_str}_2"] = v
                    else:
                        xls_data[k_str] = v

    def get_val(possible_keys, exclude_keys=None):
        for pk in possible_keys:
            pk_clean = re.sub(r'\s+', ' ', pk.lower().strip())
            pk_norm = clean_key(pk)
            for k, val in xls_data.items():
                if val is None or (isinstance(val, str) and val.strip().lower() in ("nan", "none", "null", "--", "-", "")):
                    continue
                cleaned_k = re.sub(r'\s+', ' ', str(k).lower().strip())
                norm_k = clean_key(k)
                if exclude_keys and any(ex.lower() in cleaned_k for ex in exclude_keys):
                    continue
                if pk_clean == cleaned_k or pk_norm == norm_k or pk_clean in cleaned_k or pk_norm in norm_k:
                    return val
        return None

    def normalize_date(d_str):
        if not d_str: return None
        if hasattr(d_str, 'strftime'):
            return d_str.strftime("%Y-%m-%d")
        d_clean = str(d_str).strip()
        if re.search(r'(?i)^(NA|N\.A\.|N/A|-|TBD)$', d_clean) or not d_clean: return None
        m = re.match(r'^(\d{4}-\d{2}-\d{2})', d_clean)
        if m:
            return m.group(1)
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

    def parse_asset_allocation(data):
        if not data:
            return None

        def parse_num(s):
            if s is None:
                return None
            s = str(s).strip()
            return float(s) if "." in s else int(s)

        def clean_name(n):
            if not n:
                return ""
            n = str(n).strip()
            n = re.sub(r"^[\d\w]\)[\s\-]+", "", n)
            n = re.sub(r"^\d+\.[\s\-]+", "", n)
            n = re.sub(r"^[\s*#•\-\–:,.]+", "", n)
            n = re.sub(r"[\s*#\-\–:,.]+$", "", n)
            n = re.sub(r"(?i)\s*(?:out of which|of which)\s*:?$", "", n)
            n = re.sub(r"\s+", " ", n).strip()
            return n

        # 1. Handle list input
        if isinstance(data, list):
            if all(isinstance(item, dict) and "allocation_type" in item for item in data):
                return data

            dict_allocations = []
            for item in data:
                if isinstance(item, dict):
                    name = item.get("Instruments") or item.get("Instrument") or item.get("Particulars") or item.get("Asset Class") or item.get("allocation_type") or item.get("Name")
                    pct_str = item.get("IndicativeAllocation") or item.get("Allocation") or item.get("Percentage") or item.get("Range")
                    if name:
                        name_str = clean_name(str(name))
                        if name_str:
                            min_p, max_p = None, None
                            if pct_str:
                                pct_clean = str(pct_str).strip()
                                m_range = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*(?:to|-|–|\s+)\s*(\d+(?:\.\d+)?)\s*%", pct_clean, re.I)
                                if not m_range:
                                    m_range = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-|–)\s*(\d+(?:\.\d+)?)", pct_clean, re.I)
                                if m_range:
                                    min_p = parse_num(m_range.group(1))
                                    max_p = parse_num(m_range.group(2))
                                else:
                                    m_single = re.search(r"(\d+(?:\.\d+)?)\s*%", pct_clean)
                                    if m_single:
                                        val = parse_num(m_single.group(1))
                                        if re.search(r"(?i)\b(?:upto|up to|max|maximum)\b", pct_clean):
                                            min_p, max_p = 0, val
                                        else:
                                            min_p, max_p = val, val
                            dict_allocations.append({
                                "allocation_type": name_str,
                                "minimum_percentage": min_p,
                                "maximum_percentage": max_p
                            })
            if dict_allocations:
                return dict_allocations

            data = "\n".join(str(x) for x in data if x)

        text = html.unescape(str(data)).strip()
        if not text or text.lower() in ("nan", "none", "null", "--", "-", "n.a.", "na"):
            return None

        # Remove HTML table header tokens if present
        text = re.sub(r"(?i)\b(?:Instruments\s+)?Indicative\s*Allocation\s*(?:Risk\s*Profile)?\b", " ", text)
        # Replace Risk band markers with newlines
        text = re.sub(r"(?i)\bRisk\s*Band\s*Level\s*\d+\b", "\n", text)
        text = re.sub(r"(?i)\bRisk\s*Profile\s*:\s*[\w\s]+\b", "\n", text)
        text = re.sub(r"(?i)\bRisk\s*Band\s*:\s*[\w\s]+\b", "\n", text)
        text = re.sub(r"[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\uf0a7\t]+", "\n", text)

        # 1. Clean footnote narrative lines
        raw_lines = text.split("\n")
        cleaned_lines = []
        for l in raw_lines:
            l_str = l.strip()
            if not l_str:
                continue
            if re.match(r"^(?:\*|#|note:|please refer|there is no assurance)", l_str, re.IGNORECASE):
                if not re.search(r"[-–:=]\s*\d+\s*%?\s*(?:to|-|–)\s*\d+\s*%", l_str) and not re.search(r"[-–:=]\s*\d+\s*%", l_str):
                    continue
                if re.search(r"(?i)\b(?:include both|may also include|will be upto|are invested in|having an unexpired|specified under|please refer)\b", l_str):
                    continue
            cleaned_lines.append(l_str)

        full_text = "\n".join(cleaned_lines)

        # 2. Split inline allocations (comma/period/semicolon/multispace following a percentage range or percentage)
        full_text = re.sub(r"(?i)\.?\s*Please refer.*$", "", full_text, flags=re.MULTILINE)
        full_text = re.sub(r"(\d+(?:\.\d+)?\s*%?(?:\s*of\s+(?:net|total)\s+assets)?)\s*[,;.]\s*(?=[A-Za-z*#])", r"\1\n", full_text)
        full_text = re.sub(r"(\d+(?:\.\d+)?\s*%?(?:\s*of\s+(?:net|total)\s+assets)?)\s{3,}(?=[A-Za-z*#])", r"\1\n", full_text)
        full_text = re.sub(r"(\d+(?:\.\d+)?\s*%(?:\s*of\s+(?:net|total)\s+assets)?)\s+(?=[A-Z][a-z])", r"\1\n", full_text)

        # 3. Join wrapped lines (lines where previous line had no percentage)
        pct_range_regex = re.compile(r"(?:\d+(?:\.\d+)?\s*%?\s*(?:to|-|–|\s+)\s*\d+(?:\.\d+)?\s*%?|\d+(?:\.\d+)?\s*%)", re.IGNORECASE)

        split_lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        joined_lines = []
        for l in split_lines:
            if joined_lines and not pct_range_regex.search(joined_lines[-1]):
                joined_lines[-1] = joined_lines[-1] + " " + l
            else:
                joined_lines.append(l)

        allocations = []

        range_pattern = re.compile(
            r"^(.*?)(?::\s*-|:\s*|-{1,2}|–|=|:|\s)\s*(\d+(?:\.\d+)?)\s*%?\s*(?:to|-|–|\s+)\s*(\d+(?:\.\d+)?)\s*%?(?:\s*(?:of\s+(?:net|total)\s+assets))?\s*$",
            re.IGNORECASE
        )
        single_pattern = re.compile(
            r"^(.*?)(?::\s*-|:\s*|-{1,2}|–|=|:|\s|#)\s*(?:upto|up\s+to|not\s+exceeding|maximum|max\.?)?\s*(\d+(?:\.\d+)?)\s*%?(?:\s*(?:of\s+(?:net|total)\s+assets))?\s*$",
            re.IGNORECASE
        )

        for line in joined_lines:
            line_clean = line.strip().rstrip(".,;")
            if not line_clean:
                continue
            if re.match(r"^(?:\*|#|note:|please refer|there is no assurance)", line_clean, re.IGNORECASE) and not re.search(r"\d+\s*%", line_clean):
                continue

            m = range_pattern.match(line_clean)
            if m:
                raw_name, min_val, max_val = m.group(1), m.group(2), m.group(3)
                name = clean_name(raw_name)
                if name:
                    allocations.append({
                        "allocation_type": name,
                        "minimum_percentage": parse_num(min_val),
                        "maximum_percentage": parse_num(max_val)
                    })
                    continue

            m = single_pattern.match(line_clean)
            if m:
                raw_name, pct_val = m.group(1), m.group(2)
                name = clean_name(raw_name)
                if name:
                    val = parse_num(pct_val)
                    if re.search(r"(?i)\b(?:upto|up to|max|maximum|short exposure|derivative)\b", line_clean):
                        min_p = 0
                        max_p = val
                    else:
                        min_p = val
                        max_p = val
                    allocations.append({
                        "allocation_type": name,
                        "minimum_percentage": min_p,
                        "maximum_percentage": max_p
                    })
                    continue

            if not re.match(r"^(?:\*|#|note:|please refer|there is no assurance)", line_clean, re.IGNORECASE):
                name = clean_name(line_clean)
                if name:
                    allocations.append({
                        "allocation_type": name,
                        "minimum_percentage": None,
                        "maximum_percentage": None
                    })

        return allocations if allocations else None



    def parse_fund_managers():
        records = []
        indices = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                   "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
        for idx in indices:
            name = get_val([f"fund manager {idx} - name", f"fund manager {idx} name", f"fund manager {idx}- name"])
            if not name:
                continue
            fm_type = get_val([f"fund manager {idx} - type", f"fund manager {idx} type", f"fund manager {idx}- type", f"fund manager {idx} - type (primary/comanage/description)", f"fund manager {idx}- type (primary/comanage/description)"])
            from_date = get_val([f"fund manager {idx} - from date", f"fund manager {idx} from date", f"fund manager {idx}- from date"])
            to_date = get_val([f"fund manager {idx} - to date", f"fund manager {idx} to date", f"fund manager {idx}- to date"])
            records.append({
                "name": str(name).strip(),
                "type": str(fm_type).strip() if fm_type else "",
                "from": normalize_date(from_date),
                "to": normalize_date(to_date),
                "role_or_portion": None
            })

        if records:
            return records

        fm_names_raw = get_val(["fund manager name", "fund manager"])
        fm_types_raw = get_val(["fund manager type (primary/comanage/description)", "fund manager type"])
        fm_dates_raw = get_val(["fund manager from date"])
        fm_todates_raw = get_val(["fund manager to date"])

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
            recs = []
            for i in range(len(fm_names)):
                recs.append({
                    "name": fm_names[i],
                    "type": fm_types[i] if i < len(fm_types) else "",
                    "from": normalize_date(fm_froms[i]) if i < len(fm_froms) else "",
                    "to": normalize_date(fm_tos[i]) if i < len(fm_tos) else None,
                    "role_or_portion": None
                })
            return recs
        return [r for r in records_dict.values() if r.get("name")]

    fund_managers = parse_fund_managers()



    # Extract all text blobs
    sebi_code_val = get_val(["sebi code", "sebi codes", "investment strategy code", "strategy code", "sebi"]) or (api_data.get("SEBI_Codes") if isinstance(api_data, dict) else None) or (api_data.get("sebi_code") if isinstance(api_data, dict) else None) or (api_data.get("SEBI_Code") if isinstance(api_data, dict) else None)
    fund_name_val = get_val(["name of the investment strategy", "fund name", "scheme name", "name of the strategy", "strategy name"]) or (api_data.get("Scheme_Name") if isinstance(api_data, dict) else None) or (api_data.get("scheme_name") if isinstance(api_data, dict) else None) or (api_data.get("fund_name") if isinstance(api_data, dict) else None)
    options_text = get_val(["option names", "options names", "option names (regular & direct)", "options names (regular & direct)"])
    amfi_text = get_val(["amfi code", "amfi codes", "amfi codes (to be phased out)"])
    isin_text = get_val(["isin", "isins"])
    rta_text = get_val(["rta code", "rta codes", "rta code (to be phased out)"])
    
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
        },
        "direct": {
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
        
        if ptype not in plans:
            plans[ptype] = {
                "growth": [],
                "idcw": { "payout": [], "reinvestment": [], "transfer": [], "time_period": [], "unknown": [] },
                "unresolved": []
            }
        
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

    if not sebi_code_val:
        import logging
        fund_name_safe = str(fund_name_val).upper() if fund_name_val else "UNKNOWN_FUND"
        logging.warning(f"Could not extract SEBI code for scheme {fund_name_safe}. Leaving as None.")
        sebi_code_val = None

    def extract_scheme_objective():
        # Check standard structured Field 8 first if available
        f8 = xls_data.get("field_8")
        if f8 and isinstance(f8, str) and not re.match(r"^(?:primary|comanage|co manage|co-manage|regular|direct|growth|dividend|idcw|n\.a\.|na|-|--)$", f8.strip(), re.IGNORECASE):
            return f8.strip()

        raw = get_val([
            "description, objective of the investment strategy",
            "description, objective of the strategy",
            "description, objective of the scheme",
            "description, objective of scheme",
            "description / objective of the scheme",
            "description / objective of the strategy",
            "objective of the investment strategy",
            "objective of the strategy",
            "objective of the scheme",
            "objective of strategy",
            "objective of scheme",
            "investment objective",
            "description, objective",
            "description / objective",
            "scheme objective",
            "strategy objective",
            "description_objective_of_the_scheme",
            "description_objective_of_the_strategy",
            "description_objective_of_the_investment_strategy",
            "description_objective",
            "description"
        ], exclude_keys=["fund manager", "manager", "type", "category", "plan", "option", "code", "table", "risk"])

        if raw and not re.match(r"^(?:primary|comanage|co manage|co-manage|regular|direct|growth|dividend|idcw|n\.a\.|na|-|--)$", str(raw).strip(), re.IGNORECASE):
            return str(raw).strip()

        api_obj = (api_data.get("Scheme_Objective") if isinstance(api_data, dict) else None) or (api_data.get("scheme_objective") if isinstance(api_data, dict) else None) or (api_data.get("Description") if isinstance(api_data, dict) else None)
        if api_obj and not re.match(r"^(?:primary|comanage|co manage|co-manage|regular|direct|growth|dividend|idcw|n\.a\.|na|-|--)$", str(api_obj).strip(), re.IGNORECASE):
            return str(api_obj).strip()

        return None

    def extract_asset_allocation():
        v = get_val([
            "stated asset allocation", "stated_asset_allocation", "stated asset allocation1",
            "stated_asset_allocation1", "stated asset allocation 1", "asset allocation",
            "asset_allocation", "asset allocation pattern", "indicative asset allocation",
            "portfolio asset allocation", "stated_asset_allocation2", "stated_asset_allocation3",
            "field_9", "field_9_2"
        ], exclude_keys=["fund manager"])

        alloc_collected = []
        if v is not None:
            if isinstance(v, list):
                alloc_collected.extend(v)
            elif isinstance(v, str) and v.strip():
                alloc_collected.append(v.strip())

        f9 = xls_data.get("field_9")
        if f9 and isinstance(f9, str) and f9.strip() and f9.strip() not in alloc_collected:
            alloc_collected.append(f9.strip())

        if alloc_collected:
            return parse_asset_allocation(alloc_collected)

        api_alloc = (api_data.get("Asset_Allocation") if isinstance(api_data, dict) else None) or (api_data.get("asset_allocation") if isinstance(api_data, dict) else None)
        if api_alloc:
            return parse_asset_allocation(api_alloc)

        return None

    result = {
        "sebi_code": sebi_code_val,
        "scheme_name": fund_name_val,
        "fund_name": fund_name_val,
        "scheme_type": get_val(["fund type", "type of investment strategy", "type of scheme"]) or (api_data.get("SchemeType_Desc") if isinstance(api_data, dict) else None),
        "fund_type": get_val(["fund type", "type of investment strategy", "type of scheme"]) or (api_data.get("SchemeType_Desc") if isinstance(api_data, dict) else None),
        "category": get_val(["category as per sebi", "category of the investment strategy", "category as per sebi categorization circular", "category as per"]) or (api_data.get("SchemeCat_Desc") if isinstance(api_data, dict) else None),
        
        "riskometer_at_launch": get_val(["riskometer (at the time of launch)", "riskometer at launch", "risk band (at the time of launch)", "riskband (at the time of launch)", "risk- band (at the time of launch)"]),
        "riskometer_as_on_date": get_val(["riskometer (as on date)", "riskometer as on date", "risk band (as on date)", "riskband (as on date)", "risk- band (as on date)", "riskometer (august 31, 2026)", "riskometer (march 31, 2026)"]),
        "potential_risk_class": get_val(["potential risk class", "potential risk class (as on date)"]),
        "scheme_objective": extract_scheme_objective(),
        
        "face_value": get_val(["face value"]),
        
        "nfo_open_date": normalize_date(get_val(["nfo open date"])) or normalize_date(api_data.get("Launch_Date") if isinstance(api_data, dict) else None),
        "nfo_close_date": normalize_date(get_val(["nfo close date", "nfo close date"])) or normalize_date(api_data.get("Closure_Date") if isinstance(api_data, dict) else None),
        "allotment_date": normalize_date(get_val(["allotment date"])),
        "reopen_date": normalize_date(get_val(["reopen date", "re-open date"])) or normalize_date(api_data.get("Reopen_Date") if isinstance(api_data, dict) else None),
        "maturity_date": normalize_date(get_val(["maturity date", "maturity date (for closed-end funds)"])),
        
        "benchmark_tier_1": get_val([
            "benchmark (tier 1)",
            "benchmark (tier1)",
            "tier 1 benchmark",
            "tier 1",
            "tier1",
            "benchmark name",
            "benchmark"
        ]) or (api_data.get("Benchmark_Tier_1") if isinstance(api_data, dict) else None) or (api_data.get("benchmark_tier_1") if isinstance(api_data, dict) else None) or (api_data.get("Benchmark") if isinstance(api_data, dict) else None) or (api_data.get("benchmark") if isinstance(api_data, dict) else None),
        "benchmark_tier_2": get_val([
            "benchmark (tier 2)",
            "benchmark (tier2)",
            "tier 2 benchmark",
            "tier 2",
            "tier2"
        ]) or (api_data.get("Benchmark_Tier_2") if isinstance(api_data, dict) else None) or (api_data.get("benchmark_tier_2") if isinstance(api_data, dict) else None),
        
        "asset_allocation": extract_asset_allocation(),
        "listing_details": get_val(["listing details"]),
        
        "plans": plans,
        "fund_managers": fund_managers,
        
        "investment_limits": {
            "minimum_application_amount": get_val(["minimum application amount", "min. application amount", "minimum amount", "min. amount"]) or (api_data.get("Scheme_min_amt") if isinstance(api_data, dict) else None) or (api_data.get("scheme_min_amt") if isinstance(api_data, dict) else None),
            "application_multiple": get_val(["minimum application amount in multiples", "min. application amount in multiples of", "minimum application amount in multiples of rs.", "application multiple", "in multiple of", "in multiples of"]),
            "minimum_additional_amount": get_val(["minimum additional amount", "min. additional amount"]),
            "additional_multiple": get_val(["minimum additional amount in multiples", "min. additional amount in multiples of", "minimum additional amount in multiples of rs.", "additional multiple"]),
            "minimum_redemption_amount": get_val(["minimum redemption amount in rs.", "minimum redemption amount in rs", "minimum redemption amount", "min. redemption amount"]),
            "minimum_redemption_units": get_val(["minimum redemption amount in units", "minimum redemption units", "min. redemption units"]),
            "minimum_balance_amount": get_val(["minimum balance amount (if applicable)", "min. balance amount (if applicable)", "minimum balance amount"]),
            "minimum_balance_units": get_val(["minimum balance amount in units (if applicable)", "min. balance amount in units (if applicable)", "minimum balance amount in units"]),
            "maximum_investment_amount": get_val(["max investment amount", "max. investment amount", "maximum amount (if any)", "max. amounts (if any)"])
        },

        "switch_details": {
            "minimum_switch_amount": get_val(["minimum switch amount (if applicable)", "min. switch amount (if applicable)", "minimum switch amount"]),
            "minimum_switch_units": get_val(["minimum switch units", "min. switch units"]),
            "switch_multiple_amount": get_val(["switch multiple amount (if applicable)", "switch multiple amount"]),
            "switch_multiple_units": get_val(["switch multiple units (if applicable)", "switch multiple units"]),
            "maximum_switch_amount": get_val(["max switch amount", "max. switch amount"]),
            "maximum_switch_units": get_val(["max switch units (if applicable)", "max switch unit (if applicable)", "max. switch units (if applicable)"])
        },

        "systematic_investment_plans": {
            "frequency": get_val(["sip swp & stp details: frequency", "frequency"]),
            "minimum_amount": get_val(["sip swp & stp details: minimum amount", "sip details", "stp details", "swp details"]),
            "in_multiples_of": get_val(["sip swp & stp details: in multiple of"]),
            "minimum_installments": get_val(["sip swp & stp details: minimum instalments", "minimum instalments", "min. installments"]),
            "dates": get_val(["sip swp & stp details: dates", "dates"]),
            "maximum_amount": get_val(["sip swp & stp details: maximum amount (if any)"])
        },

        "expenses_and_loads": {
            "exit_load": get_val(["exit load (if applicable)", "exit load"]) or (api_data.get("scheme_load") if isinstance(api_data, dict) else None) or (api_data.get("Scheme_Load") if isinstance(api_data, dict) else None),
            "actual_expense": get_val(["annual expense (actual expenses)", "actual expense", "annual expense (actual expenses) as on august 31, 2026"]),
            "stated_maximum_expense": get_val(["annual expense (stated maximum)", "annual expense (stated max)"])
        },

        "special_facilities": {
            "swing_pricing": get_val(["swing pricing (if applicable)", "swing pricing"]),
            "side_pocketing": get_val(["side-pocketing (if applicable)", "side-pocketing", "segragated portfolio (if applicable)", "segregated portfolio"])
        },

        "amc_details": {
            "sif_name": (api_data.get("SIF_Name") if isinstance(api_data, dict) else None) or (api_data.get("sif_name") if isinstance(api_data, dict) else None),
            "amc_website": (api_data.get("AMC_Website") if isinstance(api_data, dict) else None) or (api_data.get("amc_website") if isinstance(api_data, dict) else None),
            "scheme_bonus": (api_data.get("Scheme_Bonus") if isinstance(api_data, dict) else None) or (api_data.get("scheme_bonus") if isinstance(api_data, dict) else None)
        },

        "exit_load": get_val(["exit load (if applicable)", "exit load"]) or (api_data.get("scheme_load") if isinstance(api_data, dict) else None) or (api_data.get("Scheme_Load") if isinstance(api_data, dict) else None),
        "registrar": get_val(["registrar"]),
        "custodian": get_val(["custodian"]),
        "auditor": get_val(["auditor"])
    }

    return result, primary_amfi_code
