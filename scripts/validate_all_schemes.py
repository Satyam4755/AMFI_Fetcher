import sys
import os
import json
import re
import glob

# Allow direct execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_api_client import fetch_all_sifs, fetch_investment_strategies
from services.xls_parser_service import parse_summary_xls

from services.scheme_api_client import fetch_scheme_detail

def get_sebi_to_scheme_mapping():
    sif_list = fetch_all_sifs()
    if not sif_list:
        return {}
        
    def normalize_name(name):
        return re.sub(r'[\s\-]+', '', name.lower()) if name else ""

    mapping = {}
    for sif in sif_list:
        strategies = fetch_investment_strategies(sif['SIF_Id'])
        for strat in strategies:
            scheme_id = strat.get('scheme_id')
            scheme_name = strat.get('scheme_name')
            if scheme_id and scheme_name:
                mapping[normalize_name(scheme_name)] = scheme_id
    return mapping

def extract_expected_identifiers(rows):
    # Extracts all AMFI, ISIN, and RTA codes using the raw regex from the XLS rows.
    amfi_set = set()
    isin_set = set()
    rta_set = set()
    
    amfi_pattern = re.compile(r'\b(?:SIF|S)[-\s]*\d+\b', re.IGNORECASE)
    isin_pattern = re.compile(r'\bINF[A-Z0-9]{8}[0-9]', re.IGNORECASE)
    # RTA is harder to regex generically, but we can look for typical RTAs: ETD\d+, ETRD, etc.
    # If we want a strict validation, maybe we use the parser's RTA column.
    
    # Let's iterate over rows and extract cells
    rta_pattern = re.compile(r'\b(?:ETRD|ETD\d+|KFIN\d+|CAMS\d+)\b', re.IGNORECASE)
    
    for row in rows:
        for key, val in row.items():
            if not isinstance(val, str):
                continue
            text = val
            amfi_matches = amfi_pattern.findall(text)
            for m in amfi_matches: amfi_set.add(m.strip().upper().replace(" ", ""))
            
            isin_matches = isin_pattern.findall(text)
            for m in isin_matches: isin_set.add(m.strip().upper())
                
            rta_matches = rta_pattern.findall(text)
            for m in rta_matches: rta_set.add(m.strip().upper())
                
    return amfi_set, isin_set, rta_set

def collect_assigned_identifiers(plans, actual_amfi, actual_isin, actual_rta, duplicates_found):
    # Recursive function to gather all amfi, isin, rta from the JSON plans
    if isinstance(plans, list):
        for item in plans:
            collect_assigned_identifiers(item, actual_amfi, actual_isin, actual_rta, duplicates_found)
    elif isinstance(plans, dict):
        # Base case: Node is an actual plan item
        if "plan_type" in plans and "name" in plans:
            # Check for AMFI
            amfi = plans.get("amfi_code")
            if amfi:
                amfi = amfi.strip().upper().replace(" ", "")

                actual_amfi.add(amfi)
            # Check for ISIN
            isin = plans.get("isin_code")
            if isin:
                isin = isin.strip().upper()

                actual_isin.add(isin)
            # Check for RTA
            rta = plans.get("rta_code")
            if rta:
                rta = rta.strip().upper()

                actual_rta.add(rta)
        else:
            for k, v in plans.items():
                collect_assigned_identifiers(v, actual_amfi, actual_isin, actual_rta, duplicates_found)

def validate_json_file(json_file_path, mapping):
    def normalize_name(name):
        return re.sub(r'[\s\-]+', '', name.lower()) if name else ""

    with open(json_file_path, "r") as f:
        data = json.load(f)
        
    fund_name = data.get('fund_name')
    scheme_id = mapping.get(normalize_name(fund_name)) if fund_name else None
    
    if not scheme_id:
        return "FAIL", f"Could not find scheme_id for SEBI code: {fund_name}"
        
    xls_path = f"temp/xls/SSD_{scheme_id}.xls"
    if not os.path.exists(xls_path):
        return "FAIL", f"Source XLS not found: {xls_path}"
        
    # Read source
    try:
        rows = parse_summary_xls(xls_path)
    except Exception as e:
        return "FAIL", f"Could not parse XLS: {e}"
        
    expected_amfi, expected_isin, expected_rta = set(), set(), set()
    for sheet_name, sheet_rows in rows.items():
        if isinstance(sheet_rows, list):
            a, i, r = extract_expected_identifiers(sheet_rows)
            expected_amfi.update(a)
            expected_isin.update(i)
            expected_rta.update(r)
    
    # Read JSON
    plans = data.get("plans", {})
    actual_amfi, actual_isin, actual_rta = set(), set(), set()
    duplicates = []
    collect_assigned_identifiers(plans, actual_amfi, actual_isin, actual_rta, duplicates)
    
    reasons = []
    
    # 1. Check counts
    if len(expected_amfi) != len(actual_amfi):
        reasons.append(f"AMFI Count Mismatch (Expected: {len(expected_amfi)}, Actual: {len(actual_amfi)})")
    if len(expected_isin) != len(actual_isin):
        reasons.append(f"ISIN Count Mismatch (Expected: {len(expected_isin)}, Actual: {len(actual_isin)})")
        
    # 2. Check for missing / orphan
    missing_amfi = expected_amfi - actual_amfi
    orphan_amfi = actual_amfi - expected_amfi
    if missing_amfi: reasons.append(f"Missing AMFI: {missing_amfi}")
    if orphan_amfi: reasons.append(f"Orphan AMFI: {orphan_amfi}")
    
    missing_isin = expected_isin - actual_isin
    orphan_isin = actual_isin - expected_isin
    if missing_isin: reasons.append(f"Missing ISIN: {missing_isin}")
    if orphan_isin: reasons.append(f"Orphan ISIN: {orphan_isin}")
    
    # 3. Duplicates
    if duplicates:
        # Check if the duplicate was intentional (e.g. payout and reinvestment sharing an AMFI)
        # We will log it, but wait, the instruction says "Verify every identifier appears exactly once unless intentional duplication is required".
        # We can just check if any duplicates exist and flag them to be sure.
        reasons.append(f"Duplicate identifiers assigned: {set(duplicates)}")
        
    # 4. Unknown / Unresolved
    # Traverse to see if there are any nodes in unknown or unresolved
    unknowns_found = []
    unresolved_found = []
    
    # plans -> unresolved
    if plans.get("unresolved"):
        unresolved_found.extend(plans["unresolved"])
        
    # unknowns inside regular/direct -> idcw -> unknown
    for ptype in ["regular", "direct"]:
        ptype_node = plans.get(ptype, {})
        idcw_node = ptype_node.get("idcw", {})
        unk = idcw_node.get("unknown", [])
        if unk:
            unknowns_found.extend(unk)
            
    if unknowns_found:
        reasons.append(f"Records found in 'unknown': {len(unknowns_found)} records")
    if unresolved_found:
        reasons.append(f"Records found in 'unresolved': {len(unresolved_found)} records")
        
    if reasons:
        return "FAIL", "; ".join(reasons)
    return "PASS", ""

def main():
    print("Loading SEBI to Scheme mapping from API...")
    mapping = get_sebi_to_scheme_mapping()
    
    json_files = glob.glob("data/sif/scheme/details/*.json")
    # Exclude basic json files (which have name s_XX.json)
    json_files = [f for f in json_files if re.match(r'.*_[a-z0-9]{4}\.json', f)]
    
    print(f"\nValidating {len(json_files)} schemes...\n")
    
    results = []
    pass_count = 0
    fail_count = 0
    
    for j_path in sorted(json_files):
        with open(j_path, "r") as f:
            d = json.load(f)
            fund_name = d.get("fund_name", "Unknown Scheme")
            
        status, reason = validate_json_file(j_path, mapping)
        
        results.append((fund_name, status, reason))
        if status == "PASS":
            pass_count += 1
        else:
            fail_count += 1
            
    # Print Report
    print(f"{'Scheme':<50} {'Result'}")
    print("-" * 60)
    for name, status, reason in results:
        name_short = name[:45] + "..." if len(name) > 48 else name
        print(f"{name_short:<50} {status}")
        if status == "FAIL":
            print(f"   -> Reason: {reason}")
            
    print("\nSummary")
    print("-" * 10)
    print(f"PASS : {pass_count}")
    print(f"FAIL : {fail_count}")

if __name__ == "__main__":
    main()
