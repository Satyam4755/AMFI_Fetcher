import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.scheme_parser import build_scheme_json

class TestObjectiveAndBenchmarkExtraction(unittest.TestCase):

    def test_qsif_strategy_label_and_tier1_no_space(self):
        """Tests AMFI XLS format with 'Description, Objective of the strategy' and 'Benchmark (Tier1)'."""
        rows = [
            {
                "Fields": 8.0,
                "SUMMARY DOCUMENT OF STRATEGIES": "Description, Objective of the strategy",
                "Unnamed: 2": "To achieve long-term capital appreciation by concentrating investments in equity of up to four high-potential sectors."
            },
            {
                "Fields": 16.0,
                "SUMMARY DOCUMENT OF STRATEGIES": "Benchmark (Tier1)",
                "Unnamed: 2": "NIFTY 500 Total Return Index (TRI)"
            },
            {
                "Fields": 17.0,
                "SUMMARY DOCUMENT OF STRATEGIES": "Benchmark (Tier2)",
                "Unnamed: 2": "--"
            },
            {
                "Fields": 42.0,
                "SUMMARY DOCUMENT OF STRATEGIES": "SEBI Codes",
                "Unnamed: 2": "QSIF/O/E/SRLS/25/10/0005/QNTM"
            }
        ]
        api_data = {"Scheme_Name": "qsif Sector Rotation Long-Short Fund"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(
            result["scheme_objective"],
            "To achieve long-term capital appreciation by concentrating investments in equity of up to four high-potential sectors."
        )
        self.assertEqual(result["benchmark_tier_1"], "NIFTY 500 Total Return Index (TRI)")
        self.assertIsNone(result["benchmark_tier_2"])

    def test_isif_investment_strategy_label_and_duplicate_row(self):
        """Tests AMFI XLS format with 'Description, Objective of the Investment Strategy' and duplicate allocation key."""
        rows = [
            {
                "Fields": 8,
                "Investment Strategy Summary Document": "Description, Objective of the Investment Strategy",
                "Unnamed: 2": "The Investment Strategy intends to dynamically invest in equity and equity related securities."
            },
            {
                "Fields": 9,
                "Investment Strategy Summary Document": "Description, Objective of the Investment Strategy",
                "Unnamed: 2": "Equity and Equity related securities 35%-80%\nDebt instruments 10%-55%"
            },
            {
                "Fields": 16,
                "Investment Strategy Summary Document": "Benchmark (Tier 1)",
                "Unnamed: 2": "50% Nifty 500 TRI + 40% Nifty Composite Debt Index + 7% Gold + 3% Silver"
            },
            {
                "Fields": 30,
                "Investment Strategy Summary Document": "SEBI Codes",
                "Unnamed: 2": "ISIF/I/H/AALS/25/11/0003/ICIC"
            }
        ]
        api_data = {"Scheme_Name": "iSIF Active Asset Allocator Long-Short Fund"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(
            result["scheme_objective"],
            "The Investment Strategy intends to dynamically invest in equity and equity related securities."
        )
        self.assertEqual(
            result["benchmark_tier_1"],
            "50% Nifty 500 TRI + 40% Nifty Composite Debt Index + 7% Gold + 3% Silver"
        )
        self.assertIsNotNone(result["asset_allocation"])

    def test_api_data_fallback_when_xls_missing(self):
        """Tests fallback to api_data when XLS rows are empty or missing objective/benchmark."""
        rows = []
        api_data = {
            "Scheme_Name": "Altiva Equity Long-Short Fund",
            "Scheme_Objective": "To generate long-term capital appreciation by predominantly investing in listed equity.",
            "Benchmark_Tier_1": "Nifty 500 TRI",
            "Benchmark_Tier_2": None
        }
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(
            result["scheme_objective"],
            "To generate long-term capital appreciation by predominantly investing in listed equity."
        )
        self.assertEqual(result["benchmark_tier_1"], "Nifty 500 TRI")
        self.assertIsNone(result["benchmark_tier_2"])

    def test_benchmark_name_single_tier(self):
        """Tests format where single benchmark is labeled 'Benchmark Name'."""
        rows = [
            {
                "Unnamed: 1": "Objective of the Investment Strategy",
                "Unnamed: 2": "To generate capital appreciation."
            },
            {
                "Unnamed: 1": "Benchmark Name",
                "Unnamed: 2": "NIFTY 500 TRI"
            }
        ]
        api_data = {"Scheme_Name": "Apex Equity LSF"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(result["scheme_objective"], "To generate capital appreciation.")
        self.assertEqual(result["benchmark_tier_1"], "NIFTY 500 TRI")
        self.assertIsNone(result["benchmark_tier_2"])

    def test_direct_and_regular_plans_extraction(self):
        """Tests that both Direct and Regular plans are properly captured into plans dict."""
        rows = [
            {
                "Fields": 1,
                "SCHEME SUMMARY DOCUMENT": "Fund Name",
                "Unnamed: 2": "Test Scheme"
            },
            {
                "Fields": 2,
                "SCHEME SUMMARY DOCUMENT": "Option Names (Regular & Direct)",
                "Unnamed: 2": "Regular - Growth\nRegular - IDCW Payout\nDirect - Growth\nDirect - IDCW Reinvestment"
            },
            {
                "Fields": 28,
                "SCHEME SUMMARY DOCUMENT": "ISIN",
                "Unnamed: 2": "Regular - Growth - INF123456789\nDirect - Growth - INF987654321"
            },
            {
                "Fields": 29,
                "SCHEME SUMMARY DOCUMENT": "AMFI Code",
                "Unnamed: 2": "Regular - Growth - SIF-01\nDirect - Growth - SIF-02"
            }
        ]
        api_data = {"Scheme_Name": "Test Scheme"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertIn("regular", result["plans"])
        self.assertIn("direct", result["plans"])
        self.assertTrue(len(result["plans"]["regular"]["growth"]) > 0)
        self.assertTrue(len(result["plans"]["direct"]["growth"]) > 0)
        self.assertEqual(result["plans"]["regular"]["growth"][0]["isin_code"], "INF123456789")
        self.assertEqual(result["plans"]["direct"]["growth"][0]["isin_code"], "INF987654321")

    def test_apex_investment_strategy_code_and_limits(self):
        """Tests Apex scheme SEBI code ('Investment strategy code') and investment/switch limits."""
        rows = [
            {
                "Unnamed: 1": "Name of the Investment Strategy",
                "Unnamed: 2": "Apex Hybrid Long-Short Fund"
            },
            {
                "Unnamed: 1": "Investment strategy code",
                "Unnamed: 2": "APEX/I/H/HLSF/26/02/0001/ABSL"
            },
            {
                "Unnamed: 1": "Min. Application Amount",
                "Unnamed: 2": "10,00,000"
            },
            {
                "Unnamed: 1": "Min. Additional Amount",
                "Unnamed: 2": "1,00,000"
            },
            {
                "Unnamed: 1": "Min. Switch Amount (If applicable)",
                "Unnamed: 2": "5,00,000"
            },
            {
                "Unnamed: 1": "Swing Pricing (If Applicable)",
                "Unnamed: 2": "Applicable"
            },
            {
                "Unnamed: 1": "Side-pocketing (If Applicable)",
                "Unnamed: 2": "Applicable"
            }
        ]
        api_data = {
            "Scheme_Name": "Apex Hybrid Long-Short Fund",
            "SIF_Name": "Apex SIF",
            "AMC_Website": "https://mutualfund.adityabirlacapital.com"
        }
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(result["sebi_code"], "APEX/I/H/HLSF/26/02/0001/ABSL")
        self.assertEqual(result["investment_limits"]["minimum_application_amount"], "10,00,000")
        self.assertEqual(result["investment_limits"]["minimum_additional_amount"], "1,00,000")
        self.assertEqual(result["switch_details"]["minimum_switch_amount"], "5,00,000")
        self.assertEqual(result["special_facilities"]["swing_pricing"], "Applicable")
        self.assertEqual(result["special_facilities"]["side_pocketing"], "Applicable")
        self.assertEqual(result["amc_details"]["sif_name"], "Apex SIF")
        self.assertEqual(result["amc_details"]["amc_website"], "https://mutualfund.adityabirlacapital.com")

if __name__ == "__main__":
    unittest.main()
