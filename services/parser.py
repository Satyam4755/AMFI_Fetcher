def extract_schemes(data):
    """Parses AMFI NAV text data into a flat list of schemes."""
    if not data:
        return None
        
    print("Extracting schemes into a list...")
    all_schemes = []
    
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
                scheme = {
                    "sif_code": parts[code_idx],
                    "nav_date": parts[date_idx],
                    "nav": parts[nav_idx]
                }
                all_schemes.append(scheme)
                
        print(f"Successfully extracted {len(all_schemes)} schemes.")
        return all_schemes
    except Exception as e:
        print(f"Error during parsing: {e}")
        return None
