import csv
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from services.parser import extract_schemes
from services.historical_nav_service import (
    parse_nav_date,
    clean_nav_value,
    merge_historical_records,
    update_historical_nav,
)
from scripts.fetch_sif_nav import (
    load_stored_schemes_map,
    evaluate_nav_updates,
    reconcile_previous_day_nav,
    sync_sif_nav,
)


class TestNavPipelineAndFreshness(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.daily_dir = os.path.join(self.test_dir, "daily")
        self.hist_dir = os.path.join(self.test_dir, "historical")
        self.perf_dir = os.path.join(self.test_dir, "performance")
        os.makedirs(self.daily_dir, exist_ok=True)
        os.makedirs(self.hist_dir, exist_ok=True)
        os.makedirs(self.perf_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_extract_schemes_sif87_sample(self):
        sample_feed = (
            "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
            "SIF-120;INF754K30094;-;Altiva Equity Ex- Top 100 Long - Short Fund;Direct Plan;Growth;10.5892;05-Oct-2026\n"
            "SIF-87;INF579M30075;-;DynaSIF Active Asset Allocator Long-Short Fund;Regular Plan;GROWTH OPTION;10.3825;05-Oct-2026\n"
        )
        schemes = extract_schemes(sample_feed)
        self.assertIsNotNone(schemes)
        self.assertEqual(len(schemes), 2)

        sif87 = next(s for s in schemes if s["sif_code"] == "SIF-87")
        self.assertEqual(sif87["sif_code"], "SIF-87")
        self.assertEqual(sif87["nav_date"], "05-Oct-2026")
        self.assertEqual(sif87["nav"], "10.3825")

    def test_extract_schemes_duplicate_sif_code_retains_latest_date(self):
        feed_with_duplicates = (
            "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
            "SIF-87;INF579M30075;-;DynaSIF Active Asset Allocator;Regular;Growth;10.3705;01-Oct-2026\n"
            "SIF-87;INF579M30075;-;DynaSIF Active Asset Allocator;Regular;Growth;10.3825;05-Oct-2026\n"
        )
        schemes = extract_schemes(feed_with_duplicates)
        self.assertIsNotNone(schemes)
        self.assertEqual(len(schemes), 1)
        self.assertEqual(schemes[0]["sif_code"], "SIF-87")
        self.assertEqual(schemes[0]["nav_date"], "05-Oct-2026")
        self.assertEqual(schemes[0]["nav"], "10.3825")

    def test_evaluate_nav_updates_detects_newer_date_for_sif87(self):
        stored_map = {
            "SIF-120": {"sif_code": "SIF-120", "dt": datetime(2026, 10, 5), "nav_date": "05-Oct-2026", "nav": "10.5892", "AUM": "42866.92"},
            "SIF-87": {"sif_code": "SIF-87", "dt": datetime(2026, 10, 1), "nav_date": "01-Oct-2026", "nav": "10.3705", "AUM": "17725.39"},
        }
        incoming_schemes = [
            {"sif_code": "SIF-120", "nav_date": "05-Oct-2026", "nav": "10.5892"},
            {"sif_code": "SIF-87", "nav_date": "05-Oct-2026", "nav": "10.3825"},
        ]
        target_csv = os.path.join(self.daily_dir, "20261005.csv")
        # Create dummy existing file
        with open(target_csv, "w", encoding="utf-8") as f:
            f.write("dummy")

        has_updates, updates = evaluate_nav_updates(incoming_schemes, stored_map, target_csv)
        self.assertTrue(has_updates)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["sif_code"], "SIF-87")
        self.assertEqual(updates[0]["old_date"], "01-Oct-2026")
        self.assertEqual(updates[0]["old_nav"], "10.3705")
        self.assertEqual(updates[0]["new_date"], "05-Oct-2026")
        self.assertEqual(updates[0]["new_nav"], "10.3825")

    def test_evaluate_nav_updates_retains_older_nav_when_amfi_has_no_newer_value(self):
        stored_map = {
            "SIF-1": {"sif_code": "SIF-1", "dt": datetime(2026, 10, 5), "nav_date": "05-Oct-2026", "nav": "10.9942", "AUM": "1000"},
            "SIF-2": {"sif_code": "SIF-2", "dt": datetime(2026, 10, 1), "nav_date": "01-Oct-2026", "nav": "10.5000", "AUM": "2000"},
        }
        incoming_schemes = [
            {"sif_code": "SIF-1", "nav_date": "05-Oct-2026", "nav": "10.9942"},
            {"sif_code": "SIF-2", "nav_date": "01-Oct-2026", "nav": "10.5000"},
        ]
        target_csv = os.path.join(self.daily_dir, "20261005.csv")
        with open(target_csv, "w", encoding="utf-8") as f:
            f.write("dummy")

        has_updates, updates = evaluate_nav_updates(incoming_schemes, stored_map, target_csv)
        self.assertFalse(has_updates)
        self.assertEqual(len(updates), 0)

    def test_evaluate_nav_updates_detects_corrected_nav_value_same_date(self):
        stored_map = {
            "SIF-87": {"sif_code": "SIF-87", "dt": datetime(2026, 10, 5), "nav_date": "05-Oct-2026", "nav": "10.3800", "AUM": "17725.39"},
        }
        incoming_schemes = [
            {"sif_code": "SIF-87", "nav_date": "05-Oct-2026", "nav": "10.3825"},
        ]
        target_csv = os.path.join(self.daily_dir, "20261005.csv")
        with open(target_csv, "w", encoding="utf-8") as f:
            f.write("dummy")

        has_updates, updates = evaluate_nav_updates(incoming_schemes, stored_map, target_csv)
        self.assertTrue(has_updates)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["reason"], "updated_nav_value")
        self.assertEqual(updates[0]["new_nav"], "10.3825")

    def test_merge_historical_records_updates_value_for_same_date(self):
        existing_rows = [
            {"sif_code": "SIF-87", "nav_date": "01-Oct-2026", "nav": "10.3705", "dt": datetime(2026, 10, 1)},
            {"sif_code": "SIF-87", "nav_date": "05-Oct-2026", "nav": "10.3800", "dt": datetime(2026, 10, 5)},
        ]
        new_rows = [
            {"sif_code": "SIF-87", "nav_date": "05-Oct-2026", "nav": "10.3825", "dt": datetime(2026, 10, 5)},
        ]
        merged = merge_historical_records(existing_rows, new_rows)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[1]["nav_date"], "05-Oct-2026")
        self.assertEqual(merged[1]["nav"], "10.3825")

    def test_update_historical_nav_appends_and_recalculates_performance(self):
        hist_csv = os.path.join(self.hist_dir, "sif_87.csv")
        with open(hist_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sif_code", "nav_date", "nav"])
            writer.writerow(["SIF-87", "01-Oct-2026", "10.3705"])

        schemes_to_update = [
            {"sif_code": "SIF-87", "nav_date": "05-Oct-2026", "nav": "10.3825"}
        ]
        update_historical_nav(schemes_to_update, base_dir=self.hist_dir, recalculate_perf=True)

        with open(hist_csv, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[0]["nav_date"], "01-Oct-2026")
        self.assertEqual(reader[0]["nav"], "10.3705")
        self.assertEqual(reader[1]["nav_date"], "05-Oct-2026")
        self.assertEqual(reader[1]["nav"], "10.3825")

    @patch("scripts.fetch_sif_nav.fetch_text")
    @patch("scripts.fetch_sif_nav.fetch_latest_sif_aum")
    def test_sync_sif_nav_end_to_end(self, mock_aum, mock_fetch_text):
        mock_fetch_text.return_value = (
            "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
            "SIF-120;INF754K30094;-;Altiva Equity Ex- Top 100 Long - Short Fund;Direct Plan;Growth;10.5892;05-Oct-2026\n"
            "SIF-87;INF579M30075;-;DynaSIF Active Asset Allocator Long-Short Fund;Regular Plan;GROWTH OPTION;10.3825;05-Oct-2026\n"
        )
        mock_aum.return_value = ({"SIF-120": 42866.92, "SIF-87": 17725.39}, {"financial_year": "2026-2027", "period": "Q2"})

        # Initial run for 20261005
        res = sync_sif_nav(base_dir=self.daily_dir, target_date_str="20261005")
        self.assertTrue(res)

        target_csv = os.path.join(self.daily_dir, "20261005.csv")
        self.assertTrue(os.path.exists(target_csv))

        with open(target_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)

        sif87_row = next(r for r in rows if r["sif_code"] == "SIF-87")
        self.assertEqual(sif87_row["nav_date"], "05-Oct-2026")
        self.assertEqual(sif87_row["nav"], "10.3825")
        self.assertEqual(sif87_row["AUM"], "17725.39")

    def test_reconcile_previous_day_nav_updates_yesterdays_csv(self):
        # Setup yesterday's CSV (20261006.csv) with older 05-Oct dates
        yesterday_csv = os.path.join(self.daily_dir, "20261006.csv")
        with open(yesterday_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sif_code", "nav_date", "nav", "AUM"])
            writer.writeheader()
            writer.writerows([
                {"sif_code": "SIF-86", "nav_date": "05-Oct-2026", "nav": "10.4551", "AUM": "10.50"},
                {"sif_code": "SIF-87", "nav_date": "05-Oct-2026", "nav": "10.3825", "AUM": "17725.39"},
                {"sif_code": "SIF-88", "nav_date": "05-Oct-2026", "nav": "10.4551", "AUM": "8714.99"},
                {"sif_code": "SIF-89", "nav_date": "05-Oct-2026", "nav": "10.3825", "AUM": "18.34"},
            ])

        # Incoming AMFI data has 06-Oct NAVs
        incoming_schemes = [
            {"sif_code": "SIF-86", "nav_date": "06-Oct-2026", "nav": "10.4704"},
            {"sif_code": "SIF-87", "nav_date": "06-Oct-2026", "nav": "10.3973"},
            {"sif_code": "SIF-88", "nav_date": "06-Oct-2026", "nav": "10.4704"},
            {"sif_code": "SIF-89", "nav_date": "06-Oct-2026", "nav": "10.3973"},
        ]

        # Reconcile for target date 20261007 (yesterday is 20261006)
        has_updates, updates = reconcile_previous_day_nav(
            base_dir=self.daily_dir,
            target_date_str="20261007",
            schemes=incoming_schemes,
        )
        self.assertTrue(has_updates)
        self.assertEqual(len(updates), 4)

        # Verify updated contents of 20261006.csv
        with open(yesterday_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 4)

        for row in rows:
            self.assertEqual(row["nav_date"], "06-Oct-2026")
            if row["sif_code"] in ("SIF-86", "SIF-88"):
                self.assertEqual(row["nav"], "10.4704")
            elif row["sif_code"] in ("SIF-87", "SIF-89"):
                self.assertEqual(row["nav"], "10.3973")

        # Second run should be idempotent with 0 updates
        has_updates2, updates2 = reconcile_previous_day_nav(
            base_dir=self.daily_dir,
            target_date_str="20261007",
            schemes=incoming_schemes,
        )
        self.assertFalse(has_updates2)
        self.assertEqual(len(updates2), 0)


if __name__ == "__main__":
    unittest.main()
