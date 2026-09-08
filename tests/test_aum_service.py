import os
import sys
import unittest
import tempfile
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.aum_service import (
    clean_numeric_aum,
    parse_aum_records,
    fetch_financial_years,
    fetch_periods,
    fetch_schemewise_aum_raw,
    fetch_latest_sif_aum,
    merge_aum_into_schemes,
    update_single_daily_csv,
    update_daily_csv_files,
)


class TestSIFAUMService(unittest.TestCase):

    def test_clean_numeric_aum_various_formats(self):
        """Test cleaning and conversion of various raw AUM formats."""
        # Standard float and int
        self.assertEqual(clean_numeric_aum(6138.22), 6138.22)
        self.assertEqual(clean_numeric_aum(100), 100.0)
        
        # Strings with commas and spaces (thousands separator)
        self.assertEqual(clean_numeric_aum("6,138.22"), 6138.22)
        self.assertEqual(clean_numeric_aum(" 146,725.84 "), 146725.84)
        self.assertEqual(clean_numeric_aum("Rs. 6,138.22 Lakhs"), 6138.22)
        
        # Missing / invalid values
        self.assertIsNone(clean_numeric_aum(None))
        self.assertIsNone(clean_numeric_aum(""))
        self.assertIsNone(clean_numeric_aum("   "))
        self.assertIsNone(clean_numeric_aum("-"))
        self.assertIsNone(clean_numeric_aum("N/A"))
        self.assertIsNone(clean_numeric_aum("NaN"))
        self.assertIsNone(clean_numeric_aum("null"))

    def test_parse_aum_records_generic(self):
        """Test parsing AMFI response records into SIF code -> AUM float mapping."""
        sample_records = [
            {
                "sifname": "Altiva SIF",
                "SchemeCat_Desc": "Equity Oriented Investment Strategies - Equity Ex-Top 100 Long-Short Fund",
                "schemes": [
                    {
                        "SchemeNAVName": "Altiva Equity Ex- Top 100 Long - Short Fund - Direct Plan - Growth",
                        "AMFI_Code": "SIF-120",
                        "AverageAumForTheMonth": 2975.25
                    },
                    {
                        "SchemeNAVName": "Altiva Equity Ex- Top 100 Long - Short Fund - Regular Plan - Growth",
                        "AMFI_Code": "SIF-122",
                        "AverageAumForTheMonth": "6,138.22"
                    }
                ]
            },
            {
                "sifname": "Magnum SIF",
                "SchemeCat_Desc": "Hybrid Investment Strategies - Hybrid Long-Short Fund",
                "schemes": [
                    {
                        "SchemeNAVName": "Magnum Hybrid Long Short Fund - Regular Plan - Growth",
                        "AMFI_Code": "SIF-13",
                        "AverageAumForTheMonth": 173724.47
                    }
                ]
            },
            {
                "sifname": "Total",
                "schemes": []
            }
        ]

        result = parse_aum_records(sample_records)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["SIF-120"], 2975.25)
        self.assertEqual(result["SIF-122"], 6138.22)
        self.assertEqual(result["SIF-13"], 173724.47)

    def test_parse_aum_records_empty_and_malformed(self):
        """Test handling of empty, None, and malformed rows."""
        self.assertEqual(parse_aum_records([]), {})
        self.assertEqual(parse_aum_records(None), {})
        
        malformed = [
            {"sifname": "Bad Group", "schemes": "not a list"},
            {"sifname": "Missing Code", "schemes": [{"AverageAumForTheMonth": 100}]},
            {"sifname": "Invalid AUM", "schemes": [{"AMFI_Code": "SIF-999", "AverageAumForTheMonth": "invalid"}]},
        ]
        res = parse_aum_records(malformed)
        self.assertEqual(res, {})

    def test_merge_aum_into_schemes(self):
        """Test merging AUM values into list of scheme dicts."""
        schemes = [
            {"sif_code": "SIF-122", "nav_date": "13-Jul-2026", "nav": "10.9249"},
            {"sif_code": "SIF-13", "nav_date": "13-Jul-2026", "nav": "10.5330"},
            {"sif_code": "SIF-999", "nav_date": "13-Jul-2026", "nav": "10.0000"},  # missing from AUM map
        ]
        aum_map = {
            "SIF-122": 6138.22,
            "SIF-13": 173724.47,
        }

        merged = merge_aum_into_schemes(schemes, aum_map)
        
        # Check NAV and date preserved exactly
        self.assertEqual(merged[0]["sif_code"], "SIF-122")
        self.assertEqual(merged[0]["nav_date"], "13-Jul-2026")
        self.assertEqual(merged[0]["nav"], "10.9249")
        self.assertEqual(merged[0]["AUM"], "6138.22")

        self.assertEqual(merged[1]["sif_code"], "SIF-13")
        self.assertEqual(merged[1]["nav_date"], "13-Jul-2026")
        self.assertEqual(merged[1]["nav"], "10.5330")
        self.assertEqual(merged[1]["AUM"], "173724.47")

        # Missing AUM handled safely with empty string
        self.assertEqual(merged[2]["sif_code"], "SIF-999")
        self.assertEqual(merged[2]["AUM"], "")

    def test_update_single_daily_csv(self):
        """Test updating a single daily CSV file with AUM column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "20260714.csv")
            
            # Write original 3-column CSV
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["sif_code", "nav_date", "nav"])
                writer.writerow(["SIF-122", "13-Jul-2026", "10.9249"])
                writer.writerow(["SIF-13", "13-Jul-2026", "10.5330"])
                writer.writerow(["SIF-999", "13-Jul-2026", "10.0000"])

            aum_map = {
                "SIF-122": 6138.22,
                "SIF-13": 173724.47,
            }

            # Update CSV
            success = update_single_daily_csv(csv_path, aum_map)
            self.assertTrue(success)

            # Read and verify updated CSV
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))

            self.assertEqual(len(reader), 3)
            self.assertEqual(reader[0], {
                "sif_code": "SIF-122",
                "nav_date": "13-Jul-2026",
                "nav": "10.9249",
                "AUM": "6138.22"
            })
            self.assertEqual(reader[1], {
                "sif_code": "SIF-13",
                "nav_date": "13-Jul-2026",
                "nav": "10.5330",
                "AUM": "173724.47"
            })
            self.assertEqual(reader[2], {
                "sif_code": "SIF-999",
                "nav_date": "13-Jul-2026",
                "nav": "10.0000",
                "AUM": ""
            })

            # Test idempotency: re-running should yield identical result
            update_single_daily_csv(csv_path, aum_map)
            with open(csv_path, "r", encoding="utf-8") as f:
                reader_second = list(csv.DictReader(f))
            self.assertEqual(reader, reader_second)

    def test_live_amfi_endpoint_resolution(self):
        """Integration test with live AMFI API to verify dynamic FY, period, and SIF-122 resolution."""
        sif_aum_map, metadata = fetch_latest_sif_aum()
        
        self.assertIsNotNone(metadata["financial_year"])
        self.assertIsNotNone(metadata["period"])
        self.assertGreater(len(sif_aum_map), 50, "Expected at least 50 SIF schemes in AMFI AUM response")
        
        # Verify specific known funds in real AMFI data
        self.assertIn("SIF-122", sif_aum_map)
        self.assertAlmostEqual(sif_aum_map["SIF-122"], 6138.22, places=2)
        
        self.assertIn("SIF-13", sif_aum_map)
        self.assertAlmostEqual(sif_aum_map["SIF-13"], 173724.47, places=2)
        
        self.assertIn("SIF-1", sif_aum_map)
        self.assertAlmostEqual(sif_aum_map["SIF-1"], 34219.94, places=2)


if __name__ == "__main__":
    unittest.main()
