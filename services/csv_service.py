import pandas as pd
import os

def save_to_csv(schemes, file_path):
    """Converts a list of dictionaries into a pandas DataFrame and saves to CSV."""
    if not schemes:
        print("No schemes provided to save.")
        return False
        
    try:
        print("Converting list to pandas DataFrame...")
        df = pd.DataFrame(schemes)
        
        # Check and create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        print(f"Saving DataFrame to {file_path}...")
        df.to_csv(file_path, index=False)
        print("Successfully saved data to CSV.")
        return True
    except Exception as e:
        print(f"Error while saving to CSV: {e}")
        return False
