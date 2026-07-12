import os

def update_historical_nav(schemes, base_dir="data/sif/scheme/nav/historical"):
    """
    Updates or creates historical NAV CSV files per SIF.
    Format is data/sif/scheme/nav/historical/sif_x.csv with columns sif_code,nav_date,nav.
    """
    if not schemes:
        return
        
    print(f"Updating historical NAV files in {base_dir}...")
    
    # Ensure directory exists
    os.makedirs(base_dir, exist_ok=True)
    
    for scheme in schemes:
        sif_code = scheme.get("sif_code")
        nav_date = scheme.get("nav_date")
        nav_val = scheme.get("nav")
        
        if not sif_code or not nav_date:
            continue
            
        # Convert SIF-120 to sif_120.csv
        safe_name = sif_code.lower().replace("-", "_")
        filename = f"{safe_name}.csv"
        filepath = os.path.join(base_dir, filename)
        
        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists(filepath)
        
        if file_exists:
            # Check for duplicate dates
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # If date is already in the file, skip
                if f"{nav_date}," in content:
                    continue
        
        # Append the new row
        with open(filepath, 'a', encoding='utf-8') as f:
            if not file_exists:
                f.write("sif_code,nav_date,nav\n")
            f.write(f"{sif_code},{nav_date},{nav_val}\n")
            
    print("Historical NAV files updated successfully.")
