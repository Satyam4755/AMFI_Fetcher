import os
import shutil
import tempfile
import unittest

import pandas as pd

from services.heatmap_service import (
    HEADER,
    calculate_monthly_returns_for_scheme,
    generate_all_heatmaps,
    natural_sif_sort_key,
)
from services.performance_service import calculate_performance_metrics


class TestHeatmapService(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.historical_dir = os.path.join(self.test_dir, "historical")
        self.heatmap_dir = os.path.join(self.test_dir, "heatMap")
        os.makedirs(self.historical_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_natural_sif_sort_key(self):
        codes = ["SIF-100", "SIF-2", "SIF-10", "SIF-1", "SIF-20"]
        sorted_codes = sorted(codes, key=natural_sif_sort_key)
        self.assertEqual(sorted_codes, ["SIF-1", "SIF-2", "SIF-10", "SIF-20", "SIF-100"])

    def test_positive_and_negative_monthly_returns(self):
        # January: 10.0 -> 10.5 (+5.00%)
        # February: 10.5 -> 10.2 (-2.86%)
        # March: missing
        data = {
            "sif_code": ["SIF-1"] * 5,
            "nav_date": ["02-Jan-2026", "30-Jan-2026", "02-Feb-2026", "15-Feb-2026", "27-Feb-2026"],
            "nav": [10.0, 10.5, 10.5, 10.3, 10.2],
        }
        df = pd.DataFrame(data)
        res = calculate_monthly_returns_for_scheme(df)

        self.assertIn(2026, res)
        row = res[2026]
        self.assertEqual(row["sif_code"], "SIF-1")
        self.assertEqual(row["year"], 2026)
        self.assertEqual(row["jan"], 5.00)
        self.assertEqual(row["feb"], -2.86)
        self.assertIsNone(row["mar"])
        self.assertIsNone(row["dec"])

    def test_single_day_and_partial_month(self):
        # July: Single day on 15-Jul-2026 -> 0.00%
        # August: Partial month 01-Aug to 10-Aug -> 10.0 -> 10.2 (+2.00%)
        data = {
            "sif_code": ["SIF-5"] * 3,
            "nav_date": ["15-Jul-2026", "01-Aug-2026", "10-Aug-2026"],
            "nav": [10.0, 10.0, 10.2],
        }
        df = pd.DataFrame(data)
        res = calculate_monthly_returns_for_scheme(df)

        self.assertIn(2026, res)
        row = res[2026]
        self.assertEqual(row["jul"], 0.00)
        self.assertEqual(row["aug"], 2.00)
        self.assertIsNone(row["sep"])

    def test_multiple_years_handling(self):
        data = {
            "sif_code": ["SIF-10"] * 4,
            "nav_date": ["15-Jan-2025", "30-Jan-2025", "10-Feb-2026", "28-Feb-2026"],
            "nav": [10.0, 11.0, 11.0, 12.1],
        }
        df = pd.DataFrame(data)
        res = calculate_monthly_returns_for_scheme(df)

        self.assertIn(2025, res)
        self.assertIn(2026, res)
        self.assertEqual(res[2025]["jan"], 10.00)
        self.assertIsNone(res[2025]["feb"])
        self.assertIsNone(res[2026]["jan"])
        self.assertEqual(res[2026]["feb"], 10.00)

    def test_malformed_and_invalid_data_handling(self):
        # Empty df
        self.assertEqual(calculate_monthly_returns_for_scheme(pd.DataFrame()), {})

        # Non-numeric / negative NAV / invalid dates
        data = {
            "sif_code": ["SIF-1", "SIF-1", "SIF-1", "SIF-1"],
            "nav_date": ["invalid-date", "01-Jan-2026", "15-Jan-2026", "31-Jan-2026"],
            "nav": [10.0, -5.0, "abc", 10.0],
        }
        df = pd.DataFrame(data)
        res = calculate_monthly_returns_for_scheme(df)
        # Only 31-Jan-2026 with nav=10.0 is valid
        self.assertIn(2026, res)
        self.assertEqual(res[2026]["jan"], 0.00)

    def test_generate_all_heatmaps_full_pipeline_and_determinism(self):
        # Create 2 historical files: sif_1.csv and sif_120.csv across 2025 and 2026
        df_1 = pd.DataFrame({
            "sif_code": ["SIF-1", "SIF-1", "SIF-1", "SIF-1"],
            "nav_date": ["10-Dec-2025", "31-Dec-2025", "05-Jan-2026", "30-Jan-2026"],
            "nav": [10.0, 10.5, 10.5, 11.025],
        })
        df_1.to_csv(os.path.join(self.historical_dir, "sif_1.csv"), index=False)

        df_120 = pd.DataFrame({
            "sif_code": ["SIF-120", "SIF-120"],
            "nav_date": ["01-Jan-2026", "31-Jan-2026"],
            "nav": [20.0, 19.0],
        })
        df_120.to_csv(os.path.join(self.historical_dir, "sif_120.csv"), index=False)

        # Run 1
        res1 = generate_all_heatmaps(self.historical_dir, self.heatmap_dir)
        self.assertEqual(res1["years_generated"], [2025, 2026])

        # Verify 2025.csv
        file_2025 = os.path.join(self.heatmap_dir, "2025.csv")
        self.assertTrue(os.path.exists(file_2025))
        df_2025 = pd.read_csv(file_2025, dtype=str)
        self.assertEqual(list(df_2025.columns), HEADER)
        self.assertEqual(len(df_2025), 1)
        self.assertEqual(df_2025.iloc[0]["sif_code"], "SIF-1")
        self.assertEqual(df_2025.iloc[0]["dec"], "5.00")
        self.assertTrue(pd.isna(df_2025.iloc[0]["jan"]) or df_2025.iloc[0]["jan"] == "")

        # Verify 2026.csv
        file_2026 = os.path.join(self.heatmap_dir, "2026.csv")
        self.assertTrue(os.path.exists(file_2026))
        df_2026 = pd.read_csv(file_2026, dtype=str)
        self.assertEqual(len(df_2026), 2)
        # SIF-1 must come before SIF-120
        self.assertEqual(df_2026.iloc[0]["sif_code"], "SIF-1")
        self.assertEqual(df_2026.iloc[0]["jan"], "5.00")
        self.assertEqual(df_2026.iloc[1]["sif_code"], "SIF-120")
        self.assertEqual(df_2026.iloc[1]["jan"], "-5.00")

        # Run 2: Check Determinism
        generate_all_heatmaps(self.historical_dir, self.heatmap_dir)
        df_2026_second_run = pd.read_csv(file_2026, dtype=str)
        self.assertTrue(df_2026.equals(df_2026_second_run))

    def test_existing_performance_unaffected(self):
        # Verify calculate_performance_metrics still returns correct structure
        df = pd.DataFrame({
            "sif_code": ["SIF-1", "SIF-1"],
            "nav_date": ["15-Sep-2026", "16-Sep-2026"],
            "nav": [10.0, 10.2],
        })
        perf = calculate_performance_metrics(df)
        self.assertEqual(perf["sif_code"], "SIF-1")
        self.assertEqual(perf["returns"]["1_day"], 2.00)
        self.assertIn("since_launch", perf["returns"])


if __name__ == "__main__":
    unittest.main()
