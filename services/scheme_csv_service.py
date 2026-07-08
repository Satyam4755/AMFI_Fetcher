import pandas as pd
import os

def save_schemes_to_csv(schemes):
    """
    Saves a list of scheme dictionaries to data/sif_scheme.csv using pandas.
    """
    if not schemes:
        print("No schemes to save to CSV.")
        return False
        
    try:
        # Create data folder if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Convert to DataFrame
        df = pd.DataFrame(schemes)
        
        # Save to CSV
        csv_path = "data/sif_scheme.csv"
        df.to_csv(csv_path, index=False)
        
        print(f"Successfully saved {len(schemes)} schemes to {csv_path}")
        return True
    except Exception as e:
        print(f"Failed to save scheme CSV: {e}")
        return False
