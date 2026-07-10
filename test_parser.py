import json
from services.scheme_parser import build_scheme_json

def test():
    # Let's mock a row from Altiva that caused 'Short Fund Regular Plan IDCW Reinvestment' to be an AMFI code
    # We will simulate the Excel row data
    # Actually, let's just trace how `code` can be assigned.
    
    rows = [
        {"0": "1", "1": "AMFI Codes", "2": "Short Fund Regular Plan IDCW Reinvestment"},
        {"0": "2", "1": "Option Names", "2": "Short Fund Regular Plan IDCW Reinvestment"},
        {"0": "3", "1": "ISINs", "2": "Short Fund Regular Plan IDCW Transfer"}
    ]
    
    res, code = build_scheme_json({}, rows)
    print(json.dumps(res, indent=2))
    print("Code:", code)

if __name__ == "__main__":
    test()
