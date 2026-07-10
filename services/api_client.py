import requests
import requests

def fetch_text(url):
    """Fetches text data from the given URL."""
    try:
        print(f"Fetching data from {url}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("Response status is 200 OK.")
            return response.text
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        return None
    except Exception as e:
        print(f"System error occurred: {e}")
        return None

def fetch_json(url):
    """Fetches JSON data from the given URL."""
    try:
        print(f"Fetching data from {url}...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("Response status is 200 OK.")
            return response.json()
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        return None
    except Exception as e:
        print(f"System error occurred: {e}")
        return None
