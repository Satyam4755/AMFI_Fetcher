import json
import urllib.request
import urllib.error

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,application/json,*/*",
    "Connection": "close",
}

def fetch_text(url, timeout=10):
    """Fetches text data from the given URL."""
    try:
        print(f"Fetching data from {url}...")
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                print("Response status is 200 OK.")
                return resp.read().decode("utf-8", errors="ignore")
            else:
                print(f"Failed to fetch data. Status code: {resp.status}")
                return None
    except Exception as e:
        try:
            import requests
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if response.status_code == 200:
                print("Response status is 200 OK.")
                return response.text
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
        except Exception:
            pass
        print(f"Error occurred fetching text: {e}")
        return None

def fetch_json(url, timeout=10):
    """Fetches JSON data from the given URL."""
    try:
        print(f"Fetching data from {url}...")
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                print("Response status is 200 OK.")
                return json.loads(resp.read().decode("utf-8"))
            else:
                print(f"Failed to fetch data. Status code: {resp.status}")
                return None
    except Exception as e:
        try:
            import requests
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if response.status_code == 200:
                print("Response status is 200 OK.")
                return response.json()
            else:
                print(f"Failed to fetch data. Status code: {response.status_code}")
                return None
        except Exception:
            pass
        print(f"Error occurred fetching JSON: {e}")
        return None
