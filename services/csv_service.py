import csv
import os

def save_to_csv(schemes, file_path):
    """Converts a list of dictionaries into CSV with standard columns."""
    if not schemes:
        print("No schemes provided to save.")
        return False
        
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Determine column order: sif_code, nav_date, nav, [AUM], [others]
        standard_cols = ["sif_code", "nav_date", "nav"]
        has_aum = any("AUM" in s for s in schemes)
        if has_aum:
            standard_cols.append("AUM")
            
        # Collect any other unique keys
        all_keys = []
        for s in schemes:
            for k in s.keys():
                if k not in standard_cols and k not in all_keys:
                    all_keys.append(k)
                    
        fieldnames = standard_cols + all_keys
        
        print(f"Saving {len(schemes)} schemes to {file_path} with columns {fieldnames}...")
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(schemes)
            
        print("Successfully saved data to CSV.")
        return True
    except Exception as e:
        print(f"Error while saving to CSV: {e}")
        return False
