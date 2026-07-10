import sys
import os
import json
sys.path.append(os.getcwd())
from services.scheme_api_client import fetch_investment_strategies
res = fetch_investment_strategies("15")
print(json.dumps(res, indent=2))
