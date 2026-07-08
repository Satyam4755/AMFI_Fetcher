import requests
import json

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
                # Pretty-print the JSON to the terminal
                print("\n--- JSON Data ---")
                first = data["data"][0]

                print(first["type"])
                print(type(first["categories"]))
                print(len(first["categories"]))
                category = data["data"][0]["categories"][0]
                
                for key, value in category.items():
                    print(key, ":", type(value))
                
                print("Number of groups: ", len(category["groups"]))
                group = category["groups"][0]

                print(group["SIFName"])
                print(type(group["schemes"]))
                print(len(group["schemes"]))
                print(group["schemes"][0].keys())
                print("-----------------")
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

if __name__ == "__main__":
    fetch_sif_nav()
