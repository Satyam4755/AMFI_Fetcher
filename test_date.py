import re
from datetime import datetime

def normalize_date(d_str):
    if not d_str: return None
    d_clean = str(d_str).strip()
    if re.search(r'(?i)^(NA|N\.A\.|N/A|-|TBD)$', d_clean) or not d_clean:
        return None
        
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
            
    # If all formats fail, return raw string to avoid data loss
    return d_clean

print(normalize_date("30-Mar-2026"))
print(normalize_date("2026-04-15"))
print(normalize_date("15/04/2026"))
print(normalize_date("NA"))
print(normalize_date("Some Weird Date"))
