import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.scheme_parser import build_scheme_json

def test_altiva():
    print("\nTesting Altiva...")
    rows = [
        {"AttributeName": "Option Names (Regular & Direct)", "AttributeValue": "Direct Plan Growth\nDirect Plan IDCW - Payout\nDirect Plan IDCW - Reinvestment\nDirect Plan IDCW - Transfer\nRegular Plan Growth\nRegular Plan IDCW - Payout\nRegular Plan IDCW - Reinvestment\nRegular Plan IDCW - Transfer"},
        {"AttributeName": "ISINs", "AttributeValue": "Altiva Equity ExTop 100 LongShort Fund - Direct Plan - Growth - INF754K30094\nAltiva Equity ExTop 100 LongShort Fund - Direct Plan - IDCW - Payout - INF754K30102\nAltiva Equity ExTop 100 LongShort Fund - Direct Plan - IDCW - Reinvestment - INF754K30110\nAltiva Equity ExTop 100 LongShort Fund - Direct Plan - IDCW - Transfer - INF754K30128\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - Growth - INF754K30136\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - IDCW - Payout - INF754K30144\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - IDCW - Reinvestment - INF754K30151\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - IDCW - Transfer - INF754K30169"},
        {"AttributeName": "AMFI Codes", "AttributeValue": "Altiva Equity ExTop 100 LongShort Fund - Direct Plan - Growth - SIF-120\nAltiva Equity ExTop 100 LongShort Fund - Direct Plan - IDCW - Payout - SIF-121\nAltiva Equity ExTop 100 LongShort Fund - Direct Plan - IDCW - Reinvestment - SIF-121\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - Growth - SIF-122\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - IDCW - Payout - SIF-123\nAltiva Equity ExTop 100 LongShort Fund - Regular Plan - IDCW - Reinvestment - SIF-123\n"}
    ]
    
    api_data = {"Scheme_Name": "Altiva Equity ExTop 100 LongShort Fund"}
    result, _ = build_scheme_json(api_data, rows)
    plans = result.get("plans", {})
    
    expected = {
        ("direct", "growth", None, None): ("SIF-120", "INF754K30094"),
        ("direct", "idcw", "payout", None): ("SIF-121", "INF754K30102"),
        ("direct", "idcw", "reinvestment", None): ("SIF-121", "INF754K30110"),
        ("direct", "idcw", "transfer", None): (None, "INF754K30128"),
        ("regular", "growth", None, None): ("SIF-122", "INF754K30136"),
        ("regular", "idcw", "payout", None): ("SIF-123", "INF754K30144"),
        ("regular", "idcw", "reinvestment", None): ("SIF-123", "INF754K30151"),
        ("regular", "idcw", "transfer", None): (None, "INF754K30169")
    }
    
    passed = True
    for (ptype, otype, stype, tperiod), (e_amfi, e_isin) in expected.items():
        found = False
        
        if otype == "growth":
            nodes = plans.get(ptype, {}).get("growth", [])
            for node in nodes:
                if (node.get("amfi_code") == e_amfi and node.get("isin_code") == e_isin):
                    found = True
                    break
        else:
            nodes = plans.get(ptype, {}).get("idcw", {}).get(stype, [])
            for node in nodes:
                if (node.get("amfi_code") == e_amfi and node.get("isin_code") == e_isin) and node.get("time_period") == tperiod:
                    found = True
                    break
                    
        if not found:
            print(f"❌ FAIL: Missing or incorrect mapping for {ptype} {otype} {stype} {tperiod}. Expected ({e_amfi}, {e_isin})")
            passed = False
        else:
            print(f"✅ PASS: {ptype} {otype} {stype} {tperiod} -> ({e_amfi}, {e_isin})")
            
    unresolved_d = plans.get("direct", {}).get("unresolved", [])
    unresolved_r = plans.get("regular", {}).get("unresolved", [])
    if unresolved_d or unresolved_r:
        print(f"⚠️ Unresolved identifiers present: Direct: {unresolved_d}, Regular: {unresolved_r}")
        
    return passed

def test_arudha():
    print("\nTesting Arudha...")
    rows = [
        {"AttributeName": "Option Names (Regular & Direct)", "AttributeValue": "Direct Plan Growth\nDirect Plan IDCW - Daily Reinvestment\nDirect Plan IDCW - Weekly Reinvestment\nRegular Plan Growth\nRegular Plan IDCW - Monthly Payout & Reinvestment"},
        {"AttributeName": "ISINs", "AttributeValue": "Arudha Liquid Fund - Direct Plan - Growth - INF123A01011\nArudha Liquid Fund - Direct Plan - IDCW - Daily Reinvestment - INF123A01022\nArudha Liquid Fund - Direct Plan - IDCW - Weekly Reinvestment - INF123A01033\nArudha Liquid Fund - Regular Plan - Growth - INF123A01044\nArudha Liquid Fund - Regular Plan - IDCW - Monthly Payout - INF123A01055\nArudha Liquid Fund - Regular Plan - IDCW - Monthly Reinvestment - INF123A01066"},
        {"AttributeName": "AMFI Codes", "AttributeValue": "Arudha Liquid Fund - Direct Plan - Growth - SIF-200\nArudha Liquid Fund - Direct Plan - IDCW - Daily Reinvestment - SIF-201\nArudha Liquid Fund - Direct Plan - IDCW - Weekly Reinvestment - SIF-202\nArudha Liquid Fund - Regular Plan - Growth - SIF-203\nArudha Liquid Fund - Regular Plan - IDCW - Monthly Payout & Reinvestment - SIF-204"}
    ]
    
    api_data = {"Scheme_Name": "Arudha Liquid Fund"}
    result, _ = build_scheme_json(api_data, rows)
    plans = result.get("plans", {})
    
    expected = {
        ("direct", "growth", None, None): ("SIF-200", "INF123A01011"),
        ("direct", "idcw", "reinvestment", "daily"): ("SIF-201", "INF123A01022"),
        ("direct", "idcw", "reinvestment", "weekly"): ("SIF-202", "INF123A01033"),
        ("regular", "growth", None, None): ("SIF-203", "INF123A01044"),
        ("regular", "idcw", "payout", "monthly"): ("SIF-204", "INF123A01055"),
        ("regular", "idcw", "reinvestment", "monthly"): ("SIF-204", "INF123A01066"),
    }
    
    passed = True
    for (ptype, otype, stype, tperiod), (e_amfi, e_isin) in expected.items():
        found = False
        
        if otype == "growth":
            nodes = plans.get(ptype, {}).get("growth", [])
            for node in nodes:
                if (node.get("amfi_code") == e_amfi and node.get("isin_code") == e_isin):
                    found = True
                    break
        else:
            nodes = plans.get(ptype, {}).get("idcw", {}).get(stype, [])
            for node in nodes:
                if (node.get("amfi_code") == e_amfi and node.get("isin_code") == e_isin) and node.get("time_period") == tperiod:
                    found = True
                    break
                    
        if not found:
            print(f"❌ FAIL: Missing or incorrect mapping for {ptype} {otype} {stype} {tperiod}. Expected ({e_amfi}, {e_isin})")
            passed = False
        else:
            print(f"✅ PASS: {ptype} {otype} {stype} {tperiod} -> ({e_amfi}, {e_isin})")
            
    return passed

if __name__ == "__main__":
    altiva_passed = test_altiva()
    arudha_passed = test_arudha()
    
    if altiva_passed and arudha_passed:
        print("\n✅ ALL REGRESSION TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME REGRESSION TESTS FAILED")
        sys.exit(1)
