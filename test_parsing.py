import re
import json

def parse_asset_allocation(text):
    if not text: return None
    allocations = []
    # e.g., "Equity and Equity Related Instruments - 80% to 100%\nInvestments in Debt - 0% to 20%"
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        # Regex to capture name and percentages
        m = re.search(r'^(.*?)\s*-\s*(\d+)%?\s*(?:to|-)\s*(\d+)%?$', line)
        if m:
            allocations.append({
                "allocation_type": m.group(1).strip(),
                "minimum_percentage": int(m.group(2)),
                "maximum_percentage": int(m.group(3))
            })
        else:
            # Maybe it doesn't match perfectly, just save raw
            allocations.append({
                "allocation_type": line,
                "minimum_percentage": None,
                "maximum_percentage": None
            })
    return allocations

print("Asset Allocation Test:")
aa = "Equity and Equity Related Instruments - 80% to 100%\nInvestments in Debt and Money Market instruments - 0% to 20%\nInvestments in units issued by InvITs - 0% to 20%"
print(json.dumps(parse_asset_allocation(aa), indent=2))

def parse_fund_managers(fm_names_raw, fm_types_raw, fm_dates_raw, fm_todates_raw=""):
    fm_names = [l.strip() for l in fm_names_raw.split('\n') if l.strip()] if fm_names_raw else []
    fm_types = [l.strip() for l in fm_types_raw.split('\n') if l.strip()] if fm_types_raw else []
    fm_froms = [l.strip() for l in fm_dates_raw.split('\n') if l.strip()] if fm_dates_raw else []
    fm_tos   = [l.strip() for l in fm_todates_raw.split('\n') if l.strip()] if fm_todates_raw else []
    
    # Try to parse by prefix
    def extract_prefix(text):
        m = re.match(r'^(.*?)\s*-\s*(.*)$', text)
        if m:
            prefix = m.group(1).strip()
            # If the prefix is too long, it's not a prefix
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
        if key in records_dict: records_dict[key]["from"] = val
        
    for l in fm_tos:
        pref, val = extract_prefix(l)
        key = pref if pref else "default"
        if key in records_dict: records_dict[key]["to"] = val
        
    # If dict keys are not matching well (e.g. they didn't have prefixes), fallback to positional
    # if lengths match perfectly
    if (not any(records_dict[k]["name"] for k in records_dict if k != "default")) and len(fm_names) > 1 and len(fm_names) == len(fm_types) == len(fm_froms):
        records = []
        for i in range(len(fm_names)):
            records.append({
                "name": fm_names[i],
                "type": fm_types[i] if i < len(fm_types) else "",
                "from": fm_froms[i] if i < len(fm_froms) else "",
                "to": fm_tos[i] if i < len(fm_tos) else None,
                "role_or_portion": None
            })
        return records

    # Else use the dict
    records = list(records_dict.values())
    
    return records

print("\nFund Manager Test:")
print(json.dumps(parse_fund_managers(
    "Equity Portion: FM 1 - Mr. Nilesh Saha\nDebt Portion: FM 1 - Mr. Brijesh Shah",
    "Equity Portion: FM 1 - Comanage\nDebt Portion: FM 1 - Comanage",
    "Equity Portion: FM 1 - 30-Mar-2026\nDebt Portion: FM 1 - 30-Mar-2026"
), indent=2))

def normalize_date(d_str):
    if not d_str: return None
    
    try:
        # Avoid things like 'NA', 'N.A.', '-', empty
        d_clean = d_str.strip()
        if re.search(r'(?i)^(NA|N\.A\.|N/A|-|TBD)$', d_clean): return None
        # Parse it
        parsed = dateutil.parser.parse(d_clean, dayfirst=True)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return d_str

print("\nDate Test:")
print(normalize_date("30-Mar-2026"))
print(normalize_date("NA"))
print(normalize_date("2026/04/15"))

