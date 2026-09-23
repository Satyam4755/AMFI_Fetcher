import json
import os
import shutil
import tempfile
import unittest

import pandas as pd

from services.heatmap_service import (
    calculate_monthly_returns_for_scheme,
    natural_sif_sort_key,
)
from services.performance_service import (
    calculate_monthly_returns,
    calculate_performance_metrics,
)


class TestMonthlyPerformanceAndMetrics(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.historical_dir = os.path.join(self.test_dir, "historical")
        self.perf_dir = os.path.join(self.test_dir, "performance")
        os.makedirs(self.historical_dir, exist_ok=True)
        os.makedirs(self.perf_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_natural_sif_sort_key(self):
        codes = ["SIF-100", "SIF-2", "SIF-10", "SIF-1", "SIF-20"]
        sorted_codes = sorted(codes, key=natural_sif_sort_key)
        self.assertEqual(sorted_codes, ["SIF-1", "SIF-2", "SIF-10", "SIF-20", "SIF-100"])

    def test_positive_and_negative_monthly_returns_keys_and_values(self):
        # January: 10.0 -> 10.5 (+5.00%)
        # February: 10.5 -> 10.2 (-2.86%)
        # March: missing
        data = {
            "sif_code": ["SIF-1"] * 5,
            "nav_date": ["02-Jan-2026", "30-Jan-2026", "02-Feb-2026", "15-Feb-2026", "27-Feb-2026"],
            "nav": [10.0, 10.5, 10.5, 10.3, 10.2],
        }
        df = pd.DataFrame(data)
        monthly_returns = calculate_monthly_returns(df)

        # Keys must be YYYY-MM format
        self.assertIn("2026-01", monthly_returns)
        self.assertIn("2026-02", monthly_returns)
        self.assertNotIn("2026-03", monthly_returns)

        self.assertEqual(monthly_returns["2026-01"], 5.00)
        self.assertEqual(monthly_returns["2026-02"], -2.86)

    def test_single_day_and_partial_month(self):
        # July: Single day on 15-Jul-2026 -> 0.00%
        # August: Partial month 01-Aug to 10-Aug -> 10.0 -> 10.2 (+2.00%)
        data = {
            "sif_code": ["SIF-5"] * 3,
            "nav_date": ["15-Jul-2026", "01-Aug-2026", "10-Aug-2026"],
            "nav": [10.0, 10.0, 10.2],
        }
        df = pd.DataFrame(data)
        monthly_returns = calculate_monthly_returns(df)

        self.assertIn("2026-07", monthly_returns)
        self.assertIn("2026-08", monthly_returns)
        self.assertEqual(monthly_returns["2026-07"], 0.00)
        self.assertEqual(monthly_returns["2026-08"], 2.00)
        self.assertNotIn("2026-09", monthly_returns)

    def test_multiple_years_handling(self):
        data = {
            "sif_code": ["SIF-10"] * 4,
            "nav_date": ["15-Jan-2025", "30-Jan-2025", "10-Feb-2026", "28-Feb-2026"],
            "nav": [10.0, 11.0, 11.0, 12.1],
        }
        df = pd.DataFrame(data)
        monthly_returns = calculate_monthly_returns(df)

        self.assertIn("2025-01", monthly_returns)
        self.assertIn("2026-02", monthly_returns)
        self.assertEqual(monthly_returns["2025-01"], 10.00)
        self.assertEqual(monthly_returns["2026-02"], 10.00)
        self.assertNotIn("2025-02", monthly_returns)
        self.assertNotIn("2026-01", monthly_returns)

    def test_malformed_and_invalid_data_handling(self):
        # Empty df
        self.assertEqual(calculate_monthly_returns(pd.DataFrame()), {})

        # Non-numeric / negative NAV / invalid dates
        data = {
            "sif_code": ["SIF-1", "SIF-1", "SIF-1", "SIF-1"],
            "nav_date": ["invalid-date", "01-Jan-2026", "15-Jan-2026", "31-Jan-2026"],
            "nav": [10.0, -5.0, "abc", 10.0],
        }
        df = pd.DataFrame(data)
        monthly_returns = calculate_monthly_returns(df)
        # Only 31-Jan-2026 with nav=10.0 is valid
        self.assertIn("2026-01", monthly_returns)
        self.assertEqual(monthly_returns["2026-01"], 0.00)

    def test_calculate_monthly_returns_for_scheme_backward_compatibility(self):
        data = {
            "sif_code": ["SIF-1"] * 4,
            "nav_date": ["10-Dec-2025", "31-Dec-2025", "05-Jan-2026", "30-Jan-2026"],
            "nav": [10.0, 10.5, 10.5, 11.025],
        }
        df = pd.DataFrame(data)
        res = calculate_monthly_returns_for_scheme(df)
        self.assertIn(2025, res)
        self.assertIn(2026, res)
        self.assertEqual(res[2025]["dec"], 5.00)
        self.assertEqual(res[2026]["jan"], 5.00)

    def test_performance_metrics_structure_and_returns(self):
        # Verify calculate_performance_metrics includes monthly_returns, returns, sif_code, last_updated
        df = pd.DataFrame({
            "sif_code": ["SIF-1", "SIF-1", "SIF-1"],
            "nav_date": ["10-Jul-2026", "31-Jul-2026", "16-Sep-2026"],
            "nav": [10.0, 10.5, 10.71],
        })
        perf = calculate_performance_metrics(df)
        self.assertEqual(perf["sif_code"], "SIF-1")
        self.assertIn("returns", perf)
        self.assertIn("monthly_returns", perf)
        self.assertIn("last_updated", perf)

        # Existing return metrics
        self.assertEqual(perf["returns"]["1_day"], 2.00)
        self.assertEqual(perf["returns"]["since_launch"], 7.10)

        # Monthly returns embedded
        self.assertIn("2026-07", perf["monthly_returns"])
        self.assertIn("2026-09", perf["monthly_returns"])
        self.assertEqual(perf["monthly_returns"]["2026-07"], 5.00)
        self.assertEqual(perf["monthly_returns"]["2026-09"], 0.00)

    def test_no_heatmap_csv_generated_and_performance_storage_intact(self):
        # Create sample historical NAV file
        df = pd.DataFrame({
            "sif_code": ["SIF-1", "SIF-1"],
            "nav_date": ["01-Jan-2026", "30-Jan-2026"],
            "nav": [10.0, 11.0],
        })
        hist_file = os.path.join(self.historical_dir, "sif_1.csv")
        df.to_csv(hist_file, index=False)

        # Simulate performance calculation
        metrics = calculate_performance_metrics(pd.read_csv(hist_file))
        out_path = os.path.join(self.perf_dir, "sif_1.json")
        with open(out_path, "w") as f:
            json.dump(metrics, f, indent=4)

        # Verify performance file exists and contains expected structure
        self.assertTrue(os.path.exists(out_path))
        with open(out_path, "r") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["sif_code"], "SIF-1")
        self.assertEqual(loaded["monthly_returns"]["2026-01"], 10.0)

        # Verify no heatmap directory or CSV files exist
        heatmap_dir = os.path.join(self.test_dir, "heatMap")
        self.assertFalse(os.path.exists(heatmap_dir))


if __name__ == "__main__":
    unittest.main()

