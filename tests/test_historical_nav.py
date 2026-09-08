import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from services.historical_nav_service import (
    clean_nav_value,
    discover_eligible_non_direct_sifs,
    fetch_daily_sif_nav_from_amfi,
    fetch_historical_nav_from_amfi,
    merge_historical_records,
    parse_nav_date,
    read_existing_historical_csv,
    write_historical_nav_csv,
)
from services.performance_service import calculate_performance_metrics


class TestHistoricalNAV(unittest.TestCase):

    def test_parse_nav_date(self):
        # ISO format
        dt, s = parse_nav_date("2026-08-19")
        self.assertEqual(dt, datetime(2026, 8, 19))
        self.assertEqual(s, "19-Aug-2026")

        # ISO format with timestamp
        dt, s = parse_nav_date("2026-08-19T00:00:00.000Z")
        self.assertEqual(dt, datetime(2026, 8, 19))
        self.assertEqual(s, "19-Aug-2026")

        # AMFI dd-MMM-yyyy format
        dt, s = parse_nav_date("19-Aug-2026")
        self.assertEqual(dt, datetime(2026, 8, 19))
        self.assertEqual(s, "19-Aug-2026")

        # Invalid date
        dt, s = parse_nav_date("invalid-date")
        self.assertIsNone(dt)
        self.assertIsNone(s)

    def test_clean_nav_value(self):
        self.assertEqual(clean_nav_value(10.533), 10.533)
        self.assertEqual(clean_nav_value("10.5330"), 10.533)
        self.assertEqual(clean_nav_value(" 1,024.3682 "), 1024.3682)

        # Corrupted non-numeric values must return None
        self.assertIsNone(clean_nav_value("GROWTH"))
        self.assertIsNone(clean_nav_value("Direct Plan"))
        self.assertIsNone(clean_nav_value("IDCW Option"))
        self.assertIsNone(clean_nav_value(""))
        self.assertIsNone(clean_nav_value("-"))
        self.assertIsNone(clean_nav_value(0.0))
        self.assertIsNone(clean_nav_value(-5.2))

    def test_merge_historical_records_deduplication_and_sorting(self):
        existing_rows = [
            {"sif_code": "SIF-122", "nav_date": "10-Jun-2026", "nav": "9.9678", "dt": datetime(2026, 6, 10)},
            {"sif_code": "SIF-122", "nav_date": "18-Aug-2026", "nav": "11.2185", "dt": datetime(2026, 8, 18)},
            {"sif_code": "SIF-122", "nav_date": "01-Sep-2026", "nav": "11.0820", "dt": datetime(2026, 9, 1)},
        ]

        # New records containing 19-Aug, 20-Aug, and an overlapping 18-Aug
        new_rows = [
            {"sif_code": "SIF-122", "nav_date": "18-Aug-2026", "nav": "11.2185", "dt": datetime(2026, 8, 18)},
            {"sif_code": "SIF-122", "nav_date": "19-Aug-2026", "nav": "11.2355", "dt": datetime(2026, 8, 19)},
            {"sif_code": "SIF-122", "nav_date": "20-Aug-2026", "nav": "11.2290", "dt": datetime(2026, 8, 20)},
            {"sif_code": "SIF-122", "nav_date": "11-Jun-2026", "nav": "9.9344", "dt": datetime(2026, 6, 11)},
        ]

        merged = merge_historical_records(existing_rows, new_rows)

        # Check total unique dates
        self.assertEqual(len(merged), 6)

        # Check chronological ordering
        dates = [datetime.strptime(r["nav_date"], "%d-%b-%Y") for r in merged]
        self.assertEqual(dates, sorted(dates))

        # Check specific records
        self.assertEqual(merged[0]["nav_date"], "10-Jun-2026")
        self.assertEqual(merged[1]["nav_date"], "11-Jun-2026")
        self.assertEqual(merged[2]["nav_date"], "18-Aug-2026")
        self.assertEqual(merged[3]["nav_date"], "19-Aug-2026")
        self.assertEqual(merged[4]["nav_date"], "20-Aug-2026")
        self.assertEqual(merged[5]["nav_date"], "01-Sep-2026")

    def test_merge_idempotency(self):
        rows = [
            {"sif_code": "SIF-122", "nav_date": "10-Jun-2026", "nav": "9.9678", "dt": datetime(2026, 6, 10)},
            {"sif_code": "SIF-122", "nav_date": "11-Jun-2026", "nav": "9.9344", "dt": datetime(2026, 6, 11)},
        ]
        merged1 = merge_historical_records(rows, rows)
        merged2 = merge_historical_records(merged1, rows)
        self.assertEqual(merged1, merged2)
        self.assertEqual(len(merged2), 2)

    def test_merge_recovers_missing_earlier_dates_without_overwriting(self):
        # Scenario: SIF-3 existing CSV starts at 14-Oct-2025
        existing_rows = [
            {"sif_code": "SIF-3", "nav_date": "14-Oct-2025", "nav": "10.0125", "dt": datetime(2025, 10, 14)},
            {"sif_code": "SIF-3", "nav_date": "15-Oct-2025", "nav": "10.0250", "dt": datetime(2025, 10, 15)},
        ]

        # AMFI returns missing earlier dates (08-Oct to 13-Oct) plus an overlapping date with different precision
        amfi_rows = [
            {"sif_code": "SIF-3", "nav_date": "08-Oct-2025", "nav": "10.0000", "dt": datetime(2025, 10, 8)},
            {"sif_code": "SIF-3", "nav_date": "09-Oct-2025", "nav": "10.0010", "dt": datetime(2025, 10, 9)},
            {"sif_code": "SIF-3", "nav_date": "10-Oct-2025", "nav": "10.0050", "dt": datetime(2025, 10, 10)},
            {"sif_code": "SIF-3", "nav_date": "13-Oct-2025", "nav": "10.0090", "dt": datetime(2025, 10, 13)},
            {"sif_code": "SIF-3", "nav_date": "14-Oct-2025", "nav": "10.0125", "dt": datetime(2025, 10, 14)},
        ]

        merged = merge_historical_records(existing_rows, amfi_rows)

        # 6 total dates chronologically sorted from 08-Oct-2025 to 15-Oct-2025
        self.assertEqual(len(merged), 6)
        self.assertEqual(merged[0]["nav_date"], "08-Oct-2025")
        self.assertEqual(merged[1]["nav_date"], "09-Oct-2025")
        self.assertEqual(merged[2]["nav_date"], "10-Oct-2025")
        self.assertEqual(merged[3]["nav_date"], "13-Oct-2025")
        self.assertEqual(merged[4]["nav_date"], "14-Oct-2025")
        self.assertEqual(merged[5]["nav_date"], "15-Oct-2025")

        # Existing 14-Oct and 15-Oct values are preserved
        self.assertEqual(merged[4]["nav"], "10.0125")
        self.assertEqual(merged[5]["nav"], "10.0250")


    def test_discover_eligible_non_direct_sifs_excludes_direct(self):
        navall_content = (
            "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
            "SIF-11;INF754K30052;;Altiva Hybrid Long-Short Fund;Regular Plan;Growth;10.8206;07-Sep-2026\n"
            "SIF-9;INF754K30010;;Altiva Hybrid Long-Short Fund;Direct Plan;Growth;11.1281;07-Sep-2026\n"
            "SIF-122;INF754K30136;;Altiva Equity Ex-Top 100;Regular Plan;Growth;11.0476;07-Sep-2026\n"
            "SIF-120;INF754K30094;;Altiva Equity Ex-Top 100;Direct Plan;Growth;11.0912;07-Sep-2026\n"
        )
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False) as tf:
            tf.write(navall_content)
            tf_path = tf.name

        try:
            eligible = discover_eligible_non_direct_sifs(details_dir="non_existent_dir", navall_path_or_url=tf_path)
            sif_codes = [e["sif_code"] for e in eligible]
            self.assertIn("SIF-11", sif_codes)
            self.assertIn("SIF-122", sif_codes)
            self.assertNotIn("SIF-9", sif_codes)
            self.assertNotIn("SIF-120", sif_codes)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_performance_calculation_with_backfilled_data(self):
        # Create a representative DataFrame with historical dates
        data = {
            "sif_code": ["SIF-122"] * 5,
            "nav_date": ["10-Jun-2026", "10-Jul-2026", "10-Aug-2026", "19-Aug-2026", "07-Sep-2026"],
            "nav": [10.0, 10.2, 10.5, 10.8, 11.0476]
        }
        df = pd.DataFrame(data)
        metrics = calculate_performance_metrics(df)
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["sif_code"], "SIF-122")
        self.assertIn("returns", metrics)
        self.assertIsNotNone(metrics["returns"]["since_launch"])
        self.assertIsNotNone(metrics["returns"]["1_month"])


if __name__ == "__main__":
    unittest.main()
