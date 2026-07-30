import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.scheme_parser import build_scheme_json

def test_altiva_regression():
    rows = [
        {
            "SCHEME SUMMARY DOCUMENT": "AMFI Codes",
            "Unnamed: 2": "SIF-120 - Altiva Direct Plan Growth\nSIF-121 - Altiva Direct Plan IDCW Payout\nSIF-121 - Altiva Direct Plan IDCW Reinvestment\nNA - Altiva Direct Plan IDCW Transfer\nSIF-122 - Altiva Regular Plan Growth\nSIF-123 - Altiva Regular Plan IDCW Payout\nSIF-123 - Altiva Regular Plan IDCW Reinvestment\nNA - Altiva Regular Plan IDCW Transfer"
        },
        {
            "SCHEME SUMMARY DOCUMENT": "ISINs",
            "Unnamed: 2": "INF754K30094 - Altiva Direct Plan Growth\nINF754K30102 - Altiva Direct Plan IDCW Payout\nINF754K30110 - Altiva Direct Plan IDCW Reinvestment\nINF754K30128 - Altiva Direct Plan IDCW Transfer\nINF754K30136 - Altiva Regular Plan Growth\nINF754K30144 - Altiva Regular Plan IDCW Payout\nINF754K30151 - Altiva Regular Plan IDCW Reinvestment\nINF754K30169 - Altiva Regular Plan IDCW Transfer"
        }
    ]
    
    scheme_data = {"Scheme_Name": "Altiva"}
    result, _ = build_scheme_json(scheme_data, rows)
    plans = result["plans"]
    
    assert len(plans["direct"]["growth"]) == 1
    assert plans["direct"]["growth"][0]["amfi_code"] == "SIF-120"
    assert plans["direct"]["growth"][0]["isin_code"] == "INF754K30094"
    assert len(plans["direct"]["idcw"]["payout"]) == 1
    assert plans["direct"]["idcw"]["payout"][0]["amfi_code"] == "SIF-121"

def test_arudha_regression():
    # Simulate concatenated paragraph layout!
    rows = [
        {
            "SCHEME SUMMARY DOCUMENT": "AMFI Codes",
            "Unnamed: 2": "Arudha Equity Long Short Fund Regular Plan - Growth Option-SIF-114 Arudha Equity Long Short Fund Regular Plan- - Payout of Income Distribution cum Capital Withdrawal Option-SIF-115 Arudha Equity Long Short Fund Direct Plan - Growth Option-SIF-112"
        },
        {
            "SCHEME SUMMARY DOCUMENT": "ISINs",
            "Unnamed: 2": "Arudha Equity Long Short Fund Regular Plan - Growth Option-INF582M30012 Arudha Equity Long Short Fund Regular Plan - Payout of Income Distribution cum Capital Withdrawal Option-INF582M30020 Arudha Equity Long Short Fund Direct Plan - Growth Option-INF582M30046"
        }
    ]
    
    # Fund name is critical for splitting concatenated strings
    scheme_data = {"Scheme_Name": "Arudha Equity Long Short Fund"}
    result, _ = build_scheme_json(scheme_data, rows)
    plans = result["plans"]
    
    # Assert Direct Plan
    assert len(plans["direct"]["growth"]) == 1
    assert plans["direct"]["growth"][0]["amfi_code"] == "SIF-112"
    assert plans["direct"]["growth"][0]["isin_code"] == "INF582M30046"
    
    # Assert Regular Plan
    assert len(plans["regular"]["growth"]) == 1
    assert plans["regular"]["growth"][0]["amfi_code"] == "SIF-114"
    assert plans["regular"]["growth"][0]["isin_code"] == "INF582M30012"
    
    assert len(plans["regular"]["idcw"]["payout"]) == 1
    assert plans["regular"]["idcw"]["payout"][0]["amfi_code"] == "SIF-115"
    assert plans["regular"]["idcw"]["payout"][0]["isin_code"] == "INF582M30020"

if __name__ == "__main__":
    test_altiva_regression()
    test_arudha_regression()
    print("All regression tests passed successfully!")
