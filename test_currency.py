import json
import glob
import re

def parse_currency(val_str):
    if not val_str:
        return 0.0
    val = str(val_str).lower().replace(',', '')
    match = re.search(r'\d+(\.\d+)?', val)
    if match:
        num = float(match.group(0))
        if re.search(r'\b(lakh|lakhs|lac|lacs)\b', val):
            num *= 100000
        elif re.search(r'\b(cr|crore|crores)\b', val):
            num *= 10000000
            
        # Add a sanity check if the number is gigantic > 100 Cr (1,000,000,000)
        # Fallback to 1,000,000 (10 Lakh) as per business rules
        if num > 1000000000 or num <= 0:
            return 1000000.0
            
        return num
    return 1000000.0 # Return 1000000 if no match but we had a string (parsing failed)

for f in glob.glob('/Users/smritisoni/Desktop/My_SIF/AMFI_Fetcher_clone/data/sif/scheme/details/*.json'):
    with open(f) as fp:
        data = json.load(fp)
        min_sub = data.get('investment_limits', {}).get('minimum_application_amount')
        parsed = parse_currency(min_sub)
        if parsed >= 1000000000 or parsed == 1000000.0:
             pass
        print(f"{min_sub} => {parsed}")

