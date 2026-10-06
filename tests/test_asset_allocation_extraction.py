import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.scheme_parser import build_scheme_json


class TestAssetAllocationExtraction(unittest.TestCase):

    def test_ssd_s2_example(self):
        """Tests the exact SSD_S-2.pdf / XML example from the problem description."""
        rows = [
            {
                "Fields": 1,
                "SCHEME SUMMARY DOCUMENT": "Fund Name",
                "Unnamed: 2": "qsif Hybrid Long-Short Fund"
            },
            {
                "Fields": 8,
                "SCHEME SUMMARY DOCUMENT": "Description, Objective of the scheme",
                "Unnamed: 2": "This investment strategy aims to achieve a blend of capital appreciation and income generation."
            },
            {
                "Fields": 9,
                "SCHEME SUMMARY DOCUMENT": "Stated Asset Allocation",
                "Unnamed: 2": "Investment in equity and equity-related instruments:- 25-75%\nInvestment in debt and money market instruments:- 25-75%\nInvestment in InVITs:- 0-20%"
            },
            {
                "Fields": 30,
                "SCHEME SUMMARY DOCUMENT": "SEBI Codes",
                "Unnamed: 2": "QSIF/I/H/HLSF/25/09/0002/QNTM"
            }
        ]
        api_data = {"Scheme_Name": "qsif Hybrid Long-Short Fund"}
        result, _ = build_scheme_json(api_data, rows)

        expected_allocations = [
            {
                "allocation_type": "Investment in equity and equity-related instruments",
                "minimum_percentage": 25,
                "maximum_percentage": 75
            },
            {
                "allocation_type": "Investment in debt and money market instruments",
                "minimum_percentage": 25,
                "maximum_percentage": 75
            },
            {
                "allocation_type": "Investment in InVITs",
                "minimum_percentage": 0,
                "maximum_percentage": 20
            }
        ]

        self.assertEqual(result["asset_allocation"], expected_allocations)

    def test_wrapped_multiline_allocation(self):
        """Tests multiline wrapped allocation names (SSD_S-20 pattern)."""
        rows = [
            {
                "Unnamed: 1": "Name of the Investment Strategy",
                "Unnamed: 2": "Test Fund"
            },
            {
                "Unnamed: 1": "Stated Asset Allocation",
                "Unnamed: 2": (
                    "Equity and equity-related instruments (including unhedged short exposure)   - 80% - 100% of net assets,"
                    "Debt and Money Market Instruments including units of debt \n"
                    "oriented mutual fund schemes  - 0%-20% of net assets, Units issued by InvITs - 0% - 20% of net assets. "
                    "Please refer the INVESTMENT STRATEGY Information Document for more details."
                )
            }
        ]
        api_data = {"Scheme_Name": "Test Fund"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(len(result["asset_allocation"]), 3)
        self.assertEqual(
            result["asset_allocation"][0]["allocation_type"],
            "Equity and equity-related instruments (including unhedged short exposure)"
        )
        self.assertEqual(result["asset_allocation"][0]["minimum_percentage"], 80)
        self.assertEqual(result["asset_allocation"][0]["maximum_percentage"], 100)

        self.assertEqual(
            result["asset_allocation"][1]["allocation_type"],
            "Debt and Money Market Instruments including units of debt oriented mutual fund schemes"
        )
        self.assertEqual(result["asset_allocation"][1]["minimum_percentage"], 0)
        self.assertEqual(result["asset_allocation"][1]["maximum_percentage"], 20)

        self.assertEqual(
            result["asset_allocation"][2]["allocation_type"],
            "Units issued by InvITs"
        )
        self.assertEqual(result["asset_allocation"][2]["minimum_percentage"], 0)
        self.assertEqual(result["asset_allocation"][2]["maximum_percentage"], 20)

    def test_comma_separated_inline_allocations(self):
        """Tests comma-separated single-line allocations (SSD_S-7 and SSD_S-17 pattern)."""
        rows = [
            {
                "SUMMARY DOCUMENT": "Stated Asset Allocation",
                "Unnamed: 2": "Equity and Equity related instruments including REITs and Equity Derivatives 65 -100, Debt and money market instruments including fixed income derivatives 25 -35,  InvITs 0 -10."
            }
        ]
        api_data = {"Scheme_Name": "Titanium Hybrid"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(result["asset_allocation"], [
            {
                "allocation_type": "Equity and Equity related instruments including REITs and Equity Derivatives",
                "minimum_percentage": 65,
                "maximum_percentage": 100
            },
            {
                "allocation_type": "Debt and money market instruments including fixed income derivatives",
                "minimum_percentage": 25,
                "maximum_percentage": 35
            },
            {
                "allocation_type": "InvITs",
                "minimum_percentage": 0,
                "maximum_percentage": 10
            }
        ])

    def test_html_table_flattened_allocations(self):
        """Tests HTML table flattened text with Risk Profile columns (SSD_S-4 / SSD_S-33 pattern)."""
        html_flattened = (
            "Instruments IndicativeAllocation RiskProfile "
            "Equity & Equity related instruments 65% - 75% Risk Band Level 1 "
            "Hedged (including index futures, stock futures, index options, & stock options, etc. as part of hedged / arbitrage exposure, derivative strategies like Covered calls, protective Puts etc.) 0% - 75% Risk Band Level 1 "
            "Unhedged (Short derivatives) 0% - 25% Risk Band Level 1 "
            "Debt and Money Market Instruments, including Units of Debt oriented mutual fund schemes 25% -35% Risk Band Level 1 "
            "Units issued by REITs and InvITs 0% -10% Risk Band Level 1"
        )
        rows = [
            {
                "AttributeName": "Stated Asset Allocation",
                "AttributeValue": html_flattened
            }
        ]
        api_data = {"Scheme_Name": "Magnum Hybrid"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(len(result["asset_allocation"]), 5)
        self.assertEqual(result["asset_allocation"][0]["allocation_type"], "Equity & Equity related instruments")
        self.assertEqual(result["asset_allocation"][0]["minimum_percentage"], 65)
        self.assertEqual(result["asset_allocation"][0]["maximum_percentage"], 75)

        self.assertEqual(result["asset_allocation"][2]["allocation_type"], "Unhedged (Short derivatives)")
        self.assertEqual(result["asset_allocation"][2]["minimum_percentage"], 0)
        self.assertEqual(result["asset_allocation"][2]["maximum_percentage"], 25)

        self.assertEqual(
            result["asset_allocation"][3]["allocation_type"],
            "Debt and Money Market Instruments, including Units of Debt oriented mutual fund schemes"
        )
        self.assertEqual(result["asset_allocation"][3]["minimum_percentage"], 25)
        self.assertEqual(result["asset_allocation"][3]["maximum_percentage"], 35)

    def test_html_entities_and_spacing_variations(self):
        """Tests HTML entities (&amp;) and wide spacing (SSD_S-10 pattern)."""
        rows = [
            {
                "SUMMARY": "Stated Asset Allocation",
                "Value": (
                    "Debt &amp; Money Market Instruments -  35 % to  65%                                                                                 "
                    "Equity &amp; Equity Related Instruments - 35% to 65%                                                                   "
                    "Units Issued by InvITs - 0% to 20%"
                )
            }
        ]
        api_data = {"Scheme_Name": "Asit Hybrid"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(result["asset_allocation"], [
            {
                "allocation_type": "Debt & Money Market Instruments",
                "minimum_percentage": 35,
                "maximum_percentage": 65
            },
            {
                "allocation_type": "Equity & Equity Related Instruments",
                "minimum_percentage": 35,
                "maximum_percentage": 65
            },
            {
                "allocation_type": "Units Issued by InvITs",
                "minimum_percentage": 0,
                "maximum_percentage": 20
            }
        ])

    def test_footnote_stripping_and_explanations(self):
        """Tests that footnote descriptions (* and # notes) are ignored and not treated as allocations (SSD_S-16 pattern)."""
        text = (
            "Equity and Equity related instruments*: 80% - 100%,\n"
            "Short exposure through unhedged derivative positions in equity and equity related instruments*: 0% - 25%\n"
            "Debt, money market instruments (excluding instrument, securities kept for Margin purpose), Invits, Exchange Trade Funds and units of debt mutual fund schemes#: 0% - 20%\n\n"
            "*Equity and equity related instruments include both Long and Short Equity Positions. Atleast 65% of the total proceeds of such funds are invested in the equity shares of domestic companies listed on a recognised stock exchange.\n"
            "#Money Market instruments include commercial papers, commercial bills, treasury bills, Tri-party repo, Government securities having an unexpired maturity up to one year, call or notice money, certificate of deposit, and any other like instruments as specified under applicable regulations from time to time."
        )
        rows = [{"Stated Asset Allocation": text}]
        api_data = {"Scheme_Name": "Franklin SIF"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(len(result["asset_allocation"]), 3)
        self.assertEqual(result["asset_allocation"][0]["allocation_type"], "Equity and Equity related instruments")
        self.assertEqual(result["asset_allocation"][0]["minimum_percentage"], 80)
        self.assertEqual(result["asset_allocation"][0]["maximum_percentage"], 100)

        self.assertEqual(
            result["asset_allocation"][1]["allocation_type"],
            "Short exposure through unhedged derivative positions in equity and equity related instruments"
        )
        self.assertEqual(result["asset_allocation"][1]["minimum_percentage"], 0)
        self.assertEqual(result["asset_allocation"][1]["maximum_percentage"], 25)

        self.assertEqual(
            result["asset_allocation"][2]["allocation_type"],
            "Debt, money market instruments (excluding instrument, securities kept for Margin purpose), Invits, Exchange Trade Funds and units of debt mutual fund schemes"
        )
        self.assertEqual(result["asset_allocation"][2]["minimum_percentage"], 0)
        self.assertEqual(result["asset_allocation"][2]["maximum_percentage"], 20)

    def test_decimal_percentages(self):
        """Tests decimal percentage extraction."""
        rows = [
            {
                "Stated Asset Allocation": "Equity and equity related instruments: 65.5% - 80.0%\nDebt instruments: 20.0% to 34.5%"
            }
        ]
        api_data = {"Scheme_Name": "Decimal Fund"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(result["asset_allocation"], [
            {
                "allocation_type": "Equity and equity related instruments",
                "minimum_percentage": 65.5,
                "maximum_percentage": 80.0
            },
            {
                "allocation_type": "Debt instruments",
                "minimum_percentage": 20.0,
                "maximum_percentage": 34.5
            }
        ])

    def test_single_percentage_and_special_values(self):
        """Tests single percentage (e.g. unhedged short exposure - 25%)."""
        rows = [
            {
                "Stated Asset Allocation": (
                    "Equity and equity related instruments: 65% - 100%\n"
                    "Debt and money market instruments: 0 - 35%\n"
                    "Units issued by InvITs: 0 - 20%\n"
                    "Unhedged short exposure through unhedged derivative positions: 25%"
                )
            }
        ]
        api_data = {"Scheme_Name": "Single Pct Fund"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(len(result["asset_allocation"]), 4)
        self.assertEqual(result["asset_allocation"][3]["allocation_type"], "Unhedged short exposure through unhedged derivative positions")
        self.assertEqual(result["asset_allocation"][3]["minimum_percentage"], 0)
        self.assertEqual(result["asset_allocation"][3]["maximum_percentage"], 25)


    def test_space_separated_min_max_numbers(self):
        """Tests space/tab separated two-number range (SSD_S-24 ICICI format)."""
        text = (
            "Equity and Equity related instruments* (including up to 25% in Unhedged short exposure through derivative instruments) #   80  100\n"
            "Debt, Money Market instruments and Units of Debt Oriented Mutual Funds  0   20\n"
            "Units of Infrastructure Investments Trusts (InvITs) and Real Estate Investment Trusts (REITs)   0   20"
        )
        rows = [{"Stated Asset Allocation": text}]
        api_data = {"Scheme_Name": "iSIF Equity Long-Short Fund"}
        result, _ = build_scheme_json(api_data, rows)

        self.assertEqual(result["asset_allocation"], [
            {
                "allocation_type": "Equity and Equity related instruments* (including up to 25% in Unhedged short exposure through derivative instruments)",
                "minimum_percentage": 80,
                "maximum_percentage": 100
            },
            {
                "allocation_type": "Debt, Money Market instruments and Units of Debt Oriented Mutual Funds",
                "minimum_percentage": 0,
                "maximum_percentage": 20
            },
            {
                "allocation_type": "Units of Infrastructure Investments Trusts (InvITs) and Real Estate Investment Trusts (REITs)",
                "minimum_percentage": 0,
                "maximum_percentage": 20
            }
        ])


if __name__ == "__main__":
    unittest.main()

