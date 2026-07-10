def extract_schemes(data):
    """Parses AMFI NAV text data into a flat list of schemes."""
    if not data:
        return None
        
    print("Extracting schemes into a list...")
    all_schemes = []
    
    try:
        lines = data.splitlines()
        for line in lines:
            line = line.strip()
            # Skip empty lines, headers, or section titles
            if not line or line.startswith("Scheme Code") or ";" not in line:
                continue
                
            parts = line.split(";")
            if len(parts) >= 6:
                scheme = {
                    "sif_code": parts[0].strip(),
                    "nav_date": parts[5].strip(),
                    "nav": parts[4].strip()
                }
                all_schemes.append(scheme)
                
        print(f"Successfully extracted {len(all_schemes)} schemes.")
        return all_schemes
    except Exception as e:
        print(f"Error during parsing: {e}")
        return None
