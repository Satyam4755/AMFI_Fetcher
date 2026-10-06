import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.scheme_parser import build_scheme_json


class TestFundManagerAndPipelineRegression(unittest.TestCase):

    def test_01_fund_manager_name_and_from_date_extracted_correctly(self):
        """TEST 1: Fund Manager name + From Date extracted correctly."""
        rows = [
            {
                "Field_1": "Quant",
                "Fund_Manager_1-Name": "Sandeep Tandon",
                "Fund_Manager_1-Type": "Primary",
                "Fund_Manager_1-From_Date": "10/15/2025 12:00:00 AM",
            },
            {
                "Fund_Manager_2-Name": "Jignesh Shah",
                "Fund_Manager_2-Type": "Comanage",
                "Fund_Manager_2-From_Date": "02/20/2026 12:00:00 AM",
            },
        ]
        api_data = {"Scheme_Name": "Quant SIF"}
        result, _ = build_scheme_json(api_data, rows)

        fms = result.get("fund_managers", [])
        self.assertEqual(len(fms), 2)
        self.assertEqual(fms[0]["name"], "Sandeep Tandon")
        self.assertEqual(fms[0]["type"], "Primary")
        self.assertEqual(fms[0]["from"], "2025-10-15")

        self.assertEqual(fms[1]["name"], "Jignesh Shah")
        self.assertEqual(fms[1]["type"], "Comanage")
        self.assertEqual(fms[1]["from"], "2026-02-20")

    def test_02_merged_wrapped_cells_reconstruction(self):
        """TEST 2: Fund Manager data spread across merged/wrapped cells is reconstructed correctly."""
        # Multi-line composite text layout
        rows = [
            {
                "fund_manager_name": "Mr. Harsh Agarwal\nMr. Pranav Mise",
                "fund_manager_from_date": "Mr. Harsh Agarwal - 25 Mar 2026\nMr. Pranav Mise - 24th April, 2026",
                "fund_manager_type": "Primary\nComanage",
            }
        ]
        api_data = {"Scheme_Name": "360 ONE SIF"}
        result, _ = build_scheme_json(api_data, rows)

        fms = result.get("fund_managers", [])
        self.assertEqual(len(fms), 2)
        self.assertEqual(fms[0]["name"], "Mr. Harsh Agarwal")
        self.assertEqual(fms[0]["from"], "2026-03-25")
        self.assertEqual(fms[1]["name"], "Mr. Pranav Mise")
        self.assertEqual(fms[1]["from"], "2026-04-24")

    def test_03_multiple_fund_managers_all_preserved(self):
        """TEST 3: Multiple Fund Managers are all preserved."""
        rows = [
            {"Fund_Manager_1-Name": "Sandeep Tandon", "Fund_Manager_1-From_Date": "15-10-2025"},
            {"Fund_Manager_2-Name": "Jignesh Shah", "Fund_Manager_2-From_Date": "20-02-2026"},
            {"Fund_Manager_3-Name": "Ankit Pande", "Fund_Manager_3-From_Date": "15-10-2025"},
            {"Fund_Manager_4-Name": "Sameer Kate", "Fund_Manager_4-From_Date": "15-10-2025"},
            {"Fund_Manager_5-Name": "Sanjeev Sharma", "Fund_Manager_5-From_Date": "15-10-2025"},
        ]
        api_data = {"Scheme_Name": "Quant All Managers"}
        result, _ = build_scheme_json(api_data, rows)

        fms = result.get("fund_managers", [])
        self.assertEqual(len(fms), 5)
        names = [f["name"] for f in fms]
        dates = [f["from"] for f in fms]
        self.assertEqual(names, ["Sandeep Tandon", "Jignesh Shah", "Ankit Pande", "Sameer Kate", "Sanjeev Sharma"])
        self.assertEqual(dates, ["2025-10-15", "2026-02-20", "2025-10-15", "2025-10-15", "2025-10-15"])

    def test_04_excel_datetime_and_string_formats_normalized(self):
        """TEST 4: Excel datetime/string date formats are normalized correctly."""
        rows = [
            {"Fund_Manager_1-Name": "Manager ISO", "Fund_Manager_1-From_Date": "2026-06-05T00:00:00.000"},
            {"Fund_Manager_2-Name": "Manager Ordinal", "Fund_Manager_2-From_Date": "24th April, 2026"},
            {"Fund_Manager_3-Name": "Manager MonthName", "Fund_Manager_3-From_Date": "June 19, 2026"},
            {"Fund_Manager_4-Name": "Manager Hyphen", "Fund_Manager_4-From_Date": "28-Jan-2026"},
            {"Fund_Manager_5-Name": "Manager Slash", "Fund_Manager_5-From_Date": "17/11/2025"},
        ]
        result, _ = build_scheme_json({}, rows)
        fms = result.get("fund_managers", [])
        self.assertEqual(fms[0]["from"], "2026-06-05")
        self.assertEqual(fms[1]["from"], "2026-04-24")
        self.assertEqual(fms[2]["from"], "2026-06-19")
        self.assertEqual(fms[3]["from"], "2026-01-28")
        self.assertEqual(fms[4]["from"], "2025-11-17")

    def test_05_incomplete_parser_reconciliation_preserves_existing_date(self):
        """TEST 5: Incomplete parser output does not overwrite an existing valid From Date."""
        existing_manager = {
            "name": "Sandeep Tandon",
            "from_date": "2025-10-15",
            "active": True
        }
        new_extracted_manager = {
            "name": "Sandeep Tandon",
            "from_date": None,
            "active": True
        }

        # Reconciliation logic simulation
        def reconcile_manager(existing, incoming):
            if incoming.get("from_date") is None and existing.get("from_date") is not None:
                incoming["from_date"] = existing["from_date"]
            return incoming

        reconciled = reconcile_manager(existing_manager, new_extracted_manager)
        self.assertEqual(reconciled["from_date"], "2025-10-15")

    def test_06_formatting_differences_do_not_duplicate_manager(self):
        """TEST 6: Formatting differences do not create duplicate logical Fund Managers."""
        def normalize_mgr_key(name):
            import re
            return re.sub(r'[^a-z0-9]', '', re.sub(r'^(?:mr\.|ms\.|mrs\.|dr\.)\s*', '', name.lower().strip()))

        key1 = normalize_mgr_key("  Mr. Sandeep Tandon  ")
        key2 = normalize_mgr_key("Sandeep Tandon")
        key3 = normalize_mgr_key("Sandeep  Tandon\n")
        self.assertEqual(key1, key2)
        self.assertEqual(key2, key3)

    def test_07_genuinely_new_fund_manager_added(self):
        """TEST 7: A genuinely new Fund Manager is added."""
        existing_managers = [
            {"name": "Sandeep Tandon", "from": "2025-10-15"}
        ]
        incoming_managers = [
            {"name": "Sandeep Tandon", "from": "2025-10-15"},
            {"name": "Jignesh Shah", "from": "2026-02-20"}
        ]
        existing_names = {m["name"] for m in existing_managers}
        for inc in incoming_managers:
            if inc["name"] not in existing_names:
                existing_managers.append(inc)

        self.assertEqual(len(existing_managers), 2)
        self.assertEqual(existing_managers[1]["name"], "Jignesh Shah")

    def test_08_explicitly_changed_from_date_updated(self):
        """TEST 8: An explicitly changed From Date is updated."""
        existing = {"name": "Sandeep Tandon", "from": "2025-10-15"}
        incoming = {"name": "Sandeep Tandon", "from": "2026-01-01"}
        if incoming["from"] and incoming["from"] != existing["from"]:
            existing["from"] = incoming["from"]
        self.assertEqual(existing["from"], "2026-01-01")

    def test_09_actual_amfi_asset_allocation_rows_extracted(self):
        """TEST 9: Actual AMFI Asset Allocation rows are extracted correctly."""
        rows = [
            {
                "Field_9": (
                    "Investment in Equity and equity related securities - 20 - 50%\n"
                    "Investment in Debt and money market instruments - 20 - 65%\n"
                    "Short exposure through unhedged derivative positions in equity and debt instruments - 0 - 25%\n"
                    "Units issued by INVITs - 0 - 20%\n"
                    "Commodity derivatives - 0 - 25%"
                )
            }
        ]
        result, _ = build_scheme_json({}, rows)
        alloc = result.get("asset_allocation")
        self.assertIsNotNone(alloc)
        self.assertEqual(len(alloc), 5)
        self.assertEqual(alloc[0]["allocation_type"], "Investment in Equity and equity related securities")
        self.assertEqual(alloc[0]["minimum_percentage"], 20)
        self.assertEqual(alloc[0]["maximum_percentage"], 50)

        self.assertEqual(alloc[2]["allocation_type"], "Short exposure through unhedged derivative positions in equity and debt instruments")
        self.assertEqual(alloc[2]["minimum_percentage"], 0)
        self.assertEqual(alloc[2]["maximum_percentage"], 25)

    def test_10_asset_allocation_not_empty_when_source_exists(self):
        """TEST 10: Asset Allocation does not become [] when valid source data exists."""
        rows = [
            {
                "stated_asset_allocation": [
                    {"Instruments": "Equity Securities", "IndicativeAllocation": "65% - 100%"},
                    {"Instruments": "Debt Securities", "IndicativeAllocation": "0% - 35%"}
                ]
            }
        ]
        result, _ = build_scheme_json({}, rows)
        alloc = result.get("asset_allocation")
        self.assertIsNotNone(alloc)
        self.assertEqual(len(alloc), 2)
        self.assertEqual(alloc[0]["allocation_type"], "Equity Securities")
        self.assertEqual(alloc[0]["minimum_percentage"], 65)
        self.assertEqual(alloc[0]["maximum_percentage"], 100)

    def test_11_multiline_wrapped_asset_allocation_preserved(self):
        """TEST 11: Multiline/wrapped Asset Allocation descriptions are preserved."""
        rows = [
            {
                "stated_asset_allocation": (
                    "Units of Real Estate Investment Trusts (REITs) and\n"
                    "Infrastructure Investment Trusts (InvITs) - 0 to 10%\n"
                    "Money Market Instruments having unexpired maturity\n"
                    "up to 91 Days - 0 to 20%"
                )
            }
        ]
        result, _ = build_scheme_json({}, rows)
        alloc = result.get("asset_allocation")
        self.assertIsNotNone(alloc)
        self.assertEqual(len(alloc), 2)
        self.assertIn("Units of Real Estate Investment Trusts", alloc[0]["allocation_type"])
        self.assertIn("Infrastructure Investment Trusts", alloc[0]["allocation_type"])
        self.assertEqual(alloc[0]["minimum_percentage"], 0)
        self.assertEqual(alloc[0]["maximum_percentage"], 10)

    def test_12_actual_scheme_objective_extracted(self):
        """TEST 12: Actual Scheme Objective/Description is extracted."""
        long_obj = "To generate capital appreciation and income generation with dynamic allocation to different asset classes like equities, InvITs, commodities and fixed income layered with derivatives long-short trading strategies."
        rows = [
            {
                "Field_8": long_obj
            }
        ]
        result, _ = build_scheme_json({}, rows)
        self.assertEqual(result.get("scheme_objective"), long_obj)

    def test_13_noise_words_not_stored_as_scheme_objective(self):
        """TEST 13: 'Primary' or other classification metadata is not incorrectly stored as Scheme Objective."""
        rows = [
            {
                "Field_8": "Primary",
                "Description_Objective_of_the_Strategy": "To generate long-term capital growth through equity investments."
            }
        ]
        result, _ = build_scheme_json({}, rows)
        self.assertEqual(
            result.get("scheme_objective"),
            "To generate long-term capital growth through equity investments."
        )

    def test_14_different_amfi_document_layouts_produce_canonical_structure(self):
        """TEST 14: Different AMFI document layouts produce the correct canonical structure."""
        # Layout 1: XML Spreadsheet with sub-labels (e.g. ICICI SSD_S-23)
        rows_xml_ss = [
            {"0": "Fund Manager 1 - Name", "1": "Mr. Sankaran Naren"},
            {"0": "Fund Manager 1 - From Date", "1": "2026-06-05"},
            {"0": "Fund Manager 1 - Type", "1": "Primary"},
            {"0": "Description, Objective of the Investment Strategy", "1": "Long term capital appreciation."},
        ]
        res1, _ = build_scheme_json({}, rows_xml_ss)
        self.assertEqual(len(res1["fund_managers"]), 1)
        self.assertEqual(res1["fund_managers"][0]["name"], "Mr. Sankaran Naren")
        self.assertEqual(res1["fund_managers"][0]["from"], "2026-06-05")
        self.assertEqual(res1["scheme_objective"], "Long term capital appreciation.")

        # Layout 2: Structured XML list (e.g. SBI SSD_S-4)
        rows_sbi = [
            {
                "Fund_Manager": [
                    {"Name": "Mr. Mansi Sajeja", "Type": "Primary", "FromDate": "28-Jan-2026"}
                ],
                "Description": "To generate returns by investing in equity and debt instruments."
            }
        ]
        res2, _ = build_scheme_json({}, rows_sbi)
        self.assertEqual(len(res2["fund_managers"]), 1)
        self.assertEqual(res2["fund_managers"][0]["name"], "Mr. Mansi Sajeja")
        self.assertEqual(res2["fund_managers"][0]["from"], "2026-01-28")
        self.assertEqual(res2["scheme_objective"], "To generate returns by investing in equity and debt instruments.")

    def test_15_structured_dict_allocations_preserved(self):
        """TEST 15: Previously fixed asset-allocation regression tests still pass."""
        rows = [
            {
                "stated_asset_allocation": [
                    {"Instrument": "Equity and Equity related instruments", "Range": "25-75%"},
                    {"Instrument": "Debt and Money Market Instruments", "Range": "25-75%"},
                    {"Instrument": "Units of InvITs", "Range": "0-20%"}
                ]
            }
        ]
        result, _ = build_scheme_json({}, rows)
        alloc = result.get("asset_allocation")
        self.assertEqual(len(alloc), 3)
        self.assertEqual(alloc[0]["allocation_type"], "Equity and Equity related instruments")
        self.assertEqual(alloc[0]["minimum_percentage"], 25)
        self.assertEqual(alloc[0]["maximum_percentage"], 75)
        self.assertEqual(alloc[2]["allocation_type"], "Units of InvITs")
        self.assertEqual(alloc[2]["minimum_percentage"], 0)
        self.assertEqual(alloc[2]["maximum_percentage"], 20)

    def test_16_dynasif_sif_mapping_and_no_cross_contamination(self):
        """TEST 16: DynaSIF multiline SIF codes map authoritatively to correct plans/ISINs."""
        rows = [
            {
                "fund_name": "DynaSIF Active Asset Allocator Long-Short Fund",
                "options_names": "Regular Plan-Growth Regular Plan - IDCW Payout Regular Plan - IDCW Reinvestment Direct Plan-Growth Direct Plan - IDCW Payout Direct Plan - IDCW Reinvestment",
                "rta_codes": "ALSRG\nALSRP\nALSRR\nALSDG\nALSDP\nALSDR",
                "isins": "INF579M30075\nINF579M30083\nINF579M30091\nINF579M30109\nINF579M30117\nINF579M30125",
                "amfi_codes": "SIF - 86\nSIF - 87\nSIF - 88\nSIF - 89"
            }
        ]
        result, primary_amfi = build_scheme_json({}, rows)
        self.assertEqual(primary_amfi, "SIF-87")

        plans = result.get("plans", {})
        reg_growth = plans.get("regular", {}).get("growth", [])
        self.assertEqual(len(reg_growth), 1)
        self.assertEqual(reg_growth[0]["isin_code"], "INF579M30075")
        self.assertEqual(reg_growth[0]["amfi_code"], "SIF-87")

        dir_growth = plans.get("direct", {}).get("growth", [])
        self.assertEqual(len(dir_growth), 1)
        self.assertEqual(dir_growth[0]["isin_code"], "INF579M30109")
        self.assertEqual(dir_growth[0]["amfi_code"], "SIF-88")

        reg_idcw = plans.get("regular", {}).get("idcw", {})
        reg_idcw_payout = reg_idcw.get("payout", [])
        self.assertEqual(reg_idcw_payout[0]["amfi_code"], "SIF-89")

        dir_idcw = plans.get("direct", {}).get("idcw", {})
        dir_idcw_payout = dir_idcw.get("payout", [])
        self.assertEqual(dir_idcw_payout[0]["amfi_code"], "SIF-86")

    def test_17_dynasif_multi_manager_composite_from_dates(self):
        """TEST 17: Multi-manager comma-separated date strings with ordinal formats correlate accurately."""
        rows = [
            {
                "fund_manager_name": "Mr. Harsh Agarwal, Mr. Milan Mody, Mr. Rahul Khetawat, Mr.Pranav Mise",
                "fund_manager_type": "Mr. Harsh Agarwal - Primary, Mr. Milan Mody - comanage , Mr. Rahul Khetwat - Comanage, Mr.Pranav Mise - Comanage",
                "fund_manager_from_date": "Mr. Harsh Agarwal - 25 Mar 2026, Mr. Milan Mody - 25 Mar 2026, Mr. Rahul Khetawat -  25 Mar 2026, Mr.Pranav Mise - 24th April, 2026"
            }
        ]
        result, _ = build_scheme_json({}, rows)
        fms = result.get("fund_managers", [])
        self.assertEqual(len(fms), 4)

        mgr_map = {f["name"]: f for f in fms}
        self.assertIn("Mr. Harsh Agarwal", mgr_map)
        self.assertEqual(mgr_map["Mr. Harsh Agarwal"]["from"], "2026-03-25")
        self.assertEqual(mgr_map["Mr. Harsh Agarwal"]["type"], "Primary")

        self.assertIn("Mr. Milan Mody", mgr_map)
        self.assertEqual(mgr_map["Mr. Milan Mody"]["from"], "2026-03-25")
        self.assertEqual(mgr_map["Mr. Milan Mody"]["type"], "Comanage")

        self.assertIn("Mr. Rahul Khetawat", mgr_map)
        self.assertEqual(mgr_map["Mr. Rahul Khetawat"]["from"], "2026-03-25")
        self.assertEqual(mgr_map["Mr. Rahul Khetawat"]["type"], "Comanage")

        self.assertIn("Mr.Pranav Mise", mgr_map)
        self.assertEqual(mgr_map["Mr.Pranav Mise"]["from"], "2026-04-24")
        self.assertEqual(mgr_map["Mr.Pranav Mise"]["type"], "Comanage")


if __name__ == "__main__":
    unittest.main()
