import re
import json

plans = {
    "regular": {
        "growth": {},
        "idcw": { "payout": {}, "reinvestment": {}, "transfer": {} }
    },
    "direct": {
        "growth": {},
        "idcw": { "payout": {}, "reinvestment": {}, "transfer": {} }
    }
}

def classify_plan(name_str):
    name_lower = name_str.lower()
    if "direct" in name_lower: plan_type = "direct"
    else: plan_type = "regular"
    
    if "growth" in name_lower:
        return (plan_type, "growth", None)
    else:
        if "reinvest" in name_lower: subtype = "reinvestment"
        elif "transfer" in name_lower: subtype = "transfer"
        else: subtype = "payout"
        return (plan_type, "idcw", subtype)

def get_plan_ref(classification):
    plan_type, category, subtype = classification
    if category == "growth": return plans[plan_type]["growth"]
    else: return plans[plan_type]["idcw"][subtype]

def extract_code_and_name(line):
    # e.g. "1. Growth Option - Direct Plan - SIF-1"
    # e.g. "1. Growth Option - Regular Plan -INF966L30027"
    # Remove leading numbering like "1.", "2)", etc.
    line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
    
    parts = line.split('-')
    if len(parts) > 1:
        # Check if the last part looks like a code (e.g. SIF-X, INF..., or just no spaces)
        last_part = parts[-1].strip()
        if re.match(r'^(SIF|INF|S)\S*', last_part, re.IGNORECASE) or ' ' not in last_part:
            # Reconstruct name from the rest
            if len(parts) >= 3 and re.match(r'^(SIF|S)\b', parts[-2].strip() + "-" + last_part, re.IGNORECASE):
                 code = parts[-2].strip() + "-" + last_part
                 name = "-".join(parts[:-2]).strip()
            else:
                 code = last_part
                 name = "-".join(parts[:-1]).strip()
            return name, code
    return line, None

lines = [
    "1. Growth Option - Direct Plan - SIF-1",
    "2. IDCW Option - Direct Plan - SIF-2",
    "1. Growth Option - Regular Plan -INF966L30027",
    "5. IDCW Reinvestment - Regular Plan - INF966L30068",
    "qsif Equity Long-Short Fund - Growth Option – Direct Plan"
]

for line in lines:
    # replace en dash with hyphen
    line = line.replace('–', '-')
    name, code = extract_code_and_name(line)
    cls = classify_plan(name)
    ref = get_plan_ref(cls)
    
    if "name" not in ref or len(name) > len(ref["name"]):
        ref["name"] = name
    
    if code:
        if code.startswith("INF"): ref["isin_code"] = code
        elif code.startswith("SIF") or code.startswith("S-"): ref["amfi_code"] = code
        else: ref["rta_code"] = code

print(json.dumps(plans, indent=2))
