import re
import json

def parse_asset_allocation(text):
    if not text: return None
    allocations = []
    
    text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\t]+', '\n', str(text))
    
    # Replace commas followed by space and letter if preceded by % or digit
    text = re.sub(r'(%\s*),(\s*[A-Z])', r'\1\n\2', text)
    
    # If multiple entries are on the same line (e.g. "Equity - 80% to 100% Debt - 0% to 20%")
    # Let's inject a newline after the Max percentage if it's followed by letters
    text = re.sub(r'(\d+%?)\s+(?=[A-Za-z])', r'\1\n', text)
    
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        m = re.search(r'^(.*?)\s*-\s*(\d+)(?:\.\d+)?%?\s*(?:to|-)\s*(\d+)(?:\.\d+)?%?$', line, re.IGNORECASE)
        if m:
            allocations.append({
                "allocation_type": m.group(1).strip(),
                "minimum_percentage": int(m.group(2)),
                "maximum_percentage": int(m.group(3))
            })
        else:
            allocations.append({
                "allocation_type": line,
                "minimum_percentage": None,
                "maximum_percentage": None
            })
    return allocations

print(json.dumps(parse_asset_allocation("Equity and Equity Related Instruments - 80% to 100%\nInvestments in Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equity - 80% to 100%, Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equity - 80% to 100% Debt - 0% to 20%"), indent=2))
