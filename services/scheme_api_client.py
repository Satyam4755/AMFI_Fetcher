import json
import urllib.request
import urllib.error

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Connection": "close",
}

def _get_json(url: str, timeout: int = 10):
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        try:
            import requests
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        print(f"API Request failed for {url}: {e}")
    return None

def fetch_all_sifs():
    """Fetches the complete list of all SIFs from AMFI."""
    url = "https://www.amfiindia.com/api/populate-sif"
    data = _get_json(url)
    return data if isinstance(data, list) else []

def fetch_investment_strategies(sif_id):
    """Calls the AMFI populate-investment-strategy API for a specific SIF."""
    url = f"https://www.amfiindia.com/api/populate-investment-strategy?sif_id={sif_id}"
    return _get_json(url)

def fetch_scheme_detail(sif_id, scheme_id):
    """Calls the AMFI investment-strategy-detail API for a specific scheme."""
    url = f"https://www.amfiindia.com/api/investment-strategy-detail?sif_id={sif_id}&scheme_id={scheme_id}"
    return _get_json(url)
