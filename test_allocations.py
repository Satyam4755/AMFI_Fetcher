import re
import json

def parse_asset_allocation(text):
    if not text: return None
    allocations = []
    
    # Sometimes it's one line, sometimes multiple, sometimes separated by commas.
    # Replace commas with newlines if they are used to separate entries, but it's risky if the name has a comma.
    # We can split by newline first. If there are no newlines, maybe split by comma if we see "%" before the comma.
    # Actually, a safer way to find entries is using a regex that looks for:
    # <Name> - <Min>% to <Max>%
    
    # Clean up bullet points, tabs
    text = re.sub(r'[\u2022\u25E6\u2023\u25B8\u25B9\u2043\u2219\uf0b7\t]+', '\n', str(text))
    
    # If the text is on a single line like: "Equity - 80% to 100%, Debt - 0% to 20%"
    # Let's replace commas with newlines ONLY IF they are followed by a word and preceded by a % or digit
    text = re.sub(r'(%\s*),(\s*[A-Z])', r'\1\n\2', text)
    
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
            # Maybe there are multiple entries on the same line that aren't comma separated?
            # E.g. "Equity - 80% to 100% Debt - 0% to 20%"
            # Let's see if we can find all matches
            matches = re.findall(r'(.*?)\s*-\s*(\d+)%?\s*(?:to|-)\s*(\d+)%?', line)
            if matches and len(matches) > 1:
                # The first match's name might have junk before it or be merged
                for match in matches:
                    allocations.append({
                        "allocation_type": match[0].strip(),
                        "minimum_percentage": int(match[1]),
                        "maximum_percentage": int(match[2])
                    })
            else:
                # Fallback to raw line
                allocations.append({
                    "allocation_type": line,
                    "minimum_percentage": None,
                    "maximum_percentage": None
                })
    return allocations

print(json.dumps(parse_asset_allocation("Equity and Equity Related Instruments - 80% to 100%\nInvestments in Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equity - 80% to 100%, Debt - 0% to 20%"), indent=2))
print(json.dumps(parse_asset_allocation("Equity - 80% to 100% Debt - 0% to 20%"), indent=2))

