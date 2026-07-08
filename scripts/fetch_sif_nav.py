import requests
import json
import pandas as pd
import os

def fetch_sif_nav():
    url = "https://www.amfiindia.com/api/sif-latest-nav?type="
    
    try:
        print(f"Fetching data from {url}...")
        response = requests.get(url, timeout=10)
        
        # Verify that the response status is 200
        if response.status_code == 200:
            print("Response status is 200 OK.")
            
            # Parse the returned JSON
            try:
                data = response.json()
                print("Extracting schemes into a list...")
                all_schemes = []
                
                # The JSON structure is nested: data -> categories -> groups -> schemes
                for data_item in data.get("data", []):
                    for category in data_item.get("categories", []):
                        for group in category.get("groups", []):
                            for scheme in group.get("schemes", []):
                                all_schemes.append(scheme)
                
                print(f"Successfully extracted {len(all_schemes)} schemes.")
                return all_schemes
                
            except json.JSONDecodeError:
                print("Error: Failed to parse JSON response. The server may have returned invalid JSON.")
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("Error: The request timed out.")
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to the server.")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected request error occurred: {e}")
    except Exception as e:
        print(f"An unexpected system error occurred: {e}")

def save_to_csv(schemes):
    """
    Converts a list of scheme dictionaries into a pandas DataFrame and saves it to a CSV file.
    """
    try:
        print("Converting list to pandas DataFrame...")
        df = pd.DataFrame(schemes)
        
        # Check and create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        file_path = "data/sif_nav.csv"
        print(f"Saving DataFrame to {file_path}...")
        df.to_csv(file_path, index=False)
        print("Successfully saved data to CSV.")
        
    except Exception as e:
        print(f"Error while saving to CSV: {e}")

if __name__ == "__main__":
    schemes_list = fetch_sif_nav()
    if schemes_list:
        save_to_csv(schemes_list)
