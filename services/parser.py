import re
from datetime import datetime

def _parse_date_helper(val):
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def extract_schemes(data):
    """Parses AMFI NAV text data into a flat list of schemes."""
    if not data:
        return None
        
    print("Extracting schemes into a list...")
    scheme_map = {}
    scheme_order = []
    
    try:
        lines = data.splitlines()
        
        # Default indices (pre-Aug 19)
        code_idx = 0
        nav_idx = 4
        date_idx = 5
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
                
            # Process header line and update indices dynamically
            if line.startswith("Scheme Code"):
                headers = [h.strip() for h in line.split(";")]
                try:
                    code_idx = headers.index("Scheme Code")
                    nav_idx = headers.index("Net Asset Value")
                    date_idx = headers.index("Date")
                except ValueError:
                    print(f"Warning: Expected headers not found exactly. Using code:{code_idx} nav:{nav_idx} date:{date_idx}")
                continue
                
            # Skip section titles or invalid lines
            if ";" not in line:
                continue
                
            parts = [p.strip() for p in line.split(";")]
            
            if len(parts) > max(code_idx, nav_idx, date_idx):
                code = parts[code_idx].strip()
                date_val = parts[date_idx].strip()
                nav_val = parts[nav_idx].strip()
                
                if not code:
                    continue
                    
                scheme = {
                    "sif_code": code,
                    "nav_date": date_val,
                    "nav": nav_val
                }
                
                if code not in scheme_map:
                    scheme_order.append(code)
                    scheme_map[code] = scheme
                else:
                    # If duplicate scheme code is found, retain the one with the newer valid date
                    prev_dt = _parse_date_helper(scheme_map[code].get("nav_date"))
                    curr_dt = _parse_date_helper(date_val)
                    if curr_dt and (not prev_dt or curr_dt >= prev_dt):
                        scheme_map[code] = scheme
                
        all_schemes = [scheme_map[c] for c in scheme_order]
        print(f"Successfully extracted {len(all_schemes)} schemes.")
        return all_schemes
    except Exception as e:
        print(f"Error during parsing: {e}")
        return None
