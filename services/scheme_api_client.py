import requests

def fetch_all_sifs():
    """
    Fetches the complete list of all SIFs from AMFI.
    """
    url = "https://www.amfiindia.com/api/populate-sif"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"API Request failed for populate-sif: {e}")
    return []

def fetch_investment_strategies(sif_id):
    """
    Calls the AMFI populate-investment-strategy API for a specific SIF.
    Returns the JSON response.
    """
    url = f"https://www.amfiindia.com/api/populate-investment-strategy?sif_id={sif_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"API Request failed for populate-investment-strategy sif_id={sif_id}: {e}")
    return None

def fetch_scheme_detail(sif_id, scheme_id):
    """
    Calls the AMFI investment-strategy-detail API for a specific scheme.
    """
    url = f"https://www.amfiindia.com/api/investment-strategy-detail?sif_id={sif_id}&scheme_id={scheme_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"API Request failed for investment-strategy-detail sif_id={sif_id}, scheme_id={scheme_id}: {e}")
    return None
