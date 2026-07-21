import re
import json

def parse_asset_allocation(text):
    if not text: return None
    allocations = []
    
    # Simple regex to find <Name> - <Min> to <Max> OR <Name> <Min> to <Max>
    # It must handle percentages that might have decimal points.
    pattern = r'([A-Za-z\s]+?)\s*(?:-)?\s*(\d+(?:\.\d+)?)%?\s*(?:to|-)\s*(\d+(?:\.\d+)?)%?'
    
    matches = list(re.finditer(pattern, str(text), re.IGNORECASE))
    
    if not matches:
        # If no strict range patterns match, try splitting by newline/comma
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
        # Clean up any leading junk from previous match if they were joined
        name = re.sub(r'^[\s,;]+', '', name)
        allocations.append({
            "allocation_type": name,
            "minimum_percentage": float(m.group(2)) if '.' in m.group(2) else int(m.group(2)),
            "maximum_percentage": float(m.group(3)) if '.' in m.group(3) else int(m.group(3))
        })
        
    return allocations

print(json.dumps(parse_asset_allocation("Equity and Equity Related Instruments - 80% to 100%\nInvestments in Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equity - 80% to 100%, Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equity - 80% to 100% Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equities 80 to 100%, Money Market 0 to 20"), indent=2))

