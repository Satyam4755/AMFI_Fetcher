import json
import urllib.request
import urllib.error

def fetch_text(url):
    """Fetches text data from the given URL."""
    try:
        print(f"Fetching data from {url}...")
        try:
            import requests
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                print("Response status is 200 OK.")
                return response.text
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
        except ImportError:
            pass
            
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print("Response status is 200 OK.")
                return resp.read().decode("utf-8", errors="ignore")
            else:
                print(f"Failed to fetch data. Status code: {resp.status}")
                return None
    except Exception as e:
        print(f"Error occurred fetching text: {e}")
        return None

def fetch_json(url):
    """Fetches JSON data from the given URL."""
    try:
        print(f"Fetching data from {url}...")
        try:
            import requests
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                print("Response status is 200 OK.")
                return response.json()
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
        except ImportError:
            pass
            
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print("Response status is 200 OK.")
                return json.loads(resp.read().decode("utf-8"))
            else:
                print(f"Failed to fetch data. Status code: {resp.status}")
                return None
    except Exception as e:
        print(f"Error occurred fetching JSON: {e}")
        return None
